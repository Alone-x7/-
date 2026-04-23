import time
import pandas as pd
import os

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def get_table_data(browser):
    # ✅ 等待数据行出现（关键）
    WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.XPATH, "//table//tr[td]"))
    )

    rows = browser.find_elements(By.XPATH, "//table//tr")

    data = []
    headers = []

    for i, row in enumerate(rows):
        ths = row.find_elements(By.TAG_NAME, "th")
        tds = row.find_elements(By.TAG_NAME, "td")

        if i == 0 and ths:
            headers = [th.text.strip() for th in ths]
        else:
            row_data = [td.text.strip().replace("\n", " ") for td in tds]
            if row_data:
                data.append(row_data)

    return headers, data


def go_next_page(browser):
    try:
        #//*[@id="__nuxt"]/div/main/div/div[3]/div[1]/div[2]/button[2]
        next_btn = browser.find_element(By.XPATH, "//button[@type='button'][last()]")
        browser.execute_script("arguments[0].click();", next_btn)
        time.sleep(2)
        return True
    except:
        return False


if __name__ == '__main__':
    service = Service(r'D:\Python 1.10.4\Chrome驱动\chromedriver-win64\chromedriver.exe')
    opt = Options()
    opt.debugger_address = '127.0.0.1:8888'

    browser = webdriver.Chrome(service=service, options=opt)

    url = "https://www.kaoyan.com/college/score?id=1606"
    browser.get(url)

    time.sleep(3)

    all_data = []
    headers = None

    for i in range(6):
        print(f"正在抓取第 {i+1} 页...")

        h, data = get_table_data(browser)

        if headers is None:
            headers = h

        all_data.extend(data)

        if i < 5:
            if not go_next_page(browser):
                print("没有下一页了")
                break

    df = pd.DataFrame(all_data, columns=headers)

    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    file_path = os.path.join(desktop_path, "浙江大学考研信息前六页.xlsx")

    df.to_excel(file_path, index=False)

    print("✅ 已保存到桌面：", file_path)