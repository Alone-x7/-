import requests
from bs4 import BeautifulSoup

url = 'https://books.toscrape.com/'
head = {
"user-agent":
"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
}
r = requests.get(url, headers=head)
html = r.text

soup = BeautifulSoup(html, 'html.parser')

# 书名
name = soup.find('h3').find('a')['title']
print('书名:', name)

# 价格
price = soup.find('div', class_="product_price").find('p').text
print('价格:', price)

# 图片链接
link = soup.find('div', class_="image_container").find('img')['src']
links = 'https://books.toscrape.com/' + link
print('图片链接:', links)


