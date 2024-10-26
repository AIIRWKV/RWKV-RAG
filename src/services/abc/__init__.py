#coding=utf-8
import os
from abc import ABC, abstractmethod

import zmq
import msgpack
from rwkv.utils import PIPELINE, PIPELINE_ARGS


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


class PipeLine(PIPELINE):
    def __init__(self, model, word_name):
        super().__init__(model, word_name)

    def generate(self, ctx, token_count=100, args=PIPELINE_ARGS(), callback=None, state=None):
        all_tokens = []
        out_last = 0
        occurrence = {}
        for i in range(token_count):

            # forward & adjust prob.
            tokens = self.encode(ctx) if i == 0 else [token]
            while len(tokens) > 0:
                out, state = self.model.forward(tokens[:args.chunk_len], state)
                tokens = tokens[args.chunk_len:]

            for n in args.token_ban:
                out[n] = -float('inf')
            for n in occurrence:
                out[n] -= (args.alpha_presence + occurrence[n] * args.alpha_frequency)

            # sampler
            token = self.sample_logits(out, temperature=args.temperature, top_p=args.top_p, top_k=args.top_k)
            if token in args.token_stop:
                break
            all_tokens += [token]
            for xxx in occurrence:
                occurrence[xxx] *= args.alpha_decay

            ttt = self.decode([token])
            www = 1
            if ttt in ' \t0123456789':
                www = 0
            # elif ttt in '\r\n,.;?!"\':+-*/=#@$%^&_`~|<>\\()[]{}，。；“”：？！（）【】':
            #     www = 0.5
            if token not in occurrence:
                occurrence[token] = www
            else:
                occurrence[token] += www
            # print(occurrence) # debug

            # output
            tmp = self.decode(all_tokens[out_last:])
            if '\ufffd' not in tmp:  # is valid utf-8 string?
                if callback:
                    callback(tmp)
                yield  tmp
                out_last = i + 1
