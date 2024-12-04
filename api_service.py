# coding=utf-8
"""
API Service
"""

import asyncio
import json
import os
import re
from datetime import date, datetime
from typing import List

import aiohttp
import uvicorn
from fastapi import Request, APIRouter
from fastapi.responses import FileResponse

from src.clients.index_client import IndexClient
from src.clients.llm_client import LLMClient
from src.clients import FileStatusManager
from configuration import ClientConfig
from src.diversefile import Loader
from src.diversefile import search_on_baike
from src.utils.tools import quote_filename, get_random_string, number_list_max


project_config = ClientConfig('etc/ragq.yml')

parent_dir = project_config.config.get('base', {}).get('knowledge_base_path')
default_knowledge_base_dir = os.path.join(parent_dir, "knowledge_data") # 默认联网知识的存储位置
if not os.path.exists(default_knowledge_base_dir):
    os.makedirs(default_knowledge_base_dir)

_sqlite_db_path = os.path.join(default_knowledge_base_dir, 'files_services.db')


class APIService:
    """
    API Service
    """
    api_service_router = APIRouter(prefix='/api',
                   responses={404: {"description": "Item not found"}})

    index_client  = None
    llm_client = None
    file_status_manager = None
    llm_service_config = None

    # FileStatusManager(_sqlite_db_path,
    #                                         {'default_base_model_path': default_base_model_path})

    @classmethod
    def get_index_client(cls):
        if cls.index_client is None:
            index_client_front_end = project_config.config.get('index', {}).get('front_end', {})
            index_client_tcp = '%s://%s:%s' % (index_client_front_end.get('protocol', 'tcp'),
                                               index_client_front_end.get('host', 'localhost'),
                                               index_client_front_end.get('port', '7783'))
            index_client = IndexClient(index_client_tcp)
            cls.index_client = index_client
            return index_client

        return cls.index_client

    @classmethod
    def get_llm_client(cls):
        if cls.llm_client is None:
            llm_client_front_end = project_config.config.get('llm', {}).get('front_end', {})
            llm_client_tcp = '%s://%s:%s' % (llm_client_front_end.get('protocol', 'tcp'),
                                             llm_client_front_end.get('host', 'localhost'),
                                             llm_client_front_end.get('port', '7781'))
            llm_client = LLMClient(llm_client_tcp)
            cls.llm_client = llm_client
            return llm_client
        return cls.llm_client

    @classmethod
    def get_file_status_manager(cls):
        if cls.file_status_manager is None:
            llm_service_config = APIService.get_llm_service_config()
            default_base_model_path = llm_service_config.get('base_model_path')
            files_status_manager = FileStatusManager(_sqlite_db_path,
                                                     {'default_base_model_path': default_base_model_path})
            cls.file_status_manager = files_status_manager
            return files_status_manager
        return cls.file_status_manager

    @classmethod
    def get_llm_service_config(cls):
        if cls.llm_service_config is None:
            llm_client = APIService.get_llm_client()
            llm_service_config = llm_client.llm_config()
            cls.llm_service_config = llm_service_config
            return llm_service_config
        return cls.llm_service_config



    @api_service_router.get('/ok')
    async def ok(self):
        return {"code": 200, "msg": "ok", "data": {}}

    @api_service_router.get('/knowledgebase/list')
    async def get_collection_list(self, keyword: str=None, need_count: bool=False):
        """
        获取知识库列表
        """
        index_client = APIService.get_index_client()
        collection_list = index_client.show_collections()
        if need_count:
            files_status_manager = APIService.get_file_status_manager()
            collection_counts = files_status_manager.collection_files_count()
            collection_counts_dict = {i[0]: i[1] for i in collection_counts}
        else:
            collection_counts_dict = {}
        if keyword:
            return {'code': 200, 'data': [{'name': i[0], 'meta': i[1], 'count': collection_counts_dict.get(i[0], 0)} for i in collection_list if keyword in i[0]], 'msg': 'ok'}
        return {'code': 200, 'data': [{'name': i[0], 'meta': i[1], 'count': collection_counts_dict.get(i[0], 0)} for i in collection_list], 'msg': 'ok'}


    @api_service_router.post('/knowledgebase/add')
    async def add_collection(self, body: dict):
        """
        添加知识库
        """
        name = body.get('name')
        if not name:
            return {"code": 400, "msg": '知识库名称不能为空', "data": {}}
        collection_name_rule = r'^[a-zA-Z0-9][a-zA-Z0-9_]{1,31}[a-zA-Z0-9]$'
        if not re.match(collection_name_rule, name):
            return {"code": 400, "msg": '知识库名称不合法,长度3-32的英文字符串', "data": {}}
        index_client = APIService.get_index_client()
        if index_client.has_collection():
            return {"code": 400, "msg": '知识库已存在', "data": {}}
        try:
            index_client.create_collection(name)
        except Exception as e:
            return {"code": 400, "msg": "创建知识库失败:%s" % str(e), "data": {}}
        return {"code": 200, "msg": 'ok', "data": {}}


    @api_service_router.get('/knowledgebase/delete')
    async def delete_collection(self, name: str):
        """
        删除知识库
        """
        if not name:
            return {"code": 400, "msg": '知识库名称不能为空', "data": {}}
        index_client = APIService.get_index_client()
        try:
            index_client.delete_collection(name)
        except Exception as e:
            return {"code": 400, "msg": "删除知识库失败:%s" % str(e), "data": {}}
        return {"code": 200, "msg": 'ok', "data": {}}


    @api_service_router.get('/knowledgebase/file_list')
    async def get_collection_file_list(self, name: str, page: int=1, page_size: int=100, keyword: str=None):
        """
        获取知识库下所有知识文件列表
        """
        files_status_manager = APIService.get_file_status_manager()
        file_list = files_status_manager.get_collection_files(name, page=page, page_size=page_size, keyword=keyword)
        if file_list:
            result = [{'file_path': item[0], 'create_time': item[1], 'status': item[2] if item[2] else 'processed'} for item in file_list]
        else:
            result = []
        return {"code": 200, "msg": 'ok', "data": result}


    @api_service_router.get('/knowledgebase/file_list_count')
    async def get_collection_file_list_count(self, name: str, keyword: str=None):
        """
        获取知识库下所有知识文件数量
        """
        files_status_manager = APIService.get_file_status_manager()
        count = files_status_manager.get_collection_files_count(name, keyword=keyword)
        return {"code": 200, "msg": 'ok', "data": count}


    @api_service_router.get('/knowledgebase/internet_search')
    async def internet_search(self, query: str):
        """
        联网搜索
        """
        if not query:
            return {"code": 400, "msg": '请输入搜索关键词', "data": {}}
        output_filename = '%s.txt' % quote_filename(query)
        date_str = date.today().strftime("%Y%m%d")
        output_dir = os.path.join(default_knowledge_base_dir, date_str)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        try:
            txt, filepath = search_on_baike(query, output_dir, output_filename)
            return {'code': 200, 'data': {'file_path': filepath, 'text': txt}, 'msg': 'ok'}
        except Exception as e:
            return {"code": 400, "msg": "发生错误: %s" % str(e), "data": {}}


    @api_service_router.post('/knowledgebase/archive_text')
    async def archive_text_knowledgebase(self, body: dict):
        """
        手动输入知识入库
        """
        name = body.get('name')
        text = body.get('text')
        file_name = body.get('file_name')
        if not (name and isinstance(text, str) and text and isinstance(name, str)):
            return {"code": 400, "msg": '知识库名称和文本内容不能为空', "data": {}}
        payload_texts = text.split("\n")
        success_num = 0
        failed_num = 0
        if not file_name:
            output_filename = 'manual_input_%s.txt' % get_random_string(6)
        else:
            if not isinstance(file_name, str):
                return {"code": 400, "msg": '文件名必须是字符串', "data": {}}
            output_filename = '%s_%s.txt' % (file_name, get_random_string(6))
        date_str = date.today().strftime("%Y%m%d")
        output_dir = os.path.join(default_knowledge_base_dir, date_str)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        output_file = os.path.join(output_dir, output_filename)
        llm_client = APIService.get_llm_client()
        index_client = APIService.get_index_client()
        with open(output_file, 'w', encoding='utf-8') as wf:
            for idx, chunk in enumerate(payload_texts):
                tmp = [chunk]
                embeddings = llm_client.get_embeddings(tmp)
                try:
                    index_client.index_texts( tmp, embeddings, collection_name=name)
                    success_num += 1
                except Exception as e:
                    failed_num += 1
                    continue
                wf.write(chunk)
                wf.write('\n')
        files_status_manager = APIService.get_file_status_manager()
        if failed_num > 1.5 * success_num:
             files_status_manager.add_file(output_file, name, 'failed')
        else:
            files_status_manager.add_file(output_file, name)
        return {"code": 200, "msg": 'ok', "data": {'success_num': success_num, 'failed_num': failed_num,
                                                   'file_path': output_file}}


    @api_service_router.post('/knowledgebase/archive_file')
    async def archive_file_knowledgebase(self, body: dict):
        """
        文件入库
        """
        name: str = body.get('name')
        file_path: str = body.get('file_path')
        file_name : str = body.get('file_name')
        chunk_size: int = 256 #body.get('chunk_size', 256)

        if not (name and file_path and isinstance(file_path, str) and isinstance(name, str)):
            return {"code": 400, "msg": '知识库名称和文件路径不能为空', "data": {}}

        if not (isinstance(chunk_size, int) and 100<chunk_size<=1024):
            return {"code": 400, "msg": '分词长度不合法，请输入100-1024的整数', "data": {}}
        file_path = file_path.strip()
        if not os.path.exists(file_path):
            return {"code": 400, "msg": f'文件{file_path}不存在', "data": {}}


        try:
            loader = Loader(file_path, chunk_size)
        except Exception as e:
            return {"code": 400, "msg": "文件加载和分割过程中出现错误: %s" % str(e), "data": {}}

        date_str = date.today().strftime("%Y%m%d")
        output_dir = os.path.join(default_knowledge_base_dir, date_str)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        chunks = loader.load_and_split_file(output_dir, file_name)
        success_num = 0
        failed_num = 0
        llm_client = APIService.get_llm_client()
        index_client = APIService.get_index_client()
        for idx, chunk in enumerate(chunks):
            tmp = [chunk]
            embeddings = llm_client.get_embeddings(tmp)
            try:
                index_client.index_texts(tmp, embeddings, collection_name=name)
                success_num += 1
            except Exception as e:
                failed_num += 1

        # 记录文件入库状态
        files_status_manager = APIService.get_file_status_manager()
        if failed_num > 1.5 * success_num:
            files_status_manager.add_file(file_path,name, 'failed')
        else:
            files_status_manager.add_file(file_path , name)
        return {"code": 200, "msg": 'ok', "data": {'success_num': success_num, 'failed_num': failed_num,
                                                   'file_path': [loader.output_path]}}



    @api_service_router.get('/knowledgebase/recall')
    async def search_nearby(self, name: str, query: str, is_new:bool = False):
        """
        知识检索召回
        """
        query = query.strip()
        name = name.strip()
        if not query:
            return {"code": 400, "msg": '请输入检索内容', "data": {}}
        if not name:
            return {"code": 400, "msg": '请选择知识库', "data": {}}
        llm_client = APIService.get_llm_client()
        embeddings = llm_client.get_embeddings([query])
        index_client = APIService.get_index_client()
        try:
            documents = index_client.search_nearby(embeddings, name)
        except Exception as e:
           return {"code": 400, "msg": "召回数据失败:%s" % str(e), "data": {}}

        if documents:
            # 计算最佳匹配值
            cross_scores = llm_client.get_cross_scores({"texts_0": documents,
                                                                "texts_1": [query for i in documents],
                                                                "rerank_path": project_config.default_rerank_path})
            max_value, max_index = number_list_max(cross_scores)
            if is_new:
                # 重新召回删除所有的记录
                search_id = files_status_manager.delete_search_history(name, query, delete_search=False)
                files_status_manager.update_search_history(search_id,
                                                           recall_msg=json.dumps(documents,ensure_ascii=False),
                                                           match_best=documents[max_index])
            else:
                search_id = files_status_manager.add_search_history(name, query, documents, documents[max_index])
        else:
           return {"code": 400, "msg": '相关问题找回失败，换一个问题试试！', }

        return {"code": 200, "msg": 'ok', "data": {'search_id': search_id}}

@api_service_router.post('/api/knowledgebase/search_history_delete')
async def search_history_delete(body: dict):
    """
    删除检索历史
    """
    name: str = body.get('name') or ''
    query: str = body.get('query') or ''
    name = name.strip()
    query = query.strip()
    if name and query:
        files_status_manager.delete_search_history(name, query)
        return {"code": 200, "msg": 'ok', "data": {}}
    else:
        return {"code": 400, "msg": '知识库名称和检索内容不能为空', "data": {}}

@api_service_router.get('/api/knowledgebase/search_history_list')
async def knowledge_search_history(name: str):
    """
    获取检索历史
    """
    data = files_status_manager.get_collection_search_history(name)
    result = [{'search_id': line[0], 'collection_name': line[1], 'query': line[2], 'create_time': line[3] } for line in data]
    return {"code": 200, "msg": 'ok', "data": result}


@api_service_router.get('/api/knowledgebase/history_chat_list')
async def knowledge_history_chat_list(search_id: int = None, page:int=1, page_size:int=20):
    """
    获取检索历史详情
    """
    lines = files_status_manager.get_chat_list(search_id, page, page_size)
    data = []
    for line in reversed(lines):
        try:
            chat = json.loads(line[1])
        except:
            continue
        data.append({'chat_id': line[0], 'chat': chat})
    return {"code": 200, "msg": 'ok', "data": data}


@api_service_router.get('/api/knowledgebase/search_history_detail')
async def knowledge_search_history_detail(search_id: int):
    """
    获取检索历史详情
    """
    item = files_status_manager.get_collection_search_history_info(search_id)
    if not item:
        return {"code": 400, "msg": '检索历史不存在', "data": {}}
    try:
        tmp = json.loads(item[3])
    except:
        tmp = item[3]
    return {"code": 200, "msg": 'ok', "data": {'search_id': item[0], 'collection_name': item[1], 'query': item[2],
                                               'recall_msg': tmp, 'match_best': item[4], 'create_time': item[5]}}


@api_service_router.post('/api/llm/get_embeddings')
async def get_embeddings(body: dict):
    """
    获取embedding
    """
    text = body.get('text')
    if not (text and isinstance(text, str)):
        return {"code": 400, "msg": '文本不能为空',}
    embeddings = llm_service_worker.get_embeddings({'texts':[text], "bgem3_path": project_config.default_embedding_path})
    return {"code": 200, "msg": 'ok', "data": embeddings.tolist()}


@api_service_router.post('/api/llm/cross_score')
async def get_cross_scores(body: dict):
    """
    文本相似度计算
    """
    atext = body.get("atext")
    btext = body.get("btext")
    if not (atext and btext and isinstance(atext, str) and isinstance(btext, str)):
        return {"code": 400, "msg": '参数不能为空', "data": []}
    cross_scores = llm_service_worker.get_cross_scores({"texts_0": [atext],
                                                        "texts_1": [btext],
                                                        "rerank_path": project_config.default_rerank_path})
    return {"code": 200, "msg": 'ok', "data": cross_scores[0] if cross_scores else None}


@api_service_router.post('/api/llm/batch_cross_score')
async def batch_get_cross_scores(body: dict):
    """
    文本相似度计算
    """
    atexts: List[str] = body.get("atexts")
    btexts: List[str] = body.get("btexts")
    if not atexts or not btexts:
        return {"code": 400, "msg": '参数不能为空', "data": []}
    if not isinstance(atexts, list) or not isinstance(btexts, list):
        return {"code": 400, "msg": '参数类型不正确', "data": []}
    if len(atexts) != len(btexts):
        return {"code": 400, "msg": '参数长度不一致', "data": []}
    cross_scores = llm_service_worker.get_cross_scores({"texts_0": atexts,
                                                        "texts_1": btexts,
                                                        "rerank_path": project_config.default_rerank_path})
    return {"code": 200, "msg": 'ok', "data": cross_scores}


@api_service_router.post('/api/llm/generate')
async def generate(body: dict):
    """
    LLM 生成答案
    """
    instruction_input: str = body.get('instruction')
    time1 = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    best_match: str = body.get('text')
    search_id :int = body.get('search_id', 0)
    if not (instruction_input and best_match and isinstance(instruction_input, str) and isinstance(best_match, str)):
        return {"code": 400, "msg": '指令和参考文本不能为空', "data": {}}
    cmd = {
        "instruction": instruction_input,
        "input_text": best_match,
        "state_file": '',
        "template_prompt": None,
        "base_model_path": None

    }
    sampling_results = llm_service_worker.sampling_generate(cmd)
    if isinstance(search_id, str) and search_id.isdigit():
        search_id = int(search_id)
    if isinstance(search_id, int):
        time2 = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        chat_text = json.dumps([{"role":"user","content":instruction_input, 'time': time1},
                                {"role":"assistant","content":sampling_results, 'time': time2}],
                               ensure_ascii=False)
        files_status_manager.add_chat(search_id, chat_text)
    return {"code": 200, "msg": 'ok', "data": sampling_results}


@api_service_router.get('/api/llm/current_usage')
async def current_usage():
    """
    当前使用模型等信息
    :return:
    """
    default_base_model_path = project_config.default_base_model_path
    default_base_model_name = files_status_manager.get_base_model_name_by_path(default_base_model_path) or 'default'
    current_strategy = project_config.config.get('strategy') or 'cuda fp16'
    return {"code": 200, "msg": 'ok', "data": {'base_model_name': default_base_model_name,
                                                 'strategy': current_strategy}}

@api_service_router.post('/api/llm/reload_base_model')
async def reload_base_model(body: dict):
    """
    重启模型
    """
    model_name: str = body.get('model_name')
    strategy: str = body.get('strategy')
    if not (model_name and isinstance(model_name, str)):
        return {"code": 400, "msg": '请输入模型名称', "data": {}}
    base_model_info = files_status_manager.get_base_model_path_by_name(model_name)
    if not base_model_info:
        return {"code": 400, "msg": '模型不存在', "data": {}}
    model_path, status = base_model_info
    if status != 1:
        return {"code": 400, "msg": '模型未上线', "data": {}}
    if not (os.path.isfile(model_path) and os.path.exists(model_path)):
        return {"code": 400, "msg": '模型文件不存在', "data": {}}
    if not strategy:
        strategy = project_config.config.get('strategy')
    try:
        llm_service_worker.reload_base_model({'base_model_path': model_path, 'strategy': strategy})
        project_config.set_config(base_model_path=model_path, strategy=strategy)
        files_status_manager.create_or_update_using_base_model(model_name)
    except Exception as e:
        return {"code": 400, "msg": '重启模型失败: %s' % str(e), "data": {}}
    return {"code": 200, "msg": 'ok', "data": {}}


@api_service_router.get('/api/llm/base_model_list')
async def get_base_model_list(just_name: bool=False):
    """
    获取基底模型列表
    """
    base_model_list = files_status_manager.get_base_model_list(just_name)
    if just_name:
        data = base_model_list
    else:
        data = [{'name': line[0], 'path': line[1], 'status': line[2], 'create_time': line[3]} for line in base_model_list]
    return {"code": 200, "msg": 'ok', "data": data}


@api_service_router.post('/api/llm/add_base_model')
async def add_base_model(body: dict):
    """
    新增基底模型
    """
    model_name: str = body.get('model_name')
    model_path: str = body.get('model_path')
    if not (model_name and isinstance(model_name, str)):
        return {"code": 400, "msg": '请输入模型名称', "data": {}}

    if not 3 <= len(model_name) <= 64:
        return {"code": 400, "msg": '模型名称长度必须在3到64个字符之间', "data": {}}
    if not (model_path and isinstance(model_path, str)):
        return {"code": 400, "msg": '请输入模型路径', "data": {}}
    if not os.path.exists(model_path):
        return {"code": 400, "msg": '模型路径不存在', "data": {}}

    code = files_status_manager.add_base_model(model_name, model_path)
    if code == 0:
        return {"code": 400, "msg": '基底模型已存在', "data": {}}
    return {"code": 200, "msg": 'ok', "data": {}}

@api_service_router.post('/api/llm/modify_base_model')
async def modify_base_model(body: dict):
    """
    修改基底模型，只能修改模型路径，不能修改模型名称
    """
    model_name: str = body.get('model_name')
    model_path: str = body.get('model_path')
    if not (model_name and isinstance(model_name, str)):
        return {"code": 400, "msg": '请输入模型名称'}
    if not (model_path and isinstance(model_path, str)):
        return {"code": 400, "msg": '请输入模型路径'}
    files_status_manager.change_base_model(model_name, model_path)
    return {"code": 200, "msg": 'ok', "data": {}}


@api_service_router.post('/api/llm/offline_base_model')
async def offline_base_model(body: dict):
    """
    下线基底模型
    """
    model_name: str = body.get('model_name')
    if not model_name:
        return {"code": 400, "msg": '请输入模型名称', "data": {}}
    if model_name == 'default':
        return {"code": 400, "msg": 'default 模型不能下线，可以通过修改default模型的路径来实现你的需求。', "data": {}}
    files_status_manager.offline_base_model(model_name)
    return {"code": 200, "msg": 'ok', "data": {}}

@api_service_router.post('/api/llm/active_base_model')
async def active_base_model(body: dict):
    """
    上线基底模型
    """
    model_name: str = body.get('model_name')
    if not model_name:
       return {"code": 400, "msg": '请输入模型名称', "data": {}}
    files_status_manager.active_base_model(model_name)
    return {"code": 200, "msg": 'ok', "data": {}}


@api_service_router.post('/api/config/modify')
async def modify_config(body: dict):
    """
    修改配置文件, 修改配置文件后需要重启服务才能生效
    """
    model_path: str = body.get('model_path')
    embedding_path: str = body.get('embedding_path')
    reranker_path: str = body.get('reranker_path')
    new_knowledge_base_path: str = body.get('knowledge_base_path')
    vectordb_path: str = body.get('vectordb_path')
    vectordb_port: str = body.get('vectordb_port')
    vectordb_name: str = body.get('vectordb_name')

    if model_path and not os.path.exists(model_path):
        return {"code": 400, "msg": '基底模型路径不存在', "data": {}}
    if embedding_path:
        if not os.path.exists(embedding_path):
            return {"code": 400, "msg": 'Embedding模型路径不存在', "data": {}}
        if not os.path.isdir(embedding_path):
            return {"code": 400, "msg": 'Embedding模型路径必须是目录', "data": {}}
    if reranker_path:
        if not os.path.exists(reranker_path):
            return {"code": 400, "msg": 'Reranker模型路径不存在', "data": {}}
        if not os.path.isdir(reranker_path):
            return {"code": 400, "msg": 'Reranker模型路径必须是目录', "data": {}}
    if new_knowledge_base_path:
        if not os.path.exists(new_knowledge_base_path):
            return {"code": 400, "msg": '知识库文件存储目录不存在', "data": {}}
        if not os.path.isdir(new_knowledge_base_path):
            return {"code": 400, "msg": '知识库文件存储目录必须是目录', "data": {}}
    if vectordb_port:
        if not ((isinstance(vectordb_port, str) and vectordb_port.isdigit()) or isinstance(vectordb_port, int)):
            return {"code": 400, "msg": 'vectordb_port 必须是数字', "data": {}}

    project_config.set_config(model_path, embedding_path, reranker_path, new_knowledge_base_path,
                                  vectordb_path, vectordb_port, vectordb_name=vectordb_name)

    return {"code": 200, "msg": 'ok', "data": {}}


# 据路径匹配的先后顺序，将静态文件放在最后
@api_service_router.get("/", response_class=FileResponse)
async def read_root():
    return FileResponse(path="frontend_out/index.html")


@api_service_router.get("/{full_path:path}")
async def serve_static_file(request: Request, full_path: str):
    # 构建文件路径
    _, ext = os.path.splitext(full_path)
    if ext:
        file_path = os.path.join("frontend_out", full_path)
    else:
        file_path = os.path.join("frontend_out", full_path + ".html")
    # 检查文件是否存在
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        # 如果文件不存在，返回 index.html
        return FileResponse("frontend_out/404.html")


SERVER_PORT = 8080

async def start_server():
    config = uvicorn.Config(app, host="0.0.0.0", port=SERVER_PORT, )
    server = uvicorn.Server(config)
    logo = r"""
                 ____  __        __ _  ____     __  ____      _      ____
                |  _ \ \ \      / /| |/ /\ \   / / |  _ \    / \    / ___|
                | |_) | \ \ /\ / / | ' /  \ \ / /  | |_) |  / _ \  | |  _
                |  _ <   \ V  V /  | . \   \ V /   |  _ <  / ___ \ | |_| |
                |_| \_\   \_/\_/   |_|\_\   \_/    |_| \_\/_/   \_\ \____|

        """
    print(logo)
    await server.serve()

async def check_server_started():
    url = f"http://127.0.0.1:{SERVER_PORT}/api/ok"
    timeout = aiohttp.ClientTimeout(total=1)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        while True:
            try:
                async with session.get(url) as response:
                    if response.status > 0:
                        return True
            except (aiohttp.ClientConnectionError, asyncio.TimeoutError):
                await asyncio.sleep(0.8)


async def main():
    await asyncio.gather(start_server(), open_browser())


if __name__ == "__main__":
    asyncio.run(main())