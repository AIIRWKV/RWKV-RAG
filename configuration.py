import os
import yaml

from src.core import SingletonMeta

class LLMServiceConfig(metaclass=SingletonMeta):
    def __init__(self, config_file):
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Config file {config_file} not found")
        with open(config_file) as f:
            try:
                self.config = yaml.safe_load(f)
            except yaml.YAMLError as exc:
                raise ValueError(f"Invalid config file {config_file}")
        self.config_file_path = config_file
        self.default_base_model_path = ''  # 默认基座模型路径
        self.default_bgem3_path = ''  # 默认bgem3路径
        self.default_rerank_path = ''  # 默认rerank路径
        self.default_state_path = ''  # 默认state文件
        self.validate_llm_service_config(self.config)


    def validate_llm_service_config(self, settings):
        base_model_file = settings.get("base_model_path", '')
        if not base_model_file:
            raise ValueError(f"base_model_path is required for llm service")
        if not os.path.exists(base_model_file):
            raise FileNotFoundError(f"base_model_path {base_model_file} not found for {self.config_file_path}")

        bgem3_path = settings.get("embedding_path", '')
        if not bgem3_path:
            raise ValueError(f"embedding_path is required for llm service")
        if not os.path.exists(bgem3_path):
            raise FileNotFoundError(f"embedding_path {bgem3_path} not found for {self.config_file_path}")
        rerank_path = settings.get("reranker_path", '')
        if not rerank_path:
            raise ValueError(f"reranker_path is required for llm service")
        if not os.path.exists(rerank_path):
            raise FileNotFoundError(f"reranker_path {rerank_path} not found for {self.config_file_path}")
        state_path = settings.get("state_path", '') or ''
        if state_path:
            if not os.path.exists(state_path):
                raise FileNotFoundError(f"state_path {state_path} not found for {self.config_file_path}")
        self.default_base_model_path = base_model_file.strip()
        self.default_bgem3_path = bgem3_path.strip()
        self.default_rerank_path = rerank_path.strip()
        self.default_state_path = state_path

    # def set_llm_service_config(self, base_model_path=None, embedding_path=None, reranker_path=None, state_path=None):
    #     is_save = False
    #     if base_model_path and base_model_path != self.default_base_model_path:
    #         self.default_base_model_path = base_model_path.strip()
    #         self.config['base_model_path'] = base_model_path
    #         is_save = True
    #     if embedding_path and embedding_path != self.default_bgem3_path:
    #         self.default_bgem3_path = embedding_path
    #         self.config['embedding_path'] = embedding_path
    #         is_save = True
    #     if reranker_path and reranker_path != self.default_rerank_path:
    #         self.default_rerank_path = reranker_path
    #         self.config['reranker_path'] = reranker_path
    #     if state_path and state_path != self.default_state_path:
    #         self.default_state_path = state_path
    #         self.config['state_path'] = state_path
    #         is_save = True
    #     if is_save:
    #         with open(self.config_file_path, "w") as f:
    #             yaml.dump(self.config, f)


class IndexServiceConfig(metaclass=SingletonMeta):
    def __init__(self, config_file):
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Config file {config_file} not found")
        with open(config_file) as f:
            try:
                self.config = yaml.safe_load(f)
            except yaml.YAMLError as exc:
                raise ValueError(f"Invalid config file {config_file}")
        self.config_file_path = config_file
        self.validate_index_service_config(self.config)

    def validate_index_service_config(self, settings):
        vectordb_name = settings.get("vectordb_name", '')
        vectordb_host = settings.get("vectordb_host", '')
        if not vectordb_name:
            raise ValueError(f"vectordb_name is required for index service")
        if not vectordb_host:
            raise ValueError(f"vectordb_host is required for index service")

        vectordb_port = settings.get("vectordb_port", '')
        if not (isinstance(vectordb_port, int) or (isinstance(vectordb_port, str) and vectordb_port.isdigit())):
            raise ValueError(f"vectordb_port is required for index service")

# class TuningServiceConfig(metaclass=SingletonMeta):
#     def __init__(self, config_file):
#         if not os.path.exists(config_file):
#             raise FileNotFoundError(f"Config file {config_file} not found")
#         with open(config_file) as f:
#             try:
#                 self.config = yaml.safe_load(f)
#             except yaml.YAMLError as exc:
#                 raise ValueError(f"Invalid config file {config_file}")
#         self.config_file_path = config_file


class ClientConfig(metaclass=SingletonMeta):
    def __init__(self, config_file, validate=True):
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Config file {config_file} not found")
        with open(config_file) as f:
            try:
                self.config = yaml.safe_load(f)
            except yaml.YAMLError as exc:
                raise ValueError(f"Invalid config file {config_file}")
        if validate:
            self.validate()

    def validate(self):
        """
        Validate Configuration File
        """
        base_setting = self.config.get('base', {})
        sqlite_db_path = base_setting.get("sqlite_db_path", '')
        if not sqlite_db_path:
            raise ValueError(f"sqlite_db_path is required")
        sqlite_db_path_dir = os.path.dirname(sqlite_db_path)
        if not os.path.exists(sqlite_db_path_dir):
            os.makedirs(sqlite_db_path_dir)
        knowledge_base_path = base_setting.get("knowledge_base_path", '')
        if knowledge_base_path:
            if not os.path.exists(knowledge_base_path):
                os.makedirs(knowledge_base_path)



