#coding=utf-8
import os
from abc import ABC, abstractmethod

import zmq
import msgpack


class AbstractServiceWorker(ABC):
    UNSUPPORTED_COMMAND = 'Unsupported command'

    def __init__(self, backend_url, config):
        self.init_with_config(config)
        self.backend_url = backend_url
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REP)
        self.socket.connect(backend_url)
        self.service_config = config  # 服务的配置
        print(
            f"\033[93m Service worker {self.__class__.__name__} connected to {backend_url} at process {os.getpid()}\033[0m")

    @abstractmethod
    def init_with_config(self, config):
        pass

    @abstractmethod
    def process(self, cmd):
        pass

    def run(self):
        while True:
            message = self.socket.recv()
            cmd = msgpack.unpackb(message, raw=False)
            try:
                resp = self.process(cmd)
                if resp == AbstractServiceWorker.UNSUPPORTED_COMMAND:
                    resp = {"code": 400, "error": "Unsupported command"}
                else:
                    resp = {"code": 200, "value": resp}
                self.socket.send(msgpack.packb(resp, use_bin_type=True))
            except Exception as e:
                resp = {"code": 400, "error": str(e)}
                self.socket.send(msgpack.packb(resp, use_bin_type=True))

