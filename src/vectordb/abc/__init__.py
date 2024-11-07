#coding=utf-8
from abc import ABC, abstractmethod

VECTOR_DB_DIMENSION = 1024  # 向量维度

TEXT_MAX_LENGTH = 512  # 单个文本Embedding最大长度

RECALL_NUMBER = 3  # 召回数量
INIT_VECTORDB_COLLECTION_NAME = 'initial'
VECTORDB_USED_LIMIT = {'linux': ['chromadb', 'milvus_lite'],
                       'windows': ['chromadb']
                       }



class AbstractVectorDBManager(ABC):

    def __init__(self, db_port: int, db_host: str):
        self.db_port = db_port
        self.db_host = db_host
        self._client = None

    @abstractmethod
    def client(self):
        """
        初始化数据库连接
        :return:
        """
        pass

    @abstractmethod
    def show_collections(self, page: int=None, page_size: int=None):
        """
        集合列表
        :param page:
        :param page_size:
        :return:
        """

    @abstractmethod
    def has_collection(self, collection_name: str) -> bool:
        """
        判断集合是否存在
        :param collection_name:
        :return:
        """

    @abstractmethod
    def create_collection(self, collection_name: str):
        """
        创建集合
        :param collection_name:
        :return:
        """

    @abstractmethod
    def delete_collection(self, collection_name: str):
        """
        删除集合
        :param collection_name:
        :return:
        """

    @abstractmethod
    def add(self, kwargs: dict):
        """
        添加向量
        :param kwargs:必须有如下键
            keys： List[(str)]
            texts： List[(str)]
            collection_name： str
            embeddings: List[numpy.ndarray[numpy.float16]]
        :return:
        """

    @abstractmethod
    def search_nearby(self, kwargs: dict) -> list[str]:
        """
        搜索向量
        :param kwargs:必须有如下键：
            collection_name: str
            embeddings: List[(float)]
        :return:
        """

    @staticmethod
    def padding_vectors(vector: list):
        if len(vector) < VECTOR_DB_DIMENSION:
            vector += [0] * (VECTOR_DB_DIMENSION - len(vector))
        elif len(vector) > VECTOR_DB_DIMENSION:
            vector = vector[:VECTOR_DB_DIMENSION]
        return vector