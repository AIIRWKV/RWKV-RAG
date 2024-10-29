import msgpack
import zmq

class LLMClient:
    def __init__(self,url) -> None:
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(url)
        self.socket.setsockopt(zmq.RCVTIMEO, 60000 * 5)

    def encode(self,texts):
        cmd = {"cmd": "GET_EMBEDDINGS", "texts": texts}
        self.socket.send(msgpack.packb(cmd, use_bin_type=True))
        msg = self.socket.recv()
        resp = msgpack.unpackb(msg, raw=False)
        return resp
    
    def cross_encode(self,texts_0,texts_1):
        cmd = {"cmd": "GET_CROSS_SCORES", "texts_0": texts_0,"texts_1": texts_1}
        self.socket.send(msgpack.packb(cmd, use_bin_type=True))
        msg = self.socket.recv()
        resp = msgpack.unpackb(msg, raw=False)
        return resp
    
    def beam_generate(self, instruction, input_text, token_count=128, num_beams=5):
        cmd = {
            "cmd": "BEAM_GENERATE",
            "instruction": instruction,
            "input_text": input_text,
            "token_count": token_count,
            "num_beams":num_beams
        }
        self.socket.send(msgpack.packb(cmd, use_bin_type=True))
        msg = self.socket.recv()
        resp = msgpack.unpackb(msg, raw=False)
        return resp

    def sampling_generate(self, instruction, input_text, state_file, token_count=1200, temperature=0.3,
                          top_p=0.2,template_prompt=None, base_model_path=None):
        cmd = {
            "cmd": "SAMPLING_GENERATE",
            "instruction": instruction,
            "input_text": input_text,
            "token_count": token_count,
            "top_p": top_p,
            "state_file": state_file,
            "temperature": temperature,
            "template_prompt": template_prompt,
            "base_model_path": base_model_path

        }
        self.socket.send(msgpack.packb(cmd, use_bin_type=True))
        msg = self.socket.recv()
        resp = msgpack.unpackb(msg, raw=False)
        return resp


    def reload_base_model(self, base_model_path):
        cmd = {
            "cmd": "RELOAD_BASE_MODEL",
            "base_model_path": base_model_path
        }
        self.socket.send(msgpack.packb(cmd, use_bin_type=True))
        self.socket.recv()
        return True
