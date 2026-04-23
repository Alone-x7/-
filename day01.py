import requests

# 请求网站，获取响应结果
# url= "http://books.toscrape.com/"
# response = requests.get( url, timeout=5)
# print(response.status_code)
# print(response.text)

# 解析页面内容
# import bs4
# from bs4 import BeautifulSoup
#
# soup = BeautifulSoup(response.text, "html.parser")
#
#
# print(soup.prettify())
# print(soup.title)
# print(soup.title.string)


# 在内存里的 HTML 字符串上练习 BeautifulSoup（无需联网）
from bs4 import BeautifulSoup

html = (
    '<html><body><ul class="news">'
    '<li><a href="/a">院校A</a></li>'
    '<li><a href="/b">院校B</a></li>'
    "</ul></body></html>"
)
soup = BeautifulSoup(html, "lxml")

# find：第一个 ul
# ul = soup.find("ul", class_="news")
# print("find ul:", ul)

# # select：CSS 选择器，选中 ul.news 下所有 li 里的 a
for a in soup.select("ul.news li a"):
    text = a.get_text(strip=True)
    href = a.get("href")
    print("链接文本:", text, "| href:", href)