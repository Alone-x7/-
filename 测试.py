import re
import time
from pathlib import Path

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# =========================
# 基本配置
# =========================
CHROMEDRIVER_PATH = r"D:\Python 1.10.4\Chrome驱动\chromedriver-win64\chromedriver.exe"
START_URL = "https://www.kaoyan.com/major"

DESKTOP = Path.home() / "Desktop"
OUTPUT_FILE = DESKTOP / "考研网专业信息.xlsx"


# =========================
# 启动浏览器（不使用 debugger）
# =========================
def create_driver():
    opt = Options()
    opt.add_argument("--start-maximized")

    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=opt)
    return driver


# =========================
# 等待页面加载
# =========================
def wait_page(driver):
    WebDriverWait(driver, 15).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


# =========================
# 抓专业数据（核心）
# =========================
def get_major_data(driver):
    data = []

    # 等 li 卡片加载
    WebDriverWait(driver, 15).until(
        EC.presence_of_all_elements_located((By.XPATH, "//li"))
    )

    cards = driver.find_elements(By.XPATH, "//li")

    for card in cards:
        try:
            # ===== 专业名称 =====
            name = card.find_element(By.XPATH, ".//h4").text
            name = name.replace("开设院校", "").strip()

            # 过滤无效项（比如“全部”）
            if not name or len(name) > 20:
                continue

            # ===== 专业类型 =====
            type_text = card.find_element(
                By.XPATH, ".//span[contains(text(),'专业类型')]"
            ).text

            major_type = type_text.replace("专业类型：", "").strip()

            data.append({
                "专业名称": name,
                "专业类型": major_type
            })

        except Exception:
            continue

    return data


# =========================
# 翻页（你给的 XPath）
# =========================
def next_page(driver):
    try:
        btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                '//*[@id="__nuxt"]/div/main/div/div/div[2]/div[1]/div[5]/button[2]'
            ))
        )

        driver.execute_script("arguments[0].click();", btn)
        time.sleep(2)
        wait_page(driver)
        return True

    except Exception as e:
        print("翻页失败：", e)
        return False


# =========================
# 主程序
# =========================
def main():
    driver = create_driver()
    driver.get(START_URL)
    wait_page(driver)
    time.sleep(2)

    all_data = []

    for page in range(1, 3):   # 只抓2页
        print(f"\n====== 正在抓第 {page} 页 ======")

        page_data = get_major_data(driver)
        print(f"当前页抓到 {len(page_data)} 条")

        all_data.extend(page_data)

        if page < 2:
            ok = next_page(driver)
            if not ok:
                break

    # 去重
    df = pd.DataFrame(all_data)
    df = df.drop_duplicates()

    df.to_excel(OUTPUT_FILE, index=False)
    print(f"\n已保存到：{OUTPUT_FILE}")


if __name__ == "__main__":
    main()