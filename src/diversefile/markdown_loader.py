# coding=utf-8
from markdown import markdown

from src.diversefile import AbstractLoader, HtmlCommonLoader

class MarkdownLoader(AbstractLoader):

    def load(self):
        if self.is_filepath:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                txt = f.read()
        else:
            txt = self.file_path

        html_str = markdown(txt)
        lines = HtmlCommonLoader(html_str, is_filepath=False).load()
        return lines