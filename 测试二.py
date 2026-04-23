import re
import time
from pathlib import Path

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    StaleElementReferenceException,
    WebDriverException
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# =========================
# 1. 基本配置
# =========================
CHROMEDRIVER_PATH = r"D:\Python 1.10.4\Chrome驱动\chromedriver-win64\chromedriver.exe"
DEBUGGER_ADDRESS = "127.0.0.1:8888"
START_URL = "https://www.kaoyan.com/college"

DESKTOP = Path.home() / "Desktop"
OUTPUT_FILE = DESKTOP / "考研网学校信息.xlsx"

PROVINCE_TOKENS = [
    "北京", "天津", "上海", "重庆",
    "河北", "山西", "辽宁", "吉林", "黑龙江",
    "江苏", "浙江", "安徽", "福建", "江西", "山东",
    "河南", "湖北", "湖南", "广东", "海南",
    "四川", "贵州", "云南", "陕西", "甘肃", "青海",
    "台湾", "内蒙古", "广西", "西藏", "宁夏", "新疆",
    "香港", "澳门"
]


# =========================
# 2. 连接已打开的 Chrome
# =========================
def connect_browser():
    opt = Options()

    # ✅ 正常启动浏览器（不再使用 debugger）
    opt.add_argument("--start-maximized")   # 启动即最大化（替代 maximize_window）
    opt.add_experimental_option("excludeSwitches", ["enable-automation"])
    opt.add_experimental_option("useAutomationExtension", False)

    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=opt)

    return driver


# =========================
# 3. 通用工具
# =========================
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


def safe_text(element, default=""):
    try:
        txt = element.text
        return txt.strip() if txt else default
    except Exception:
        return default


def normalize_text(text):
    return re.sub(r"\s+", " ", str(text)).strip()


def first_match_text(driver, xpaths, default=""):
    for xp in xpaths:
        try:
            el = driver.find_element(By.XPATH, xp)
            txt = safe_text(el)
            if txt:
                return txt
        except NoSuchElementException:
            continue
        except Exception:
            continue
    return default


# =========================
# 4. 解析列表页：学校名称 / 学校类型 / 学校位置 / 详情链接
# =========================
def pick_card_container(btn):
    """
    从“查看”按钮向上找最像学校卡片的容器。
    """
    candidate_xpaths = [
        "./ancestor::li[1]",
        "./ancestor::article[1]",
        "./ancestor::section[1]",
        "./ancestor::div[1]",
        "./ancestor::div[2]",
        "./ancestor::div[3]",
    ]

    best = None
    best_len = 10**9

    for xp in candidate_xpaths:
        try:
            el = btn.find_element(By.XPATH, xp)
            txt = normalize_text(el.text)
            if "查看" not in txt:
                continue
            if 15 <= len(txt) < best_len:
                best = el
                best_len = len(txt)
        except Exception:
            continue

    if best is not None:
        return best

    try:
        return btn.find_element(By.XPATH, "./ancestor::div[1]")
    except Exception:
        return btn


def extract_name_from_lines(lines):
    """
    优先找像“清华大学 / 北京大学 / 浙江大学”这种名字。
    """
    for line in lines:
        if re.search(r"(大学|学院|学校|研究院|研究所)$", line):
            return line
    return lines[0] if lines else ""


def extract_location_from_lines(lines, name):
    """
    从卡片文本里找学校位置。
    重点：支持“浙江 教育部 | 中央部委 ...”这种混在一行里的情况。
    """
    for line in lines:
        if line == name:
            continue
        if line == "查看":
            continue

        # 按空格、竖线、斜杠等切开
        parts = re.split(r"[|｜/\\,\s]+", line)
        for part in parts:
            token = part.strip()
            if not token:
                continue

            # 直辖市/省份/自治区/特别行政区
            if token in PROVINCE_TOKENS:
                return token

            # 例如“浙江省”“北京市”“广西自治区”
            for prov in PROVINCE_TOKENS:
                if (
                    token == prov + "省"
                    or token == prov + "市"
                    or token == prov + "自治区"
                    or token == prov + "特别行政区"
                ):
                    return prov

    return ""


def extract_type_from_card(card, name, location):
    """
    从卡片里的 span 或文本中提取学校类型，如：
    985高校 211高校 双一流 自划线
    """
    tags = []
    try:
        spans = card.find_elements(By.XPATH, ".//span[normalize-space()]")
        for s in spans:
            t = normalize_text(s.text)
            if not t:
                continue
            if t in {"查看", name, location}:
                continue
            if len(t) <= 20:
                tags.append(t)
    except Exception:
        pass

    if not tags:
        try:
            lines = [normalize_text(x) for x in card.text.splitlines() if normalize_text(x)]
            for line in lines:
                if line in {"查看", name, location}:
                    continue
                if len(line) <= 20 and not re.search(r"(北京|天津|上海|重庆|省|市|自治区|区|县)", line):
                    tags.append(line)
        except Exception:
            pass

    tags = list(dict.fromkeys(tags))
    return " ".join(tags)


def get_list_data_on_page(driver):
    """
    抓当前列表页的所有学校信息
    """
    data = []

    WebDriverWait(driver, 15).until(
        EC.presence_of_all_elements_located((By.XPATH, "//a[contains(normalize-space(),'查看')]"))
    )

    buttons = driver.find_elements(By.XPATH, "//a[contains(normalize-space(),'查看')]")
    seen_links = set()

    for btn in buttons:
        try:
            href = btn.get_attribute("href")
            if not href or href in seen_links:
                continue
            seen_links.add(href)

            card = pick_card_container(btn)

            lines = [normalize_text(x) for x in card.text.splitlines() if normalize_text(x)]
            lines = [x for x in lines if x not in {"查看"}]

            if not lines:
                continue

            name = extract_name_from_lines(lines)
            location = extract_location_from_lines(lines, name)
            school_type = extract_type_from_card(card, name, location)

            data.append({
                "学校名称": name,
                "学校类型": school_type,
                "学校位置": location,
                "详情页": href
            })

        except StaleElementReferenceException:
            continue
        except Exception:
            continue

    return data


# =========================
# 5. 抓详情页：只取学校介绍前50字
# =========================
def extract_intro_first_50(driver):
    """
    最终精准版：只要“学校介绍正文”，过滤招生资讯
    """

    def clean(text):
        return re.sub(r"\s+", "", text)

    def is_bad(text):
        bad_keywords = [
            "Copyright", "AllRightsReserved",
            "考研帮APP", "下载APP", "立即下载",
            "招生", "简章", "专业目录", "分数线", "报录比", "资讯", "更多"
        ]

        # 含日期（强特征：资讯）
        if re.search(r"\d{4}-\d{2}-\d{2}", text):
            return True

        return any(k in text for k in bad_keywords)

    try:
        heading = driver.find_element(By.XPATH, "//*[contains(text(),'学校介绍')]")
    except:
        return ""

    # =========================
    # 只找“标题后紧邻的第一段正文”
    # =========================
    try:
        elements = heading.find_elements(
            By.XPATH,
            "./following::*[self::p or self::div][position()<=10]"
        )

        for el in elements:
            t = el.text.strip()

            if not t:
                continue

            # ❗过滤招生资讯
            if is_bad(t):
                continue

            # ❗必须像“正文段落”
            if len(t) < 30:
                continue

            return clean(t)[:50]

    except:
        pass

    return ""

    def good_text(t):
        t = normalize_text(t).replace("\xa0", "")
        if not t:
            return False
        if len(t) < 20:
            return False
        if t == "学校介绍":
            return False
        low = t.lower()
        for kw in forbidden_keywords:
            if kw.lower() in low:
                return False
        if re.fullmatch(r"[\d\W_]+", t):
            return False
        return True

    intro = ""

    try:
        heading = driver.find_element(
            By.XPATH,
            "//*[normalize-space()='学校介绍' or contains(normalize-space(),'学校介绍')]"
        )
    except Exception:
        return ""

    containers = []
    for xp in [
        "./ancestor::section[1]",
        "./ancestor::article[1]",
        "./ancestor::main[1]",
        "./ancestor::div[1]",
        "./ancestor::div[2]",
        "./ancestor::div[3]",
    ]:
        try:
            c = heading.find_element(By.XPATH, xp)
            containers.append(c)
        except Exception:
            continue

    for container in containers:
        try:
            texts = []
            # 先找段落
            for el in container.find_elements(By.XPATH, ".//p[normalize-space()] | .//div[normalize-space()]"):
                t = normalize_text(el.text)
                if good_text(t):
                    texts.append(t)

            if texts:
                # 选最长的一段，通常是介绍正文
                intro = max(texts, key=len)
                break
        except Exception:
            continue

    if not intro:
        # 兜底：在标题后面的少量块里找
        try:
            following = heading.find_elements(
                By.XPATH,
                "./following::*[self::p or self::div][position()<=12]"
            )
            texts = []
            for el in following:
                t = normalize_text(el.text)
                if good_text(t):
                    texts.append(t)
            if texts:
                intro = max(texts, key=len)
        except Exception:
            pass

    intro = re.sub(r"\s+", "", intro)
    return intro[:50] if intro else ""


def get_intro(driver, url):
    driver.get(url)
    wait_page_ready(driver, timeout=15)
    time.sleep(1.5)
    return extract_intro_first_50(driver)


# =========================
# 6. 翻页
# =========================
def go_next_page(driver):
    try:
        next_btn = driver.find_element(
            By.XPATH,
            '//*[@id="__nuxt"]/div/main/div/div/div[2]/div[1]/div[2]/div[11]/button[2]'
        )

        # 如果按钮不可点击，直接返回 False
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


# =========================
# 7. 主流程
# =========================
def main():
    driver = connect_browser()

    driver.get(START_URL)
    wait_page_ready(driver, timeout=15)
    time.sleep(2)
    scroll_to_top(driver)

    results = []
    visited = set()

    for page_no in range(1, 11):   # 前10页
        print(f"\n====== 正在抓第 {page_no} 页 ======")

        scroll_to_top(driver)
        time.sleep(1)

        list_data = get_list_data_on_page(driver)
        print(f"当前页找到 {len(list_data)} 个学校")

        for idx, item in enumerate(list_data, start=1):
            detail_url = item["详情页"]

            if detail_url in visited:
                continue
            visited.add(detail_url)

            try:
                print(f"  正在抓取第 {idx} 个：{item['学校名称']}")

                intro = get_intro(driver, detail_url)

                results.append({
                    "学校名称": item["学校名称"],
                    "学校类型": item["学校类型"],
                    "学校位置": item["学校位置"],
                    "学校介绍": intro
                })

                print(f"    成功：{item['学校名称']}")

                driver.back()
                wait_page_ready(driver, timeout=15)
                time.sleep(1.2)
                scroll_to_top(driver)

            except Exception as e:
                print(f"    失败：{e}")
                try:
                    driver.back()
                    wait_page_ready(driver, timeout=15)
                    time.sleep(1)
                    scroll_to_top(driver)
                except Exception:
                    pass

        # 最后一页就不点下一页了
        if page_no < 10:
            ok = go_next_page(driver)
            if not ok:
                print("下一页点击失败，提前结束。")
                break

    df = pd.DataFrame(results)
    if not df.empty:
        df = df.drop_duplicates(subset=["学校名称"], keep="first")

    df.to_excel(OUTPUT_FILE, index=False)
    print(f"\n已保存到：{OUTPUT_FILE}")


if __name__ == "__main__":
    main()