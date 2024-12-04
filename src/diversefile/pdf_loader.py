#coding=utf-8

import fitz
from src.diversefile import AbstractLoader

class PDFLoader(AbstractLoader):
    def load(self):
        with fitz.open(self.file_path) as doc:
            current_txt = ''
            for page in doc:
                txt = page.get_text()
                if txt:
                    txt = txt.strip(' ')
                    current_txt = current_txt + txt
                    s = 0
                    e = 0
                    for char in current_txt:
                        e += 1
                        if char in self.delimiter and e - s >= self.chunk_size:
                            yield current_txt[s: e].replace('\n', '')
                            s = e
                    current_txt = current_txt[s:]
                current_txt = current_txt.strip()
                if current_txt:
                    yield current_txt
