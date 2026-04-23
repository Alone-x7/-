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


CHROMEDRIVER_PATH = r"D:\Python 1.10.4\Chrome驱动\chromedriver-win64\chromedriver.exe"
START_URL = "https://www.kaoyan.com/major"
OUTPUT_FILE = Path.home() / "Desktop" / "考研网专业信息.xlsx"


def connect_browser():
    opt = Options()
    opt.add_argument("--start-maximized")
    opt.add_experimental_option("excludeSwitches", ["enable-automation"])
    opt.add_experimental_option("useAutomationExtension", False)

    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=opt)
    return driver


def wait_page_ready(driver, timeout=15):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )


def scroll_to_top(driver):
    try:
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.8)
    except Exception:
        pass


def normalize_text(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def extract_major_name(card):
    """
    从“专业代码”那一行往前找专业名称（最稳）
    """
    try:
        lines = [normalize_text(x) for x in card.text.splitlines() if normalize_text(x)]

        for i, line in enumerate(lines):
            if "专业代码" in line:
                # 上一行通常就是专业名
                if i > 0:
                    name = lines[i - 1]

                    # 清理垃圾词
                    name = name.replace("开设院校", "").strip()

                    # 过滤异常
                    if 2 <= len(name) <= 30:
                        return name
    except:
        pass

    return ""


def extract_major_type(card):
    try:
        text = normalize_text(card.text)
        m = re.search(r"专业类型[:：]\s*(学术型硕士|专业硕士)", text)
        if m:
            return m.group(1)
    except:
        pass

    return ""


def get_cards_on_page(driver):
    """
    用“专业代码”作为锚点，定位每个专业条目（最稳定）
    """
    cards = []
    seen = set()

    elems = driver.find_elements(By.XPATH, "//*[contains(text(),'专业代码')]")

    for el in elems:
        try:
            best = None
            best_len = 10**9

            # 向上找最小容器
            for xp in [
                "./ancestor::li[1]",
                "./ancestor::div[1]",
                "./ancestor::div[2]",
                "./ancestor::div[3]",
                "./ancestor::section[1]",
            ]:
                try:
                    c = el.find_element(By.XPATH, xp)
                    txt = normalize_text(c.text)

                    # 必须同时包含“专业代码”和“专业类型”
                    if "专业代码" in txt and "专业类型" in txt:
                        l = len(txt)
                        if 30 < l < best_len:
                            best = c
                            best_len = l
                except:
                    continue

            if best is None:
                continue

            key = normalize_text(best.text)
            if key in seen:
                continue
            seen.add(key)

            cards.append(best)

        except:
            continue

    return cards


def go_next_page(driver):
    try:
        next_btn = driver.find_element(
            By.XPATH,
            '//*[@id="__nuxt"]/div/main/div/div/div[2]/div[1]/div[5]/button[2]'
        )

        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_btn)
        time.sleep(0.8)

        if not next_btn.is_enabled():
            return False

        driver.execute_script("arguments[0].click();", next_btn)
        time.sleep(2)
        wait_page_ready(driver, timeout=15)
        scroll_to_top(driver)
        return True

    except Exception as e:
        print("翻页失败：", e)
        return False


def scrape_page(driver):
    results = []
    cards = get_cards_on_page(driver)

    print(f"当前页找到 {len(cards)} 个专业条目")

    for card in cards:
        try:
            name = extract_major_name(card)
            major_type = extract_major_type(card)

            if not name:
                continue

            results.append({
                "专业名称": name,
                "专业类型": major_type
            })
        except Exception:
            continue

    return results


def main():
    driver = connect_browser()

    driver.get(START_URL)
    wait_page_ready(driver)
    time.sleep(2)
    scroll_to_top(driver)

    all_results = []

    for page_no in range(1, 3):  # 只要两页
        print(f"\n====== 正在抓第 {page_no} 页 ======")

        wait_page_ready(driver)
        time.sleep(1.5)
        scroll_to_top(driver)

        page_results = scrape_page(driver)
        all_results.extend(page_results)

        if page_no < 2:
            ok = go_next_page(driver)
            if not ok:
                print("下一页点击失败，提前结束。")
                break

    df = pd.DataFrame(all_results)
    if not df.empty:
        df = df.drop_duplicates(subset=["专业名称"], keep="first")

    df.to_excel(OUTPUT_FILE, index=False)
    print(f"\n已保存到：{OUTPUT_FILE}")


if __name__ == "__main__":
    main()