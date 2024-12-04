# coding=utf-8
import hashlib
import random
import string
from typing import Union, List


def calculate_string_md5(text: Union[str, bytes]):
    """
    计算字符串的md5值
    """
    if isinstance(text, str):
        text = text.encode('utf-8', errors='ignore')
    md5_hash = hashlib.md5()
    md5_hash.update(text)
    return md5_hash.hexdigest()


def quote_filename(name: str):
    """
    对于一些含有特殊字符串的进行转义，操作系统文件名不支持这些特殊字符串
    """
    if not name:
        return name
    special_chars = {
        '<': '%3C',
        '>': '%3E',
        ':': '%3A',
        '"': '%22',
        '/': '%2F',
        '\\': '%5C',
        '|': '%7C',
        '?': '%3F',
        '*': '%2A',
        ' ': ''
    }

    return ''.join([special_chars.get(n, n) for n in name])


def get_random_string(length):
    """
    获取指定长度的随机字符串
    """
    haracters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(haracters, k=length))


def number_list_max(nums:List[Union[int, float]]):
    """
    返回一个列表中最大的数字，如果列表为空，返回0
    """
    max_value = float('-inf')
    max_index = 0
    index = -1
    for value in nums:
        index += 1
        if value > max_value:
            max_value = value
            max_index = index
    return max_value, max_index