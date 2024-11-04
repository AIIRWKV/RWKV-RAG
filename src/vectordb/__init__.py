#coding: utf-8
"""
向量数据库适配层
"""
from .abc import AbstractVectorDBManager
from .abc import VECTOR_DB_DIMENSION
from .abc import VECTORDB_USED_LIMIT
from .abc import RECALL_NUMBER
from .abc import INIT_VECTORDB_COLLECTION_NAME
from .abc import TEXT_MAX_LENGTH
from .chromadb import ChromaDBManager
from .errors import VectorDBError, VectorDBCollectionNotExistError, VectorDBCollectionExistError




