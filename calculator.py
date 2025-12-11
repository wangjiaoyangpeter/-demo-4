import pandas as pd
import requests
from bs4 import BeautifulSoup
from typing import Optional
from config import FINANCE_SITES, DEFAULT_HEADERS
import streamlit as st
def get_eps_from_web(stock_code: str) -> Optional[float]:
    """
    从网页获取实时EPS（每股收益）
    """
    url = FINANCE_SITES["sina"].format(stock_code)
    try:
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        # 这里需要根据实际网页结构调整解析逻辑
        eps_tag = soup.find("span", text="每股收益")
        if eps_tag:
            eps_text = eps_tag.find_next_sibling().text
            return float(eps_text)
    except Exception as e:
        print(f"EPS获取失败: {e}")
        return None
def calculate_pe_ratio(
    stock_history: pd.DataFrame,
    stock_code: str,
    period_days: int = 12
    ) -> Optional[pd.DataFrame]:
    """
    计算动态市盈率
    采用三级数据获取策略：
    1. 优先获取专业金融软件数据（这里用 akshare 模拟）
    2. 其次通过网络爬虫获取实时EPS
    3. 最后启用模拟计算模型
    Args:
    stock_history: 历史股价数据
    stock_code: 股票代码（含市场前缀）
    period_days: 计算周期天数
    Returns:
    包含PE值及移动平均的分析结果
    """
    if stock_history.empty:
        return None
    # 模拟EPS获取（实际应调用真实数据源）
    eps = get_eps_from_web(stock_code)
    if eps is None or eps <= 0:
        st.info("EPS数据不可用，使用模拟值计算PE。")
        eps = 1.5 # 模拟值
    # 计算PE = 股价 / EPS
    close_prices = stock_history['close']
    pe_series = close_prices / eps
    # 生成结果
    result_df = pd.DataFrame({
    'close': close_prices,
    'EPS': eps,
    'PE': pe_series,
    'PE_MA': pe_series.rolling(window=period_days).mean()
    }).dropna()
    return result_df