#coding=utf-8
"""
联网搜索
"""
import os

import requests

from src.diversefile import HtmlLoader
def search_on_baike(query, output_dir, filename=None):
    if filename is None:
        filename = f'{query}.txt'
    filepath = os.path.join(output_dir, filename)

    try:
        response = requests.get(f'https://baike.baidu.com/item/{query}', timeout=8)
    except:
        raise Exception("网络错误")
    if 200 <=response.status_code <400:
        try:
            html_content = response.content.decode('utf-8', errors='ignore')
        except:
            raise ValueError("百度百科没有该词条简介，请重新输入关键词")
        html_content = html_content.strip()
        if not html_content:
            raise ValueError("百度百科没有该词条简介，请重新输入关键词")
        content_text = HtmlLoader.parser_txt(html_content, just_need_content=True)
        if not content_text:
            raise ValueError("百度百科没有该词条简介，请重新输入关键词")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content_text)
        return content_text, filepath
    else:
        raise ValueError("网络错误，稍后重试！")