# coding=utf-8

from src.diversefile import AbstractLoader

class TxtLoader(AbstractLoader):

    def load(self):

        with open(self.file_path, 'r', encoding="utf-8", errors='ignore') as f:
            current_txt = ''
            while 1:
                txt = f.read(10240)
                if not txt:
                    break
                txt = txt.strip(' ')
                current_txt = current_txt + txt
                s = 0
                e = 0
                for char in current_txt:
                    e += 1
                    if char in self.delimiter and e-s >= self.chunk_size:
                        yield current_txt[s: e].replace('\n', '')
                        s = e
                current_txt = current_txt[s:]
            current_txt = current_txt.strip()
            if current_txt:
                yield current_txt