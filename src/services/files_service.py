import os
import traceback

import sqlite3

from configuration import config as project_config


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


valid_status = ['waitinglist','processing','processed','failed']


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
    def __init__(self,db_path) -> None:
        self.db_path = db_path
        self.init_tables()


    def init_tables(self):
        if os.path.exists(self.db_path):
            return
        with SqliteDB(self.db_path) as db:
            db.execute(create_status_table_sql)
            db.execute(create_base_model_table_sql)
            try:
                # 将配置文件的基底模型添加到管理界面
                if project_config.default_base_model_path:
                    self.create_or_update_base_model('default', project_config.default_base_model_path, 1)
            except:
                pass

    def add_file(self,file_path,collection_name):
        with SqliteDB(self.db_path) as db:
            if self.check_file_exists(file_path, collection_name):
                return 0
            db.execute(f"insert into {status_table_name} (file_path,collection_name,status,last_updated)"
                       f" values (?,?,?,datetime('now'))",(file_path,collection_name,'processed'))
        return 1

    def check_file_exists(self,file_path, collection_name):
        with SqliteDB(self.db_path) as db:
            db.execute(f"select count(1) from {status_table_name} where collection_name = ? "
                           f"and file_path = ?",(collection_name, file_path))
            result = db.fetchone()
            return result[0] > 0

    def get_collection_files(self, collection_name):
        with SqliteDB(self.db_path) as db:
            db.execute(f"select file_path from {status_table_name} where collection_name = ?",(collection_name,))
            result = db.fetchall()
            return [x[0] for x in result]


    def add_base_model(self,name,path):
        with SqliteDB(self.db_path) as db:
            if self.check_file_exists(path, name):
                return 0
            db.execute(f"insert into base_model_status (name,path,status,create_time)"
                       f" values (?,?,?,datetime('now'))",(name,path,0))
        return 1

    def change_base_model(self,name,path):
        with SqliteDB(self.db_path) as db:
            db.execute(f"update base_model_status set path = ? where name = ?",(path,name))
            return 1
    def create_or_update_base_model(self,name,path, status):
        with SqliteDB(self.db_path) as db:
            if self.check_base_model_exists(name):
                db.execute(f"update base_model_status set path = ?,status =? ,create_time"
                           f" = datetime('now') where name = ?",(path,status,name))
            else:
                db.execute(f"insert into base_model_status (name,path,status,create_time)"
                           f" values (?,?,?,datetime('now'))",(name,path,status))

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

    def active_base_model(self,name):
        with SqliteDB(self.db_path) as db:
            db.execute(f"update base_model_status set status = 1 where name = ?",(name,))
            return 1

    def offline_base_model(self,name):
        with SqliteDB(self.db_path) as db:
            db.execute(f"update base_model_status set status = 0 where name = ?",(name,))
            return 1
