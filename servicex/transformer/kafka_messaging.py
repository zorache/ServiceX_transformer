# Copyright (c) 2019, IRIS-HEP
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import sys
import os
import time
from messaging import Messaging
from kafka import KafkaProducer


class KafkaMessaging(Messaging):
    def __init__(self, brokers):

        self.MAX_MESSAGES_PER_REQUEST = 100
        if 'MAX_MESSAGES_PER_REQUEST' in os.environ:
            self.MAX_MESSAGES_PER_REQUEST = int(os.environ['MAX_MESSAGES_PER_REQUEST'])
        print("max messages per request:", self.MAX_MESSAGES_PER_REQUEST)

        if not brokers:
            self.brokers = ['servicex-kafka-0.slateci.net:19092',
                            'servicex-kafka-1.slateci.net:19092',
                            'servicex-kafka-2.slateci.net:19092']
        else:
            self.brokers = brokers

        self.producer = None
        print('Configured Kafka backend')

        try:
            self.producer = KafkaProducer(bootstrap_servers=self.brokers,
                                          api_version=(0, 10))
            print("Kafka producer created successfully")
        except Exception as ex:
            print("Exception while getting Kafka producer", ex)
            sys.exit(1)

    def publish_message(self, topic_name, key, value_buffer):
        try:
            bytes = value_buffer.to_pybytes()
            self.producer.send(topic_name, key=str(key),
                               value=bytes)
            self.producer.flush()
            print("Message published successfully ", len(bytes))
        except Exception as ex:
            print("Exception in publishing message", ex)
            raise
        return True
