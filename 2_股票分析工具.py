import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import os
from config import CSV_PATH, DATA_DIR
from data_fetcher import fetch_stock_history
from calculator import calculate_pe_ratio
from predictor import FinancialPredictor
from visualizer import plot_stock_data, plot_pe_analysis
def main():
    st.title("股票数据分析工具")
    
    # 侧边栏：选择分析模式
    with st.sidebar:
        st.header("分析模式")
        analysis_mode = st.radio(
            "选择分析模式",
            ["单只股票分析", "选股结果分析"]
        )
    
    if analysis_mode == "单只股票分析":
        # 1. 获取股票历史数据
        st.header("1. 获取股票历史数据")
        stock_history_df = fetch_stock_history()
        if stock_history_df is None or stock_history_df.empty:
            st.info("请先查询股票数据。")
            return
        # 2. 计算市盈率
        st.header("2. 市盈率分析")
        stock_code = st.text_input("股票代码", value="sh600519", key="pe_stock_code")
        pe_df = calculate_pe_ratio(stock_history_df, stock_code)
        if pe_df is not None and not pe_df.empty:
            st.subheader("市盈率数据")
            st.dataframe(pe_df.tail())
            # 3. 预测未来市盈率
            st.header("3. 市盈率预测")
            forecast_days = st.slider("预测天数", min_value=1, max_value=30, value=7)
            predictor = FinancialPredictor(model_type="random_forest")
            forecast_df, metrics = predictor.predict_pe(pe_df['PE'], forecast_days)
            st.subheader("预测结果")
            st.dataframe(forecast_df)
            # 4. 可视化
            st.header("4. 数据可视化")
            plot_stock_data(stock_history_df)
            plot_pe_analysis(pe_df, forecast_df)
        else:
            st.warning("市盈率数据获取失败。")
    
    else:  # 选股结果分析模式
        st.header("选股结果分析")
        
        # 检查是否存在选股结果文件
        selected_stocks_file = "selected_stocks_for_analysis.csv"
        if os.path.exists(selected_stocks_file):
            # 读取选股结果
            selected_stocks_df = pd.read_csv(selected_stocks_file)
            
            if not selected_stocks_df.empty:
                st.success(f"已加载选股结果，共{len(selected_stocks_df)}只股票")
                
                # 显示选股列表
                st.subheader("选股列表")
                st.dataframe(selected_stocks_df, use_container_width=True)
                
                # 选择要分析的股票
                selected_stock = st.selectbox(
                    "选择要分析的股票",
                    selected_stocks_df["name"].tolist(),
                    index=0
                )
                
                # 获取选中股票的代码
                stock_code = selected_stocks_df[selected_stocks_df["name"] == selected_stock]["code"].values[0]
                
                # 获取该股票的历史数据
                with st.spinner(f"正在获取{selected_stock}的历史数据..."):
                    from data_fetcher import fetch_stock_history as fetch_single_stock
                    # 修改data_fetcher.py以支持根据代码获取单只股票数据
                    # 这里我们使用现有的fetch_stock_history函数，但传入特定的股票代码
                    stock_history_df = fetch_stock_history(stock_code=stock_code)
                
                if stock_history_df is not None and not stock_history_df.empty:
                    # 计算市盈率
                    pe_df = calculate_pe_ratio(stock_history_df, stock_code)
                    
                    if pe_df is not None and not pe_df.empty:
                        # 显示股票基本信息
                        st.subheader(f"{selected_stock} ({stock_code}) 基本信息")
                        stock_info = selected_stocks_df[selected_stocks_df["name"] == selected_stock].iloc[0]
                        info_cols = st.columns(2)
                        with info_cols[0]:
                            st.metric("市盈率", f"{stock_info['pe']:.2f}")
                            st.metric("市净率", f"{stock_info['pb']:.2f}")
                            st.metric("换手率", f"{stock_info['turnover_rate']:.2f}%")
                        with info_cols[1]:
                            st.metric("流通市值", f"{stock_info['circulation_market_value']/100000000:.2f}亿")
                            st.metric("最新收盘价", f"{stock_info['latest_close']:.2f}")
                            st.metric("20天涨幅", f"{stock_info['price_trend']:.2f}%")
                        
                        # 市盈率分析
                        st.subheader("市盈率分析")
                        st.dataframe(pe_df.tail(), use_container_width=True)
                        
                        # 预测未来市盈率
                        st.subheader("市盈率预测")
                        forecast_days = st.slider("预测天数", min_value=1, max_value=30, value=7, key="forecast_days")
                        predictor = FinancialPredictor(model_type="random_forest")
                        forecast_df, metrics = predictor.predict_pe(pe_df['PE'], forecast_days)
                        st.dataframe(forecast_df, use_container_width=True)
                        
                        # 可视化
                        st.subheader("数据可视化")
                        plot_stock_data(stock_history_df)
                        plot_pe_analysis(pe_df, forecast_df)
                    else:
                        st.warning("无法获取市盈率数据。")
                else:
                    st.warning("无法获取股票历史数据。")
            else:
                st.warning("选股结果为空。")
        else:
            st.info("未找到选股结果文件。请先使用选股工具生成选股结果。")
            st.markdown("使用以下命令运行选股工具：")
            st.code("python choose.py")
if __name__ == "__main__":
     main()