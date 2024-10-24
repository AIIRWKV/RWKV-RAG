import time
import subprocess
from datetime import datetime
from multiprocessing import Lock

import chromadb

from src.services import AbstractServiceWorker
from src.clients import LLMClient


CHROMA_DB_COLLECTION_NAME = 'initial'

    
class ServiceWorker(AbstractServiceWorker):

    lock = Lock()

    def init_with_config(self, config):
        
        llm_front_end_url = config.get("llm_front_end_url", '')
        self.llm_client = LLMClient(llm_front_end_url)
        chroma_port = config["chroma_port"]
        chroma_host = config["chroma_host"]

        self.chroma_host = chroma_host
        self.chroma_port = chroma_port
        self.init_chroma_db()

    def init_chroma_db(self):
        """
        Init the chromadb
        """
        if self.lock.acquire(False):
            try:
                chroma_client = chromadb.HttpClient(host=self.chroma_host,
                                                port=self.chroma_port)
                if CHROMA_DB_COLLECTION_NAME not in [c.name for c in chroma_client.list_collections()]:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    chroma_client.create_collection(CHROMA_DB_COLLECTION_NAME,
                                                metadata={"hnsw:space": "cosine",
                                                          "create_time": now})
                    print(f"Chroma db collection {CHROMA_DB_COLLECTION_NAME} is created")
                    print(f"Chroma db collection {CHROMA_DB_COLLECTION_NAME} is ready")
                    print(f'Current collections are {chroma_client.list_collections()}')
                del chroma_client
            finally:
                self.lock.release()

    @staticmethod
    def init_once(config):
        if config.get('docker'):
            # 如果是docker部署的话，不需要检查
            return
        # 检测chroma db是否已启动
        command1 = "ps -ef | grep '{}'".format("chroma")
        output = subprocess.check_output(command1, shell=True, text=True)
        processes = [line for line in output.split('\n')]
        for o in processes:
            if 'chroma run ' in o:
                print("chroma db is running")
                return True

        chroma_path = config.get("chroma_path")
        chroma_port = config.get("chroma_port")
        chroma_host = config.get("chroma_host")
        print(f"Start chroma db")
        # spawn a process "chroma run --path chroma_path --port chroma_port --host chroma_host"
        command = f"chroma run --path {chroma_path} --port {chroma_port} --host {chroma_host}"
        process = subprocess.Popen(command, shell=True)
        print(f"Started indexing service with command {command}, pid is {process.pid}")
        time.sleep(5)

    def cmd_index_texts(self, cmd: dict):
        keys = cmd["keys"]
        values = cmd["texts"]
        collection_name = cmd['collection_name']
        embeddings = self.llm_client.encode(values)["value"]

        chroma_client = chromadb.HttpClient(host=self.chroma_host,
                                            port=self.chroma_port)

        collection = chroma_client.get_collection(collection_name)

        collection.add(
            ids=keys,
            embeddings=embeddings,
            documents=values
        )
        # index the value
        return True

    def cmd_show_collections(self, cmd: dict):
        # TODO 如果集合数太多，要做分页处理
        chroma_client = chromadb.HttpClient(host=self.chroma_host,
                                            port=self.chroma_port)
        collections = chroma_client.list_collections()

        return [(i.name, i.metadata) for i in collections]

    def cmd_create_collection(self, cmd: dict):
        collection_name = cmd['collection_name']
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        chroma_client = chromadb.HttpClient(host=self.chroma_host,
                                            port=self.chroma_port)
        chroma_client.create_collection(collection_name,
                                        metadata={"hnsw:space": "cosine",
                                                  "create_time": now})
        return True

    def cmd_delete_collection(self, cmd: dict):
        collection_name = cmd['collection_name']
        chroma_client = chromadb.HttpClient(host=self.chroma_host,
                                            port=self.chroma_port)
        chroma_client.delete_collection(collection_name)
        return True

    def cmd_search_nearby(self, cmd: dict):
        text = cmd["text"]
        collection_name = cmd.get('collection_name')
        embedings = self.llm_client.encode([text])["value"]
        print(f"Searching nearby for {text} with embeddings {embedings}")
        chroma_client = chromadb.HttpClient(host=self.chroma_host,
                                            port=self.chroma_port)
        collection = chroma_client.get_collection(collection_name or CHROMA_DB_COLLECTION_NAME)
        search_result = collection.query(
            query_embeddings=embedings,
            n_results=3,
            include=['documents', 'distances'])
        return search_result

def process(self, cmd):
    cmd_name = cmd.get('cmd', '').lower()
    function_name = f'cmd_{cmd_name}'
    if hasattr(self, function_name) and callable(getattr(self, function_name)):
        return getattr(self, function_name)(cmd)
    return ServiceWorker.UNSUPPORTED_COMMAND

