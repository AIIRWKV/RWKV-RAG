# coding=utf-8
from .abc import AbstractLoader, HtmlCommonLoader
from .docx_loader import DocxLoader
from .excel_loader import ExcelLoader
from .html_loader import HtmlLoader
from .markdown_loader import MarkdownLoader
from .txt_loader import TxtLoader
from .pdf_loader import PDFLoader
from .internet_search import search_on_baike


import os

class Loader:
    """
    加载器，用来分割本地文件
    """
    def __init__(self, file_path: str, chunk_size:int):
        """
        :param file_path: 文件路径或者目录地址
        :param chunk_size: 块大小
        """
        self.file_path = file_path
        self.chunk_size = chunk_size
        self.output_path = ''
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File or Directory not found: {file_path}")
        if os.path.isdir(file_path):
            raise NotImplementedError("Directory is not supported yet")


    def load_txt(self):
        loader = TxtLoader(self.file_path, chunk_size=self.chunk_size)
        return loader.load()

    def load_pdf(self):
        loader = PDFLoader(self.file_path, chunk_size=self.chunk_size)
        return loader.load()


    def load_excel(self):
        loader = ExcelLoader(self.file_path, chunk_size=self.chunk_size)
        return loader.load()

    def load_docx(self):
        loader = DocxLoader(self.file_path, chunk_size=self.chunk_size)
        return loader.load()

    def load_html(self):
        loader = HtmlLoader(self.file_path, chunk_size=self.chunk_size)
        return loader.load()

    def load_markdown(self):
        loader = MarkdownLoader(self.file_path, chunk_size=self.chunk_size)
        return loader.load()


    def load_and_split_file(self, output_dir: str, file_name=None):
        base_filename, file_ext = os.path.splitext(os.path.basename(self.file_path))
        if file_name:
            base_filename = file_name

        file_ext = file_ext.lstrip('.')
        file_ext = file_ext.lower()
        if file_ext == 'docx':
            func = self.load_docx
        elif file_ext == 'pdf':
            func = self.load_pdf
        elif file_ext == 'xlsx' or file_ext == 'xls':
            func = self.load_excel
        elif file_ext in ('txt', 'py', 'js', 'java', 'c', 'cpp', 'h', 'php', 'go', 'ts', 'sh', 'cs', 'kt', 'sql'):
            func = self.load_txt
        elif file_ext == 'md' or file_ext == 'markdown':
            func = self.load_markdown
        elif file_ext == 'html' or file_ext == 'htm':
            func = self.load_html
        else:
            raise NotImplementedError(
                "file type not supported yet(pdf, xlsx, docx, txt, markdown, html supported)")
        if func and callable(func):
            output_file = os.path.join(output_dir, f"{base_filename}_chunks.txt")
            self.output_path = output_file
            with open(output_file, 'w', encoding='utf-8') as f:
                for item in func():
                    if item:
                        yield item
                        f.write(item)
                        f.write('\n')


