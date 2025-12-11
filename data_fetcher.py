import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import akshare as ak # 假设你用 akshare 获取数据
from config import CSV_PATH
def fetch_stock_history(stock_code: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    获取股票历史数据
    
    参数:
    stock_code: Optional[str] - 股票代码，如果提供则直接获取该股票数据，不显示表单
    
    返回:
    Optional[pd.DataFrame] - 股票历史数据
    """
    # 如果提供了股票代码，则直接获取数据
    if stock_code:
        try:
            # 设置默认日期范围（最近120天）
            start_date = datetime.today() - timedelta(days=120)
            end_date = datetime.today()
            
            # 使用 akshare 获取数据
            history_df = ak.stock_zh_a_hist(
                symbol=stock_code.strip("shsz"),
                period="daily",
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d")
            )
            
            if history_df.empty:
                return None
                
            # 重命名列以统一格式
            history_df.rename(columns={
                "日期": "date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume"
            }, inplace=True)
            
            history_df.set_index("date", inplace=True)
            
            # 保存到 CSV
            history_df.to_csv(CSV_PATH)
            
            return history_df
            
        except Exception as e:
            return None
    
    # 如果没有提供股票代码，则显示表单交互
    with st.form("stock_history_form"):
        stock_code = st.text_input("股票代码", placeholder="示例: sh600519")
        start_date = st.date_input("起始日期", datetime.today() - timedelta(days=120))
        end_date = st.date_input("结束日期", datetime.today())
        submit_button = st.form_submit_button("查询数据")
    
    if submit_button:
        if not stock_code:
            st.warning("请填写股票代码")
            return _load_cached_data()
        
        try:
            # 使用 akshare 获取数据
            history_df = ak.stock_zh_a_hist(
                symbol=stock_code.strip("shsz"),
                period="daily",
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d")
            )
            
            if history_df.empty:
                st.error("未获取到数据，请检查股票代码或日期范围。")
                return _load_cached_data()
            
            # 重命名列以统一格式
            history_df.rename(columns={
                "日期": "date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume"
            }, inplace=True)
            
            history_df.set_index("date", inplace=True)
            
            # 保存到 CSV
            history_df.to_csv(CSV_PATH)
            
            st.success("数据获取成功并已保存！")
            return history_df
            
        except Exception as e:
            st.error(f"数据获取失败: {e}")
            return _load_cached_data()
    
    # 默认加载缓存数据
    return _load_cached_data()
def _load_cached_data() -> Optional[pd.DataFrame]:
    """加载本地缓存数据"""
    if CSV_PATH.exists():
        try:
            df = pd.read_csv(CSV_PATH, index_col="date", parse_dates=True)
            st.info("已加载本地缓存数据。")
            return df
        except Exception as e:
            st.warning(f"缓存数据加载失败: {e}")
            return None