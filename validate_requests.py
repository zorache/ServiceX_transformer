#!/usr/bin/env python

# this code gets requests in state: Created, Validates request on one file
# if request valid (all branches exist) it sets request state to Defined
# if not it sets state to Failed, deletes all the paths belonging to that request.

import time
import ROOT
import requests
from confluent_kafka import KafkaException, KafkaError
from confluent_kafka.admin import AdminClient, NewTopic

ROOT.gROOT.Macro('$ROOTCOREDIR/scripts/load_packages.C')


CONFIG = {
    'bootstrap.servers': 'servicex-kafka-1.slateci.net:19092',
    'client.id': 'monitor',
    'group.id': 'monitor',
    'session.timeout.ms': 5000,
}

ADMIN = AdminClient(CONFIG)

default_servicex_endpoint = 'https://servicex-frontend.uc.ssl-hep.org:443'


def validate_branches(file_name, branch_names):
    print("Validating file: " + file_name)
    # file_in = ROOT.TFile.Open('AOD.11182705._000001.pool.root.1')
    file_in = ROOT.TFile.Open(file_name)
    tree_in = ROOT.xAOD.MakeTransientTree(file_in)

    for branch_name in branch_names:
        if '.' not in branch_name:
            print(branch_name + " is not valid collection + attribute")
            return(False, "Not valid collection.attribute")

        branch = branch_name.split('.')[0].strip(' ')
        attr = branch_name.split('.')[1].strip('()')
        for i_evt in range(10):
            tree_in.GetEntry(i_evt)
            try:
                particles = getattr(tree_in, branch)
                if particles.size() >= 1:
                    if not attr in dir(particles.at(0)):
                        print(attr + " is not an attribute of " + branch)
                        return(False, attr + " is not an attribute of " + branch)
                    break
            except:
                return(False, "No collection with name:" + branch)

    return(True, "Validated OK")


def create_kafka_topic(admin, topic):
    config = {
        'compression.type': 'lz4',
        'max.message.bytes': 14500000
    }

    new_topics = [NewTopic(topic, num_partitions=10, replication_factor=1,
                           config=config)]
    response = admin.create_topics(new_topics, request_timeout=15.0)
    for topic, res in response.items():
        try:
            res.result()   # The result itself is None
            print("Topic {} created".format(topic))
        except KafkaException as k_execpt:
            k_error = k_execpt.args[0]
            print(k_error.str())
            return(k_error.code() == 36)


if __name__ == "__main__":
    while True:
        # gets request in Created
        req_resp = requests.get(default_servicex_endpoint + '/drequest/status/LookedUp', verify=False)
        try:
            req = req_resp.json()
        except ValueError:
            print("Decoding request response failed. Cont.")
            time.sleep(10)
            continue
        if not req:
            continue
        # print(req)

        req_id = req['reqId']
        branches = req['columns']

        # gets one file belonging to this request
        path_res = requests.get(default_servicex_endpoint + '/dpath/' + req_id + '/Created', verify=False)
        try:
            pat = path_res.json()
        except ValueError:
            print("Decoding path response failed. Cont.")
            time.sleep(10)
            continue

        if not pat:
            continue
        # print(pat)

        # checks the file
        (valid, info) = validate_branches(pat['file_path'], branches)

        if valid:
            # sets all the files to "Validated"
            while True:
                path_res = requests.get(default_servicex_endpoint + '/dpath/' + req_id + '/Created', verify=False)
                pat = path_res.json()
                if not pat:
                    break
                path_res = requests.put(default_servicex_endpoint + '/dpath/status/' + pat['pathId'] + '/Validated/' + info, verify=False)
                print('path: ' + pat['pathId'] + ' validation: ' + str(path_res.status_code))
            # sets request to "Validated"
            requests.put(default_servicex_endpoint + '/drequest/status/' + req_id + '/Validated/' + info, verify=False)

            create_kafka_topic(ADMIN, req_id)

        else:
            # fails all files
            while True:
                path_res = requests.get(default_servicex_endpoint + '/dpath/' + req_id + '/Created', verify=False)
                pat = path_res.json()
                if not pat:
                    break
                path_res = requests.put(default_servicex_endpoint + '/dpath/status/' + pat['pathId'] + '/Failed/' + info, verify=False)
                print('path: ' + pat['pathId'] + ' failing: ' + str(path_res.status_code))
            # sets request to "Failed"
            requests.put(default_servicex_endpoint + '/drequest/status/' + req_id + '/Failed/' + info, verify=False)
