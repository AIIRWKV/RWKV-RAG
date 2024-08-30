
import msgpack
import zmq


class TuningClient:
    def __init__(self,frontend_url: str) -> None:
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ) # 设置请求套接字
        self.socket.connect(frontend_url)
        self.socket.setsockopt(zmq.RCVTIMEO, 60000 * 5)


    def jsonl2binidx(self,jsonl_file: str=None,
                  n_epoch: int=3,
                  output_path: str=None,
                  context_len: int=1024,
                  is_str=False,
                  ):
        """
        jsonl转换成binidx
        """
        cmd = {"cmd": "MAKE_DATA", 'jsonl_file': jsonl_file, 'n_epoch': n_epoch,
               'output_path': output_path, 'context_len': context_len, 'is_str': is_str}
        self.socket.send(msgpack.packb(cmd, use_bin_type=True))
        response = self.socket.recv()
        return msgpack.unpackb(response, raw=False)

    def lora_train(self,**kwargs):

        kwargs.update({"cmd":"LORA"})
        self.socket.send(msgpack.packb(kwargs, use_bin_type=True))
        response = self.socket.recv()
        return msgpack.unpackb(response, raw=False)

    def state_tuning_train(self,**kwargs):

        kwargs.update({"cmd":"STATE_TUNING"})
        self.socket.send(msgpack.packb(kwargs, use_bin_type=True))
        response = self.socket.recv()
        return msgpack.unpackb(response, raw=False)

    def pissa_train(self,**kwargs):
        kwargs.update({"cmd":"PISSA"})
        self.socket.send(msgpack.packb(kwargs, use_bin_type=True))
        response = self.socket.recv()
        return msgpack.unpackb(response, raw=False)

    def wandb_login(self,api_key: str):
        cmd = {"cmd": "WANDB_LOGIN", 'api_key': api_key}
        self.socket.send(msgpack.packb(cmd, use_bin_type=True))
        response = self.socket.recv()
        return msgpack.unpackb(response, raw=False)

    def wandb_info(self):
        cmd = {"cmd": "WANDB"}
        self.socket.send(msgpack.packb(cmd, use_bin_type=True))
        response = self.socket.recv()
        return msgpack.unpackb(response, raw=False)

    def wandb_add_project(self,project_name: str):
        cmd = {"cmd": "WANDB_ADD_PROJECT", 'project_name': project_name}
        self.socket.send(msgpack.packb(cmd, use_bin_type=True))
        response = self.socket.recv()
        return msgpack.unpackb(response, raw=False)

    def wandb_list_project(self):
        cmd = {"cmd": "WANDB_LIST_PROJECT"}
        self.socket.send(msgpack.packb(cmd, use_bin_type=True))
        response = self.socket.recv()
        return msgpack.unpackb(response, raw=False)
