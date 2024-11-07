# coding=utf-8
"""
Windows  Linux都支持
"""
import uuid
from datetime import datetime

from src.vectordb import RECALL_NUMBER
from src.vectordb import AbstractVectorDBManager
from .errors import VectorDBCollectionNotExistError, VectorDBError


class ChromaDBManager(AbstractVectorDBManager):

    def client(self):
        import chromadb
        if self._client is None:
            print(self.db_host)
            try:
                self._client = chromadb.HttpClient(host=self.db_host,
                                            port=self.db_port)
                return self._client
            except Exception as e:
                raise VectorDBError('连接Chroma服务失败')
        return self._client


    def has_collection(self, collection_name: str) -> bool:
        chroma_client = self.client()
        try:
            collection = chroma_client.get_collection(collection_name)
        except:
            return False
        if collection:
            return True
        return False

    def show_collections(self, page: int=None, page_size: int=None):
        chroma_client = self.client()
        offset = (page - 1) * page_size if page is not None and page_size is not None else None
        collections = chroma_client.list_collections(page_size, offset)
        return [(i.name, i.metadata) for i in collections] if collections else []

    def create_collection(self, collection_name: str):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        client = self.client()
        client.get_or_create_collection(collection_name,
                                        metadata={"hnsw:space": "cosine",
                                            "create_time": now})
        return True

    def delete_collection(self, collection_name: str):

        client = self.client()
        try:
            client.delete_collection(collection_name)
        except:
            raise VectorDBCollectionNotExistError()
        return True

    def add(self,kwargs:dict):
        keys = kwargs.get("keys")
        values = kwargs["texts"]
        collection_name = kwargs.get('collection_name')
        embeddings = kwargs.get('embeddings')

        if keys is None or isinstance(keys, list) is False or len(keys) != len(values):
            keys = [str(uuid.uuid4()) for i in range(len(values))]
        client = self.client()
        new_embeddings = [eb for eb in embeddings]
        try:
            collection = client.get_collection(collection_name)
        except:
            raise VectorDBCollectionNotExistError()
        collection.add(
            ids=keys,
            embeddings=new_embeddings,
            documents=values
        )
        # index the value
        return True

    def search_nearby(self, kwargs: dict):
        collection_name = kwargs.get('collection_name')
        embeddings = kwargs.get('embeddings')
        client = self.client()
        try:
            collection = client.get_collection(collection_name)
        except:
            raise VectorDBCollectionNotExistError()
        search_result = collection.query(
            query_embeddings=embeddings,
            n_results=RECALL_NUMBER,
            include=['documents'])
        return search_result['documents'][0]

