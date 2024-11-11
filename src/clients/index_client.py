import uuid
from typing import List

import msgpack
import zmq


class IndexClient:
    def __init__(self,frontend_url) -> None:
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(frontend_url)
        self.socket.setsockopt(zmq.RCVTIMEO, 60000 * 5)

    def index_config(self,config):
        cmd = {"cmd": "INDEX_CONFIG"}
        self.socket.send(msgpack.packb(cmd, use_bin_type=True))
        msg = self.socket.recv()
        resp = msgpack.unpackb(msg, raw=False)
        return resp


    def index_texts(self,texts, embeddings:List[List[float]], keys=None,collection_name=None):
        if keys is None or isinstance(keys, list) is False or len(keys) != len(texts):
            keys = [str(uuid.uuid4()) for i in range(len(texts))]
        cmd = {"cmd": "INDEX_TEXTS", "texts": texts,
               "embeddings": embeddings,
               "keys": keys,'collection_name':collection_name}
        self.socket.send(msgpack.packb(cmd, use_bin_type=True))
        msg = self.socket.recv()
        resp = msgpack.unpackb(msg, raw=False)
        resp["keys"] = keys
        return resp

    def show_collection(self):
        cmd = {"cmd":'SHOW_COLLECTIONS'}
        self.socket.send(msgpack.packb(cmd, use_bin_type=True))
        msg = self.socket.recv()
        resp = msgpack.unpackb(msg, raw=False)
        return resp

    def create_collection(self,collection_name=None):
        cmd = {"cmd":'CREATE_COLLECTION','collection_name':collection_name}
        self.socket.send(msgpack.packb(cmd, use_bin_type=True))
        msg = self.socket.recv()
        resp = msgpack.unpackb(msg, raw=False)
        return resp

    def delete_collection(self,collection_name=None):
        cmd = {"cmd":'DELETE_COLLECTION','collection_name':collection_name}
        self.socket.send(msgpack.packb(cmd, use_bin_type=True))
        msg = self.socket.recv()
        resp = msgpack.unpackb(msg, raw=False)
        return resp

    def search_nearby(self,embeddings,collection_name):
        cmd = {"cmd": "SEARCH_NEARBY", "embeddings": embeddings, 'collection_name':collection_name}
        self.socket.send(msgpack.packb(cmd, use_bin_type=True))
        msg = self.socket.recv()
        resp = msgpack.unpackb(msg, raw=False)
        return resp
