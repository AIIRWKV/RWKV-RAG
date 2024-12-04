# coding=utf-8
import re

from docx import Document

from src.diversefile import AbstractLoader



class DocxLoader(AbstractLoader):
    """
    处理docx文件，不支持doc，doc需转成docx
    # TODO 暂时不能解析docx中的表格，图片等

    """
    def __clean(self, line):
        line = re.sub(r"\u3000", " ", line).strip()
        return line

    def load(self):
        doc = Document(self.file_path)
        new_lines = [self.__clean(page.text) for page in doc.paragraphs if page.text.strip()]
        current_txt = ''
        for line in new_lines:
            if len(current_txt) >= self.chunk_size:
                yield current_txt
                current_txt = ''
            current_txt += ' ' + line
        if current_txt:
            yield current_txt
        del doc
