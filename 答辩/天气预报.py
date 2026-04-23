import re
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup


URL = "https://www.tianqihoubao.com/lishi/beijing/month/202311.html"


def split_weather(text: str):
    """把 '晴 / 雾' 这种内容拆成白天状况、夜间状况"""
    if pd.isna(text):
        return None, None
    text = str(text).replace("／", "/").replace(" ", "")
    parts = [p for p in text.split("/") if p]
    if len(parts) >= 2:
        return parts[0], parts[1]
    elif len(parts) == 1:
        return parts[0], None
    return None, None


def split_wind(text: str):
    """把 '无持续风向1-3级 / 无持续风向1-3级' 拆成白天/夜间风力风向"""
    if pd.isna(text):
        return None, None
    text = str(text).replace("／", "/").replace(" ", "")
    parts = [p for p in text.split("/") if p]
    if len(parts) >= 2:
        return parts[0], parts[1]
    elif len(parts) == 1:
        return parts[0], None
    return None, None


def split_temp(text: str):
    """把 '22℃ / 13℃' 拆成最高气温、最低气温"""
    if pd.isna(text):
        return None, None
    text = str(text).replace("／", "/").replace(" ", "")
    parts = [p for p in text.split("/") if p]

    nums = []
    for p in parts:
        m = re.search(r"-?\d+", p)
        if m:
            nums.append(int(m.group()))

    if len(nums) >= 2:
        return nums[0], nums[1]
    elif len(nums) == 1:
        return nums[0], None
    return None, None


def main():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    }

    resp = requests.get(URL, headers=headers, timeout=20)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding

    # 先用 pandas 直接读表
    tables = pd.read_html(resp.text)

    if not tables:
        raise RuntimeError("没有解析到表格，请检查网页结构是否变化。")

    # 找到最像目标表的那个
    df = None
    for t in tables:
        cols = [str(c) for c in t.columns]
        if any("日期" in c for c in cols):
            df = t.copy()
            break

    if df is None:
        df = tables[0].copy()

    # 统一列名（按截图里的顺序）
    # 一般为：日期 / 天气状况(白天/夜间) / 最高/最低气温 / 风力风向(白天/夜间)
    if df.shape[1] < 4:
        raise RuntimeError(f"表格列数不足，当前只有 {df.shape[1]} 列。")

    df = df.iloc[:, :4].copy()
    df.columns = ["日期", "天气状况", "最高/最低气温", "风力风向"]

    # 拆列
    df[["白天状况", "夜间状况"]] = df["天气状况"].apply(
        lambda x: pd.Series(split_weather(x))
    )
    df[["最高气温", "最低气温"]] = df["最高/最低气温"].apply(
        lambda x: pd.Series(split_temp(x))
    )
    df[["白天风力风向", "夜间风力风向"]] = df["风力风向"].apply(
        lambda x: pd.Series(split_wind(x))
    )

    # 整理输出列
    out = df[
        ["日期", "白天状况", "夜间状况", "最高气温", "最低气温", "白天风力风向", "夜间风力风向"]
    ].copy()

    # 清理日期中的多余换行/空格
    out["日期"] = out["日期"].astype(str).str.replace(r"\s+", "", regex=True)

    # 保存到桌面
    desktop = Path.home() / "Desktop"
    if not desktop.exists():
        desktop = Path.cwd()

    save_path = desktop / "北京202311月天气数据.xlsx"
    out.to_excel(save_path, index=False, engine="openpyxl")

    print(f"已保存到：{save_path}")


if __name__ == "__main__":
    main()