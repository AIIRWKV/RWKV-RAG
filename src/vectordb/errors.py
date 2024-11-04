#coding: utf-8

class VectorDBError(Exception):
    """
    向量数据库自定义异常类
    """
    def __init__(self, message="未知错误"):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return self.message


class VectorDBCollectionNotExistError(VectorDBError):
    """
    集合不存在
    """
    def __init__(self, message="集合不存在"):
        self.message = message
        super().__init__(self.message)


class VectorDBCollectionExistError(VectorDBError):
    """
    集合已存在
    """
    def __init__(self, message="集合已存在"):
        self.message = message
        super().__init__(self.message)