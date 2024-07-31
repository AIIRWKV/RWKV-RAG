import traceback

import sqlite3


status_table_name = 'file_status' # 记录文件信息
create_status_table_sql = ("create table if not exists file_status "
                           "(file_path text NOT NULL, "
                           "collection_name text NOT NULL, "
                           "status text, "
                           "last_updated text NULL, "
                           "primary key(collection_name,file_path))")



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
        with SqliteDB(self.db_path) as db:
            db.execute(create_status_table_sql)

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