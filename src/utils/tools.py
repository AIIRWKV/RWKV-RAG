# coding=utf-8
import hashlib
from typing import Union


def calculate_string_md5(text: Union[str, bytes]):
    """
    计算字符串的md5值
    """
    if isinstance(text, str):
        text = text.encode('utf-8')
    md5_hash = hashlib.md5()
    md5_hash.update(text)
    return md5_hash.hexdigest()