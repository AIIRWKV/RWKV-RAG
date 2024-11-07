import gc
import os
import traceback

import torch
from FlagEmbedding import FlagReranker, BGEM3FlagModel
from rwkv.model import RWKV as OriginRWKV
from rwkv.utils import PIPELINE, PIPELINE_ARGS

from src.services import AbstractServiceWorker

os.environ['RWKV_JIT_ON'] = '1'
os.environ['RWKV_T_MAX'] = '4096'
os.environ['RWKV_FLOAT_MODE'] = 'bf16'
os.environ['RWKV_HEAD_SIZE_A'] = '64'
os.environ['RWKV_T_MAX'] = '4096'
os.environ["RWKV_MY_TESTING"] = 'x060'
os.environ['RWKV_CTXLEN'] = '4096'


class LLMService:

    def __init__(self,
                 base_rwkv: str,
                 config: dict,
                 device='cuda',
                 dtype=torch.bfloat16,
                 **kwargs
                 ) -> None:
        """
        Args:
            base_rwkv： str， the path of rwkv model
        """

        self.base_rwkv = base_rwkv
        self.device = device
        self.dtype = dtype
        self.kwargs = kwargs
        self.config = config

        strategy = kwargs.get('strategy') or 'cuda fp16'
        self.model = OriginRWKV(base_rwkv, strategy=strategy)
        info = vars(self.model.args)
        print(f'load model from {base_rwkv},result is {info}')

        self.bgem3 = None
        self.reranker = None

        self._current_bgem3_path = ''
        self._current_reranker_path = ''
        self._current_base_model_path = self.base_rwkv
        self._current_states_path = ''
        self._current_states_value = []

    # def load_state_tuning(self, states_file):
    #     """
    #     加载state模型文件
    #     """
    #     if self._current_states_value and self._current_states_path == states_file:
    #         return self._current_states_value
    #     states = torch.load(states_file)
    #     states_value = []
    #     for i in range(self.model.args.n_layer):
    #         key = f'blocks.{i}.att.time_state'
    #         value = states[key]
    #         prev_x = torch.zeros(self.model.args.n_embd, device=self.device, dtype=torch.float16)
    #         prev_states = value.clone().detach().to(device=self.device, dtype=torch.float16).transpose(1, 2)
    #         prev_ffn = torch.zeros(self.model.args.n_embd, device=self.device, dtype=torch.float16)
    #         states_value.append(prev_x)
    #         states_value.append(prev_states)
    #         states_value.append(prev_ffn)
    #     self._current_states_value = states_value
    #     self._current_states_path = states_file
    #     return states_value

    def reload_base_model(self, base_model_path, strategy=None):
        if not os.path.exists(base_model_path):
            raise FileNotFoundError(f'Model not found at {base_model_path}')
        if base_model_path == self._current_base_model_path and self.model:
            return
        # 清除 GPU 缓存
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        self.model = None
        self._current_states_value = []
        gc.collect()
        strategy = strategy or 'cuda fp16'
        self.model = OriginRWKV(base_model_path, strategy=strategy)
        self._current_base_model_path = base_model_path

    def load_bgem3(self, bgem3_path):
        """
        Embedding 模型
        """
        if self.bgem3 is not None and self._current_bgem3_path == bgem3_path:
            return
        if not os.path.exists(bgem3_path):
            raise FileNotFoundError(f'Embedding model not found at {bgem3_path}')
        self.bgem3 = BGEM3FlagModel(bgem3_path, use_fp16=True)
        self._current_bgem3_path = bgem3_path

    def load_rerank(self, rerank_path):
        if self.reranker is not None and self._current_reranker_path == rerank_path:
            return
        if not os.path.exists(rerank_path):
            raise FileNotFoundError(f'Rerank model not found at {rerank_path}')
        self.reranker = FlagReranker(rerank_path, use_fp16=True)  # Setting use_fp16 to True speeds
        self._current_reranker_path = rerank_path

    def get_embeddings(self, inputs, bgem3_path=None):
        if isinstance(inputs, str):
            inputs = [inputs]
        if not bgem3_path:
            bgem3_path = self.config.get('embedding_path')
        self.load_bgem3(bgem3_path)
        outputs = self.bgem3.encode(inputs,
                                    max_length=512,
                                    )['dense_vecs'].tolist()  # 要进行网络传输，所以转成list

        return outputs

    def cross_encode_text(self, text_a, text_b, rerank_path=None):
        if not rerank_path:
            rerank_path = self.config.get('reranker_path')
        self.load_rerank(rerank_path)
        score = self.reranker.compute_score([text_a, text_b])
        return score

    def cross_encode_texts(self, texts_a, texts_b, rerank_path=None):
        assert len(texts_a) == len(texts_b)
        outputs = []
        for text_a, text_b in zip(texts_a, texts_b):
            outputs.append(self.cross_encode_text(text_a, text_b, rerank_path))
        return outputs

    def sampling_generate(self, instruction, input_text, state_file,
                          temperature=0.3,
                          top_p=0.2,
                          top_k=0,
                          alpha_frequency=0.5,
                          alpha_presence=0.67,
                          alpha_decay=0.996,
                          template_prompt=None,
                          base_model_path=None,
                          ):
        if base_model_path:
            self.reload_base_model(base_model_path)
        # if not state_file:
        #     state_file = self.config.get('state_path')
        # if state_file:
        #     states_value = self.load_state_tuning(state_file)
        # else:
        #     states_value = None
        states_value = None
        gen_args = PIPELINE_ARGS(temperature=temperature, top_p=top_p, top_k=top_k,  # top_k = 0 then ignore
                                 alpha_frequency=alpha_frequency,
                                 alpha_presence=alpha_presence,
                                 alpha_decay=alpha_decay,  # gradually decay the penalty
                                 token_ban=[0],  # ban the generation of some tokens
                                 token_stop=[0, 1],  # stop generation whenever you see any token here
                                 chunk_len=256)
        if not template_prompt:
            ctx = f'Instruction: {instruction}\nInput: {input_text}\n\nResponse:'
        else:
            ctx = template_prompt
        print(ctx)
        try:
            pipeline = PIPELINE(self.model, "rwkv_vocab_v20230424")
            output = pipeline.generate(ctx, token_count=1200, args=gen_args, state=states_value)
            return output
        except:
            raise ValueError(traceback.format_exc())


class LLMServiceWorker(AbstractServiceWorker):
    def init_with_config(self, config):
        base_model_file = config.get("base_model_path")  # 默认使用配置文件的模型
        self.llm_service = LLMService(base_model_file, config, strategy=config.get('strategy'))

    def cmd_llm_config(self, cmd: dict):
        """
        LLM 服务配置
        """
        return self.service_config

    def cmd_get_embeddings(self, cmd: dict):
        texts = cmd.get("texts")
        bgem3_path = cmd.get("bgem3_path")
        value = self.llm_service.get_embeddings(texts, bgem3_path)
        return value

    def cmd_get_cross_scores(self, cmd: dict):
        texts_0 = cmd.get("texts_0")
        texts_1 = cmd.get("texts_1")
        rerank_path = cmd.get("rerank_path")
        value = self.llm_service.cross_encode_texts(texts_0, texts_1, rerank_path)
        return value

    def cmd_sampling_generate(self, cmd: dict):
        instruction = cmd.get("instruction")
        input_text = cmd["input_text"]
        # temperature = cmd.get('temperature', 1.0)
        # top_p = cmd.get('top_p', 0)
        state_file = cmd.get('state_file')
        template_prompt = cmd.get('template_prompt')
        base_model_path = cmd.get('base_model_path')
        value = self.llm_service.sampling_generate(instruction, input_text, state_file,
                                                   template_prompt=template_prompt, base_model_path=base_model_path)
        return value

    def cmd_reload_base_model(self, cmd: dict):
        base_model_path = cmd.get("base_model_path")
        self.llm_service.reload_base_model(base_model_path)
        return 'ok'

    def process(self, cmd: dict):
        cmd_name = cmd.get('cmd', '').lower()
        function_name = f'cmd_{cmd_name}'
        if hasattr(self, function_name) and callable(getattr(self, function_name)):
            return getattr(self, function_name)(cmd)
        return LLMServiceWorker.UNSUPPORTED_COMMAND
