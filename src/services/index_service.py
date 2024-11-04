from multiprocessing import Lock

from src.services import AbstractServiceWorker
from src.vectordb import INIT_VECTORDB_COLLECTION_NAME


class ServiceWorker(AbstractServiceWorker):
    lock = Lock()

    def init_with_config(self, config: dict):
        # 向量数据库相关配置
        self.vectordb_name = config.get("vectordb_name")
        self.vectordb_port = config.get("vectordb_port")
        self.vectordb_host = config.get("vectordb_host", )
        self.vectordb_path = config.get("vectordb_path")
        self.vectordb_manager = None  # 管理器
        self.init_vectordb_db()

    def init_vectordb_db(self):
        """
        Init the vectordb
        """
        if self.lock.acquire(False): # TODO 集群模式的话需加分布式锁
            try:
                manager = self.vectordb_manager
                if not manager.has_collection(INIT_VECTORDB_COLLECTION_NAME):
                    manager.create_collection(INIT_VECTORDB_COLLECTION_NAME)
                    print(f"{self.vectordb_name} collection {INIT_VECTORDB_COLLECTION_NAME} is created")
                    print(f"{self.vectordb_name} collection {INIT_VECTORDB_COLLECTION_NAME} is ready")
            finally:
                self.lock.release()

    # def init_once(self):
    #     # 启动本地向量数据库服务
    #     if self.vectordb_name == 'chromadb':
    #         from src.vectordb import ChromaDBManager
    #         self.vectordb_manager = ChromaDBManager(self.vectordb_path, self.vectordb_port)
    #     else:
    #         raise VectorDBError(f'暂时不支持向量数据库类型:{self.vectordb_name}')
    #     self.vectordb_manager.run()
    #     time.sleep(5)

    def index_texts(self, cmd: dict):
        return self.vectordb_manager.add(cmd)

    def show_collections(self, cmd: dict):
        return self.vectordb_manager.show_collections(cmd)

    def create_collection(self, cmd: dict):
        collection_name = cmd['collection_name']
        return self.vectordb_manager.create_collection(collection_name)

    def delete_collection(self, cmd: dict):
        collection_name = cmd['collection_name']
        return self.vectordb_manager.delete_collection(collection_name)

    def search_nearby(self, cmd: dict):
        return self.vectordb_manager.search_nearby(cmd)


