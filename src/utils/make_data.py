# coding=utf-8
"""
将 jsonl 文件转化为 binidx 文件
"""

import json
import random
import os
import fileinput
import time
import string

import numpy as np

from .binidx import MMapIndexedDataset
from tokenizer.rwkv_tokenizer import TRIE_TOKENIZER


def get_random_string(length):
    haracters = string.ascii_uppercase + string.digits
    return ''.join(random.choices(haracters, k=length))

def index_file_path(prefix_path):
    return prefix_path + ".idx"


def data_file_path(prefix_path):
    return prefix_path + ".bin"


class MMapIndexedDatasetBuilder:
    """
    binidx 文件生成器
    """

    def __init__(self, out_file, dtype=np.uint16):
        self._data_file = open(out_file, "wb")
        self._dtype = dtype
        self._sizes = []
        self._doc_idx = [0]

    def add_item(self, np_array):
        assert np_array.dtype == self._dtype
        self._data_file.write(np_array.tobytes(order="C"))
        self._sizes.append(np_array.size)

    def end_document(self):
        self._doc_idx.append(len(self._sizes))

    def finalize(self, index_file):
        self._data_file.close()
        with MMapIndexedDataset.Index.writer(index_file, self._dtype) as index:
            index.write(self._sizes, self._doc_idx)


class Jsonl2Binidx:
    """
    jsonl文件转Binidx文件 用于rwkv训练
    """

    def __init__(self, jsonl_file: str, n_epoch: int, output_path: str, context_len: int=1024, is_str=False):
        """
        :param jsonl_file: jsonl文件路径 或者 符合要求的字符串
        :param n_epoch:epoch大小
        :param context_len: 上下文长度
        :param output_path: 目标文件路径
        :param is_str: 是字符串还是文件
        """
        self.jsonl_file = jsonl_file
        self.n_epoch = n_epoch
        self.context_len = context_len
        self.is_str = is_str
        if is_str:
            output_basename = get_random_string(10) + str(int(time.time()))[-4:]
            output_file_name_prefix = os.path.join(output_path, output_basename)
        else:
            output_basename = os.path.splitext(os.path.basename(jsonl_file))[0]
            output_file_name_prefix = os.path.join(output_path, output_basename)
        self.output_file_name_prefix = output_file_name_prefix
        self._tmp_file_name = '%s_make_data_temp.jsonl' % output_basename  # 临时文件
        self.builder = MMapIndexedDatasetBuilder(f"{self.output_file_name_prefix}.bin")  # binidx 文件生成器
        self._count = 0  # 当前处理数据的条数
        self.tokenizer = TRIE_TOKENIZER()

    def shuffle_jsonl_file(self):
        """
        随机打乱jsonl文件
        # TODO 目前实现方案，如果文件过大，存在性能问题，会很消耗内存，后续优化
        """
        with open(self.jsonl_file, "r", encoding="utf-8") as rf, open(self._tmp_file_name, "w", encoding="utf-8") as wf:
            non_empty_lines = [line.strip() for line in rf if line.strip()]
            print(f"### Found {len(non_empty_lines)} non-empty lines in {self.jsonl_file}")
            for i in range(self.n_epoch):
                print(f"Shuffle: {i + 1} out of {self.n_epoch}")
                random.shuffle(non_empty_lines)
                for entry in non_empty_lines:
                    wf.write(entry + "\n")

    def shuffle_jsonl_file_string(self):
        """
        按行随机打乱jsonl字符串， \n分割
        """
        with open(self._tmp_file_name, "w", encoding="utf-8") as wf:
            rf = self.jsonl_file.split("\n")
            non_empty_lines = [line.strip() for line in rf if line.strip()]
            for i in range(self.n_epoch):
                print(f"Shuffle: {i + 1} out of {self.n_epoch}")
                random.shuffle(non_empty_lines)
                for entry in non_empty_lines:
                    wf.write(entry + "\n")


    def run(self):
        """
        转换数据
        """

        print(f"### Convert input_file to {self.output_file_name_prefix}.bin/idx...")
        if self.is_str:
            self.shuffle_jsonl_file_string()
        else:
            self.shuffle_jsonl_file()
        print("### Building binidx...")

        with fileinput.input(self._tmp_file_name, encoding="utf-8") as ffff:
            for line in ffff:
                x = json.loads(line)["text"]  # TODO 待优化 可用性能更高的反序列工具，数据量大的话，优势就可以体现出来, 数据不合法怎么处理
                self.add_raw(x)
        self.builder.finalize(f"{self.output_file_name_prefix}.idx")
        print("done")

        print("### Verifying result...")
        data = MMapIndexedDataset(self.output_file_name_prefix)
        data_len = len(data)
        data_size = len(data._bin_buffer) // data._index._dtype_size

        todo = [0, data_len - 1]
        preview_limit = 100
        for idx in todo:
            ptr, size = data._index[idx]
            dix = data.get(idx=idx, offset=0, length=size).astype(int)
            print("-" * 70 + f"[{self.output_file_name_prefix} idx {idx} sz {size}]")
            assert dix[-1] == 0
            dix = dix[:-1]
            if len(dix) > preview_limit:
                try:
                    print(self.tokenizer.decode(dix[:preview_limit]))
                except:
                    try:
                        print(self.tokenizer.decode(dix[: preview_limit + 1]))
                    except Exception as e:
                        print(self.tokenizer.decode(dix[: preview_limit + 2]))
                print("· " * 30)
                try:  # avoid utf-8 bug
                    print(self.tokenizer.decode(dix[-preview_limit:]))
                except:
                    try:
                        print(self.tokenizer.decode(dix[-preview_limit - 1:]))
                    except Exception as e:
                        print(self.tokenizer.decode(dix[-preview_limit - 2:]))
            else:
                print(self.tokenizer.decode(dix))

        print(
            f"{'-' * 80}\n### Final {self.output_file_name_prefix}.bin/idx has {data_size} tokens, {data_len} "
            f"items. Dtype {data._index.dtype}")

        if data_size >= self.context_len * 3:
            n_chunk = int(data_size // self.context_len) - 1
            for i in range(n_chunk, 0, -1):
                if i % 3 == 2:
                    if self.is_prime(i):
                        print(f"\n### magic_prime = {i} (for ctxlen {self.context_len})")
                        print(f'\n--my_exit_tokens {data_size} --magic_prime {i} --ctx_len {self.context_len}\n')

    def add_raw(self, raw):
        """
        添加数据
        """
        out = self.tokenizer.encode(raw)
        if self.tokenizer.decode(out) != raw:
            print("ERROR" * 100)
            exit(0)
        out.append(0)  # [0] = end_of_doc for rwkv tokenizer
        self.builder.add_item(np.array(out, dtype=np.uint16))
        self.builder.end_document()
        if self._count % 500 == 0:
            print(self._count, end=" ", flush=True)
        self._count += 1

    @staticmethod
    def is_prime(n):
        """
        判断是否为质数
        """
        if n <= 1:
            return False
        if n <= 3:
            return True
        if n % 2 == 0 or n % 3 == 0:
            return False
        i = 5
        while i * i <= n:
            if n % i == 0 or n % (i + 2) == 0:
                return False
            i += 6
        return True

