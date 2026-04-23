import random
import time
import re
from pathlib import Path
from io import StringIO

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options


# ========= 配置 =========
CHROMEDRIVER_PATH = r"D:\Python 1.10.4\Chrome驱动\chromedriver-win64\chromedriver.exe"
BASE_URL = "https://www.tianqihoubao.com/lishi/shenzhen/month/{}.html"

START_YEAR = 2011
START_MONTH = 1
END_YEAR = 2026
END_MONTH = 3

SAVE_PATH = Path.home() / "Desktop" / "深圳天气_2011_2026.xlsx"


# ========= 月份生成 =========
def month_range(sy, sm, ey, em):
    res = []
    y, m = sy, sm
    while (y < ey) or (y == ey and m <= em):
        res.append(f"{y}{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return res


# ========= 数据拆分 =========
def split_weather(text):
    text = str(text).replace(" ", "").replace("／", "/")
    parts = text.split("/")
    return (parts + [None, None])[:2]


def split_temp(text):
    nums = re.findall(r"-?\d+", str(text))
    nums = [int(x) for x in nums]
    return (nums + [None, None])[:2]


def split_wind(text):
    text = str(text).replace(" ", "").replace("／", "/")
    parts = text.split("/")
    return (parts + [None, None])[:2]


def extract(html):
    tables = pd.read_html(StringIO(html))
    df = tables[0].iloc[:, :4]
    df.columns = ["日期", "天气", "气温", "风"]

    df[["白天状况", "夜间状况"]] = df["天气"].apply(lambda x: pd.Series(split_weather(x)))
    df[["最高气温", "最低气温"]] = df["气温"].apply(lambda x: pd.Series(split_temp(x)))
    df[["白天风力风向", "夜间风力风向"]] = df["风"].apply(lambda x: pd.Series(split_wind(x)))

    return df[["日期", "白天状况", "夜间状况", "最高气温", "最低气温", "白天风力风向", "夜间风力风向"]]


# ========= Selenium 配置 =========
options = Options()

# 不建议无脑 headless（容易被识别）
# options.add_argument("--headless=new")

options.add_argument("start-maximized")

# 伪装浏览器
options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# 去自动化特征
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)

service = Service(CHROMEDRIVER_PATH)
driver = webdriver.Chrome(service=service, options=options)

# 隐藏 webdriver 标志
driver.execute_cdp_cmd(
    "Page.addScriptToEvaluateOnNewDocument",
    {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"}
)


# ========= 断点续爬 =========
if SAVE_PATH.exists():
    existing_df = pd.read_excel(SAVE_PATH)
    done_months = set(existing_df["月份"].astype(str))
    print(f"检测到已有数据：{len(done_months)} 个月，启用断点续爬")
else:
    existing_df = None
    done_months = set()


all_data = []


# ========= 主爬虫 =========
try:
    months = month_range(START_YEAR, START_MONTH, END_YEAR, END_MONTH)

    for i, ym in enumerate(months):

        if ym in done_months:
            print(f"跳过（已存在）：{ym}")
            continue

        url = BASE_URL.format(ym)
        print(f"\n正在爬取：{ym}")

        try:
            driver.get(url)

            # 随机延时（核心防封）
            sleep_time = random.uniform(2, 5)
            print(f"  等待 {sleep_time:.2f} 秒")
            time.sleep(sleep_time)

            html = driver.page_source

            # 检测是否被反爬
            if "访问过于频繁" in html or "验证码" in html:
                print("  ⚠️ 被限制，休眠 60 秒...")
                time.sleep(60)
                continue

            df = extract(html)
            df.insert(0, "月份", ym)

            all_data.append(df)
            print(f"  成功：{len(df)} 行")

            # 每5个月长休息
            if i % 5 == 0 and i != 0:
                print("  💤 长休息 15 秒")
                time.sleep(15)

        except Exception as e:
            print(f"  ❌ 失败：{e}")
            time.sleep(10)

finally:
    driver.quit()


# ========= 保存 =========
if all_data:
    new_df = pd.concat(all_data, ignore_index=True)

    if existing_df is not None:
        result = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        result = new_df

    result.to_excel(SAVE_PATH, index=False)

    print(f"\n已保存到：{SAVE_PATH}")
    print(f"总数据量：{len(result)} 行")
else:
    print("没有新增数据")