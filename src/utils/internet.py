from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import os

async def search_on_baike(query, output_directory='.', filename=None):
    
    if filename is None:
        filename = f'{query}.txt'
    filepath = os.path.join(output_directory, filename)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto('https://baike.baidu.com/')

        await page.wait_for_selector('#root > div > div.index-module_pageHeader__jSG5w > div.lemmaSearchBarWrapper.undefined > div > div > div > div > input', timeout=5000)
        await page.fill('#root > div > div.index-module_pageHeader__jSG5w > div.lemmaSearchBarWrapper.undefined > div > div > div > div > input', query)
        await page.click('#root > div > div.index-module_pageHeader__jSG5w > div.lemmaSearchBarWrapper.undefined > div > div > div > button.lemmaBtn')

        await page.wait_for_timeout(5000)
        html_content = await page.content()
        soup = BeautifulSoup(html_content, 'html.parser')
        content_div = soup.find('div', {'class': 'J-lemma-content'})
        if content_div:
            content_text = content_div.get_text().strip()

            # Save content_text to the specified file
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content_text)
            return ''
        else:
            return "百度百科没有该词条简介，请重新输入关键词"
