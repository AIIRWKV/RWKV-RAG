import threading
import json
import traceback
from typing import List
import sqlite3

status_table_name = 'file_status' # 记录文件信息
create_status_table_sql = ("create table if not exists file_status "
                           "(file_path text NOT NULL, "
                           "collection_name text NOT NULL, "
                           "status text, "
                           "last_updated text NULL, "
                           "primary key(collection_name,file_path))")

create_base_model_table_sql = ("create table if not exists base_model_status "
                           "(name text NOT NULL, "
                           "path text, "
                           "status INTEGER DEFAULT 0, "  # 0 下线  1 上线
                           "create_time text NULL, "
                           "primary key(name))")

create_using_base_model_table_sql = ("create table if not exists base_model_using_base_model "
                                     "(id INTEGER PRIMARY KEY AUTOINCREMENT,"
                                     "name text NOT NULL)")

create_search_history_table_sql = ("create table if not exists search_history "
                           "(id INTEGER PRIMARY KEY AUTOINCREMENT,"
                            "collection_name text NOT NULL, "
                           "query text NOT NULL, "
                            "recall_msg text,"
                           "match_best text,"
                           "create_time text NULL, "
                           " UNIQUE (collection_name, query))")

create_chat_history_table_sql_list = ['create table if not exists chat_history_0 (id INTEGER PRIMARY KEY AUTOINCREMENT,search_id INTEGER NOT NULL, chat text not null, create_time text NULL)',
                                      'create table if not exists chat_history_1 (id INTEGER PRIMARY KEY AUTOINCREMENT,search_id INTEGER NOT NULL, chat text not null, create_time text NULL)',
                                      'create table if not exists chat_history_2 (id INTEGER PRIMARY KEY AUTOINCREMENT,search_id INTEGER NOT NULL, chat text not null, create_time text NULL)',
                                      'create table if not exists chat_history_3 (id INTEGER PRIMARY KEY AUTOINCREMENT,search_id INTEGER NOT NULL, chat text not null, create_time text NULL)',
                                      'create table if not exists chat_history_4 (id INTEGER PRIMARY KEY AUTOINCREMENT,search_id INTEGER NOT NULL, chat text not null, create_time text NULL)']


valid_status = ['unprocess', 'waitinglist','processing','processed','failed']


class SqliteDB:
    def __init__(self,db_path) -> None:
        self.db_path = db_path
        self.connection = None
        self.cursor = None

    def __enter__(self):
        try:
            self.connection = sqlite3.connect(database=self.db_path)
            self.cursor = self.connection.cursor()
            return self.cursor
        except Exception as ex:
            traceback.print_exc()
            raise ex

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if not exc_type is None:
                self.connection.rollback()
                return False
            else:
                self.connection.commit()
        except Exception as ex:
            traceback.print_exc()
            raise ex
        finally:
            self.cursor.close()
            self.connection.close()


class FileStatusManager:

    init_once = False
    lock = threading.Lock()
    def __init__(self,db_path: str, default_base_model_path:str) -> None:
        self.db_path = db_path
        self.default_base_model_path = default_base_model_path
        with FileStatusManager.lock:
            if not FileStatusManager.init_once:
                self.init_tables()
                FileStatusManager.init_once = True

    def init_tables(self):
        default_base_model_path = self.default_base_model_path

        with SqliteDB(self.db_path) as db:
            db.execute(create_status_table_sql)
            db.execute(create_base_model_table_sql)
            db.execute(create_using_base_model_table_sql)
            db.execute(create_search_history_table_sql)
            for sql in create_chat_history_table_sql_list:
                db.execute(sql)
            try:
                # 将配置文件的基底模型添加到管理界面
                db_base_model = self.get_using_base_model()
                config_base_model_name = self.get_base_model_name_by_path(default_base_model_path)
                if not db_base_model and config_base_model_name:
                    self.create_or_update_using_base_model(config_base_model_name, None)
                elif not db_base_model and not config_base_model_name:
                    self.create_or_update_base_model('default', default_base_model_path, 1)
                    self.create_or_update_using_base_model('default', None)
                elif db_base_model and not config_base_model_name:
                    self.create_or_update_base_model('default', default_base_model_path, 1)
                    self.create_or_update_using_base_model('default', db_base_model[0])
                else:
                    if db_base_model[1] != config_base_model_name:
                        self.create_or_update_using_base_model(config_base_model_name, db_base_model[0])
            except:
                pass

    def add_file(self,file_path, collection_name, status='processed'):
        with SqliteDB(self.db_path) as db:
            if self.check_file_exists(file_path, collection_name):
                return 0
            db.execute(f"insert into {status_table_name} (file_path,collection_name,status,last_updated)"
                       f" values (?,?,?,datetime('now', 'localtime'))",(file_path,collection_name,status))
        return 1

    def check_file_exists(self,file_path, collection_name):
        with SqliteDB(self.db_path) as db:
            db.execute(f"select count(1) from {status_table_name} where collection_name = ? "
                           f"and file_path = ?",(collection_name, file_path))
            result = db.fetchone()
            return result[0] > 0

    def update_file_status(self,file_path, collection_name, status):
        with SqliteDB(self.db_path) as db:
            db.execute(f"update {status_table_name} set status = ?,last_updated = datetime('now', 'localtime') where collection_name = ? "
                           f"and file_path = ?",(status,collection_name,file_path))
            return db.rowcount

    def get_collection_files(self, collection_name, page:int=1, page_size:int=100, keyword:str=None):
        """
        获取加入知识库的文件列表
        """
        with SqliteDB(self.db_path) as db:
            if not keyword:
                db.execute(f"select file_path, last_updated, status from {status_table_name} where collection_name = ? limit ? offset ?",
                       (collection_name, page_size, page * page_size - page_size))
            else:
                db.execute(f"select file_path, last_updated, status from {status_table_name} where collection_name = ? and file_path like ? limit ? offset ?",
                       (collection_name, '%'+keyword+'%', page_size, page * page_size - page_size))
            result = db.fetchall()
            return result

    def get_collection_files_count(self, collection_name, keyword:str=None):
        """
        获取加入知识库的文件列表
        """
        with SqliteDB(self.db_path) as db:
            if not keyword:
                db.execute(f"select count(1) from {status_table_name} where collection_name = ? ",
                       (collection_name,))
            else:
                db.execute(f"select count(1) from {status_table_name} where collection_name = ? and file_path like ? ?",
                       (collection_name, '%'+keyword+'%'))
            result = db.fetchone()
            return result[0]

    def collection_files_count(self):
        with SqliteDB(self.db_path) as db:
            db.execute(f"select collection_name,count(1) AS total from {status_table_name} group by collection_name")
            result = db.fetchall()
            return result


    def check_search_history_exist(self, collection_name: str, query: str):
        """
        检查是否已经召回过
        :return:
        """
        with SqliteDB(self.db_path) as db:
            db.execute(f"select count(1) from search_history where collection_name = ? and query = ?",
                       (collection_name, query))
            result = db.fetchone()
            return result[0]
    def get_search_history_id_by_query(self, collection_name: str, query: str):
        """
        获取id
        :return:
        """
        with SqliteDB(self.db_path) as db:
            db.execute(f"select id from search_history where collection_name = ? and query = ?",
                       (collection_name, query))
            result = db.fetchone()
            if result:
                return result[0]
            else:
                return 0

    def add_search_history(self, collection_name: str, query: str, recall_result: List[str], match_best: str):
        """
        添加召回信息
        :return:
        """
        new_id = self.check_search_history_exist(collection_name, query)
        if new_id > 0:
            return new_id
        with SqliteDB(self.db_path) as db:
            db.execute(f'insert into search_history (collection_name,query,recall_msg,match_best,create_time)'
                           f' values (?,?,?,?,datetime("now", "localtime"))',
                           (collection_name, query, json.dumps(recall_result, ensure_ascii=False), match_best))
            db.execute(f'select id from search_history where collection_name = ? and query = ? ',
                       (collection_name, query))
            new_id = db.fetchone()[0]
            return new_id

    def update_search_history(self, search_id: int, **kwargs):
        is_update = False
        update_sql = f"update search_history set  "
        update_sql_list = []
        params = []
        if 'recall_msg' in kwargs:
            recall_msg = kwargs.get('recall_msg') or ''
            is_update = True
            update_sql_list.append(f'recall_msg = ?')
            params.append(recall_msg)
        if 'match_best' in kwargs:
            match_best = kwargs.get('match_best') or ''
            is_update = True
            update_sql_list.append(f'match_best = ?')
            params.append(match_best)
        if is_update:
            sql = update_sql + ','.join(update_sql_list) + ' where id = ?'
            params.append(search_id)
            with SqliteDB(self.db_path) as db:
                db.execute(sql, params)

    def delete_search_history(self, collection_name:str, query: str, delete_search=True):
        history_id = self.get_search_history_id_by_query(collection_name, query)
        if history_id > 0:
            table_id = history_id % 5
            with SqliteDB(self.db_path) as db:
                if delete_search:
                    db.execute(f'delete from search_history where id = ?', (history_id,))
                db.execute(f'delete from chat_history_{table_id} where search_id = ?', (history_id,))
        return history_id

    def get_collection_search_history(self, collection_name: str, limit: int=1000):
        with SqliteDB(self.db_path) as db:
            db.execute(f"select id,collection_name,query,create_time from search_history where collection_name = ? limit ? ",
                       (collection_name, limit))
            result = db.fetchall()
            return result

    def get_collection_search_history_info(self, search_id:int):
        with SqliteDB(self.db_path) as db:
            db.execute(f"select id,collection_name,query,recall_msg,match_best,create_time from search_history where id = ?",
                       (search_id,))
            result = db.fetchone()
            return result

    def add_chat(self, search_id: int, chat_text: str):
        """
        :param search_id:
        :param chat_text: [{"role":"user","content":instruct}, {"role":"assistant","content":response}]
        :return:
        """
        if search_id > 0:
            with SqliteDB(self.db_path) as db:
                db.execute(f'insert into chat_history_{search_id % 5} (search_id,chat,create_time)'
                       f' values (?,?,datetime("now", "localtime"))',(search_id,chat_text))

    def get_chat_list(self, search_id: int, page: int=1, page_size: int=100):
        with SqliteDB(self.db_path) as db:
            db.execute(f"select id,chat from chat_history_{search_id % 5} where search_id = ? order by id DESC limit ? offset ? ",
                       (search_id, page_size, (page - 1) * page_size))
            result = db.fetchall()
            return result


    def add_base_model(self,name,path):
        with SqliteDB(self.db_path) as db:
            if self.check_file_exists(path, name):
                return 0
            db.execute(f"insert into base_model_status (name,path,status,create_time)"
                       f" values (?,?,?,datetime('now', 'localtime'))",(name,path,0))
        return 1

    def change_base_model(self,name,path):
        with SqliteDB(self.db_path) as db:
            db.execute(f"update base_model_status set path = ? where name = ?",(path,name))
            return 1
    def create_or_update_base_model(self,name,path, status):
        with SqliteDB(self.db_path) as db:
            if self.check_base_model_exists(name):
                db.execute(f"update base_model_status set path = ?,status =? ,create_time"
                           f" = datetime('now', 'localtime') where name = ?",(path,status,name))
            else:
                db.execute(f"insert into base_model_status (name,path,status,create_time)"
                           f" values (?,?,?,datetime('now', 'localtime'))",(name,path,status))

    def check_base_model_exists(self, name):
        with SqliteDB(self.db_path) as db:
            db.execute(f"select count(1) from base_model_status where name = ?",(name,))
            result = db.fetchone()
            return result[0] > 0


    def get_base_model_list(self, just_name=False):
        with SqliteDB(self.db_path) as db:
            if just_name:
                db.execute(f"select name from base_model_status where status = 1 and name != 'default' ")
                result = db.fetchall()
                return ['default'] + [x[0] for x in result]
            else:
                db.execute(f"select name,path,status, create_time from base_model_status")
                result = db.fetchall()
                return result

    def get_base_model_name_by_path(self,path):
        with SqliteDB(self.db_path) as db:
            db.execute(f"select name from base_model_status where path = ? and status = 1",(path,))
            result = db.fetchone()
            return result[0] if result else None

    def get_base_model_path_by_name(self,name):
        with SqliteDB(self.db_path) as db:
            db.execute(f"select path, status from base_model_status where name = ?",(name,))
            result = db.fetchone()
            return result if result else None

    def active_base_model(self,name):
        with SqliteDB(self.db_path) as db:
            db.execute(f"update base_model_status set status = 1 where name = ?",(name,))
            return 1

    def offline_base_model(self,name):
        with SqliteDB(self.db_path) as db:
            db.execute(f"update base_model_status set status = 0 where name = ?",(name,))
            return 1

    def get_using_base_model(self):
        with SqliteDB(self.db_path) as db:
            db.execute(f"select id, name from base_model_using_base_model order by id ASC limit 1")
            result = db.fetchone()
            return result if result else None

    def create_or_update_using_base_model(self, name, model_id=None):
        if model_id is None:
            result = self.get_using_base_model()
            if result is None:
                with SqliteDB(self.db_path) as db:
                    db.execute(f"insert into base_model_using_base_model (name) values (?)",(name,))
                    return 1
            else:
                model_id = result[0]
                if name != result[1]:
                    with SqliteDB(self.db_path) as db:
                        db.execute(f"update base_model_using_base_model set name = ? where id = ?",(name,model_id))
                        return 1
        else:
            with SqliteDB(self.db_path) as db:
                db.execute(f"update base_model_using_base_model set name = ? where id = ?",(name,model_id))
                return 1
