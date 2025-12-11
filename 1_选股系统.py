import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time
import random
import logging
import streamlit as st

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_stock_basic_info() -> Optional[pd.DataFrame]:
    """
    获取股票基本信息，包括股票代码、名称、行业等
    """
    max_retries = 3
    retry_delay = 3  # 重试间隔时间（秒）
    
    for retry in range(max_retries):
        try:
            logging.info(f"尝试获取股票基本信息 (第{retry+1}次)...")
            # 获取所有A股基本信息
            stock_basic_df = ak.stock_zh_a_spot_em()
            
            # 保留需要的列
            stock_basic_df = stock_basic_df[[
                '代码', '名称', '行业', '地区', '市盈率', '市净率', '换手率', '流通市值'
            ]]
            
            # 重命名列
            stock_basic_df.columns = [
                'code', 'name', 'industry', 'region', 'pe', 'pb', 'turnover_rate', 'circulation_market_value'
            ]
            
            logging.info("股票基本信息获取成功")
            return stock_basic_df
        except Exception as e:
            logging.error(f"获取股票基本信息失败: {e}")
            if retry < max_retries - 1:
                logging.info(f"{retry_delay}秒后重试...")
                time.sleep(retry_delay)
                retry_delay *= 2  # 指数退避
                retry_delay += random.uniform(0, 1)  # 添加随机延迟避免并发问题
            else:
                logging.error("已达到最大重试次数，获取股票基本信息失败")
                return None

def get_financial_indicators(stock_code: str) -> Optional[pd.DataFrame]:
    """
    获取股票财务指标
    """
    max_retries = 2
    retry_delay = 2
    
    for retry in range(max_retries):
        try:
            logging.debug(f"获取{stock_code}财务指标 (第{retry+1}次)...")
            # 获取财务指标数据
            financial_df = ak.stock_financial_analysis_indicator(stock_code)
            
            # 取最新一期数据
            latest_financial = financial_df.iloc[0].to_frame().T
            
            return latest_financial
        except Exception as e:
            logging.debug(f"获取{stock_code}财务指标失败: {e}")
            if retry < max_retries - 1:
                time.sleep(retry_delay)
    
    return None

def get_stock_k_data(stock_code: str, days: int = 120) -> Optional[pd.DataFrame]:
    """
    获取股票K线数据
    """
    max_retries = 2
    retry_delay = 2
    
    for retry in range(max_retries):
        try:
            end_date = datetime.today().strftime("%Y%m%d")
            start_date = (datetime.today() - timedelta(days=days)).strftime("%Y%m%d")
            
            logging.debug(f"获取{stock_code}K线数据 (第{retry+1}次)...")
            # 获取K线数据
            k_data = ak.stock_zh_a_hist(
                symbol=stock_code.strip("shsz"),
                period="daily",
                start_date=start_date,
                end_date=end_date
            )
            
            # 重命名列
            k_data.rename(columns={
                "日期": "date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume"
            }, inplace=True)
            
            # 计算技术指标
            k_data['ma5'] = k_data['close'].rolling(window=5).mean()
            k_data['ma20'] = k_data['close'].rolling(window=20).mean()
            k_data['ma60'] = k_data['close'].rolling(window=60).mean()
            
            return k_data
        except Exception as e:
            logging.debug(f"获取{stock_code}K线数据失败: {e}")
            if retry < max_retries - 1:
                time.sleep(retry_delay)
    
    return None

def calculate_technical_indicators(k_data: pd.DataFrame) -> Dict[str, float]:
    """
    计算技术指标
    """
    # 确保数据按日期排序
    k_data = k_data.sort_values('date')
    
    # 计算均线关系
    latest_data = k_data.iloc[-1]
    
    # 均线多头排列判断（短期均线上穿长期均线）
    is_ma_bullish = latest_data['ma5'] > latest_data['ma20'] > latest_data['ma60']
    
    # 计算价格趋势（最近20天涨幅）
    if len(k_data) >= 20:
        price_trend = (latest_data['close'] - k_data.iloc[-20]['close']) / k_data.iloc[-20]['close'] * 100
    else:
        price_trend = 0
    
    return {
        'is_ma_bullish': is_ma_bullish,
        'price_trend': price_trend,
        'latest_close': latest_data['close'],
        'ma5': latest_data['ma5'],
        'ma20': latest_data['ma20'],
        'ma60': latest_data['ma60']
    }

def select_stocks(basic_info: pd.DataFrame, limit: int = 10, selection_mode: str = 'comprehensive', 
                  price_trend_days: int = 20, price_trend_min: float = 0, price_trend_max: float = 100, 
                  pe_min: float = 0, pe_max: float = 30, pb_max: float = 5, market_cap_min: float = 1000000000) -> List[Dict]:
    """
    选股函数
    
    参数:
    - basic_info: 股票基本信息
    - limit: 选股数量限制
    - selection_mode: 选股模式 ('comprehensive' 综合模式, 'price_trend' 简单涨幅模式)
    - price_trend_days: 涨幅计算周期（天）
    - price_trend_min: 最小涨幅（%）
    - price_trend_max: 最大涨幅（%）
    - pe_min: 最小市盈率
    - pe_max: 最大市盈率
    - pb_max: 最大市净率
    - market_cap_min: 最小流通市值
    """
    selected_stocks = []
    processed_count = 0
    
    # 判断是否使用模拟数据（通过检查是否存在于session_state）
    is_using_simulated_data = False
    if hasattr(st.session_state, 'simulated_data') and basic_info.equals(st.session_state['simulated_data']):
        is_using_simulated_data = True
        logging.info("检测到使用模拟数据进行选股")
    
    if selection_mode == 'price_trend':
        # 简单涨幅模式：只基于涨幅筛选
        logging.info("使用简单涨幅模式选股")
        
        # 遍历所有股票
        for _, stock in basic_info.iterrows():
            processed_count += 1
            if processed_count % 10 == 0:
                logging.info(f"已处理{processed_count}只股票，当前选中{len(selected_stocks)}只")
            
            stock_code = stock['code']
            
            if is_using_simulated_data:
                # 直接使用模拟数据中的信息
                latest_close = stock.get('latest_close', random.uniform(2, 300))
                price_trend = stock.get('price_trend', random.uniform(-10, 30))
            else:
                # 获取技术面数据
                k_data = get_stock_k_data(stock_code, days=price_trend_days + 5)  # 确保有足够的数据
                if k_data is None or len(k_data) < price_trend_days:
                    continue
                
                # 计算指定周期内的涨幅
                latest_close = k_data.iloc[-1]['close']
                if len(k_data) >= price_trend_days:
                    past_close = k_data.iloc[-price_trend_days]['close']
                    price_trend = (latest_close - past_close) / past_close * 100
                else:
                    continue
            
            # 涨幅筛选条件
            if price_trend_min <= price_trend <= price_trend_max:
                # 构建选股结果
                stock_info = {
                    'code': stock['code'],
                    'name': stock['name'],
                    'industry': stock.get('industry', '未知'),
                    'pe': stock['pe'],
                    'pb': stock['pb'],
                    'turnover_rate': stock['turnover_rate'],
                    'circulation_market_value': stock['circulation_market_value'],
                    'price_trend': price_trend,
                    'price_trend_days': price_trend_days,
                    'latest_close': latest_close
                }
                
                selected_stocks.append(stock_info)
                
                # 达到选股数量限制
                if len(selected_stocks) >= limit:
                    break
            
            # 仅当使用真实数据时添加延迟
            if not is_using_simulated_data:
                time.sleep(0.1)
        
        # 按涨幅排序
        selected_stocks.sort(key=lambda x: x['price_trend'], reverse=True)
    
    else:
        # 综合模式：基于基本面和技术面指标
        logging.info("使用综合模式选股")
        
        # 基本面筛选条件
        filtered_basic = basic_info[
            (basic_info['pe'] > pe_min) & (basic_info['pe'] < pe_max) &
            (basic_info['pb'] < pb_max) &
            (basic_info['circulation_market_value'] > market_cap_min)
        ]
        
        logging.info(f"基本面筛选后剩余{len(filtered_basic)}只股票")
        
        # 遍历筛选后的股票
        for _, stock in filtered_basic.iterrows():
            processed_count += 1
            if processed_count % 10 == 0:
                logging.info(f"已处理{processed_count}只股票，当前选中{len(selected_stocks)}只")
            
            stock_code = stock['code']
            
            if is_using_simulated_data:
                # 使用模拟数据中的信息
                latest_close = stock.get('latest_close', random.uniform(2, 300))
                price_trend = stock.get('price_trend', random.uniform(-10, 30))
                # 模拟技术指标
                technical_indicators = {
                    'is_ma_bullish': random.choice([True, False]),
                    'price_trend': price_trend,
                    'latest_close': latest_close,
                    'ma5': latest_close * random.uniform(0.95, 1.05),
                    'ma20': latest_close * random.uniform(0.9, 1.1),
                    'ma60': latest_close * random.uniform(0.85, 1.15)
                }
            else:
                # 获取技术面数据
                k_data = get_stock_k_data(stock_code)
                if k_data is None or len(k_data) < 60:
                    continue
                
                # 计算技术指标
                technical_indicators = calculate_technical_indicators(k_data)
            
            # 技术面筛选条件
            if technical_indicators['is_ma_bullish'] and technical_indicators['price_trend'] > 0:
                # 构建选股结果
                stock_info = {
                    'code': stock['code'],
                    'name': stock['name'],
                    'industry': stock.get('industry', '未知'),
                    'pe': stock['pe'],
                    'pb': stock['pb'],
                    'turnover_rate': stock['turnover_rate'],
                    'circulation_market_value': stock['circulation_market_value'],
                    'price_trend': technical_indicators['price_trend'],
                    'latest_close': technical_indicators['latest_close'],
                    'ma5': technical_indicators['ma5'],
                    'ma20': technical_indicators['ma20'],
                    'ma60': technical_indicators['ma60']
                }
                
                selected_stocks.append(stock_info)
                
                # 达到选股数量限制
                if len(selected_stocks) >= limit:
                    break
            
            # 添加小延迟避免请求过快
            time.sleep(0.1)
        
        # 按流通市值排序
        selected_stocks.sort(key=lambda x: x['circulation_market_value'], reverse=True)
    
    logging.info(f"共处理{processed_count}只股票，最终选中{len(selected_stocks)}只")
    
    return selected_stocks

def generate_stock_selection_report(limit: int = 10, selection_mode: str = 'comprehensive', 
                                    price_trend_days: int = 20, price_trend_min: float = 0, price_trend_max: float = 100, 
                                    pe_min: float = 0, pe_max: float = 30, pb_max: float = 5, market_cap_min: float = 1000000000) -> pd.DataFrame:
    """
    生成选股报告
    
    参数:
    - limit: 选股数量限制
    - selection_mode: 选股模式 ('comprehensive' 综合模式, 'price_trend' 简单涨幅模式)
    - price_trend_days: 涨幅计算周期（天）
    - price_trend_min: 最小涨幅（%）
    - price_trend_max: 最大涨幅（%）
    - pe_min: 最小市盈率
    - pe_max: 最大市盈率
    - pb_max: 最大市净率
    - market_cap_min: 最小流通市值
    """
    logging.info("开始生成选股报告...")
    
    # 优先使用会话中的模拟数据
    if "simulated_data" in st.session_state:
        logging.info("使用模拟数据进行选股")
        basic_info = st.session_state["simulated_data"]
    else:
        # 获取真实股票基本信息
        logging.info("尝试从akshare获取真实股票数据")
        basic_info = get_stock_basic_info()
        
        if basic_info is None:
            logging.error("无法获取股票基本信息，选股失败")
            st.error("无法从akshare获取真实股票数据，请先生成模拟数据")
            return pd.DataFrame()
    
    # 选股
    logging.info("开始选股...")
    selected_stocks = select_stocks(basic_info, limit=limit, selection_mode=selection_mode,
                                  price_trend_days=price_trend_days, price_trend_min=price_trend_min, price_trend_max=price_trend_max,
                                  pe_min=pe_min, pe_max=pe_max, pb_max=pb_max, market_cap_min=market_cap_min)
    
    # 转换为DataFrame
    report_df = pd.DataFrame(selected_stocks)
    
    logging.info(f"选股报告生成完成，共选中{len(report_df)}只股票")
    
    # 保存选股结果到CSV文件，以便main.py可以访问
    if not report_df.empty:
        csv_path = f"selected_stocks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        report_df.to_csv(csv_path, index=False)
        logging.info(f"选股结果已保存到{csv_path}文件")
        
        # 同时保存到分析工具需要的文件
        report_df.to_csv("selected_stocks_for_analysis.csv", index=False, encoding="utf-8-sig")
    
    return report_df

def main():
    """
    Streamlit应用入口函数
    """
    st.title("智能选股系统")
    st.markdown("基于基本面和技术面指标的股票筛选工具")
    
    # 选股参数设置
    with st.sidebar:
        st.header("选股参数")
        
        # 模拟数据生成选项
        with st.expander("📊 生成模拟数据", expanded=False):
            st.subheader("模拟数据设置")
            
            # 生成模拟数据的数量
            sim_stock_count = st.number_input("模拟股票数量", min_value=5, max_value=50, value=20, step=5)
            
            # 生成模拟数据按钮
            if st.button("生成模拟数据"):
                
                
                # 模拟股票代码和名称
                stock_codes = []
                stock_names = []
                stock_industries = []
                
                # 股票行业类别
                industries = ["银行", "科技", "医药", "消费", "能源", "地产", "制造", "传媒", "互联网", "通信"]
                
                for i in range(sim_stock_count):
                    # 随机生成股票代码
                    market = random.choice(["sh", "sz"])
                    code = market + str(random.randint(100000, 999999)).zfill(6)
                    stock_codes.append(code)
                    
                    # 随机选择行业
                    industry = random.choice(industries)
                    stock_industries.append(industry)
                    
                    # 随机生成股票名称
                    company = random.choice(["中国", "华夏", "东方", "南方", "北方", "西部", "联合", "国际", "环球", "全球"])
                    type_name = random.choice(["科技", "发展", "创新", "投资", "控股", "集团", "股份", "有限", "实业", "产业"])
                    stock_names.append(f"{company}{industry}{type_name}")
                
                # 生成模拟财务和市场数据
                sim_data = {
                    "code": stock_codes,
                    "name": stock_names,
                    "industry": stock_industries,
                    "pe": [round(random.uniform(5, 30), 2) for _ in range(sim_stock_count)],  # 市盈率5-30
                    "pb": [round(random.uniform(0.5, 5), 2) for _ in range(sim_stock_count)],  # 市净率0.5-5
                    "turnover_rate": [round(random.uniform(0.1, 5), 2) for _ in range(sim_stock_count)],  # 换手率0.1-5%
                    "circulation_market_value": [random.randint(5000000000, 500000000000) for _ in range(sim_stock_count)],  # 流通市值50亿-5000亿
                    "latest_close": [round(random.uniform(2, 300), 2) for _ in range(sim_stock_count)],  # 收盘价2-300元
                    "price_trend": [round(random.uniform(-10, 30), 2) for _ in range(sim_stock_count)]  # 涨幅-10%到30%
                }
                
                sim_df = pd.DataFrame(sim_data)
                
                # 保存模拟数据到CSV文件（用于分析工具）
                sim_df.to_csv("selected_stocks_for_analysis.csv", index=False, encoding="utf-8-sig")
                
                # 保存到会话状态
                st.session_state["simulated_data"] = sim_df
                
                st.success(f"已生成{sim_stock_count}只股票的模拟数据！")
            
            # 如果会话中有模拟数据，显示保存和查看功能
            if "simulated_data" in st.session_state:
                sim_df = st.session_state["simulated_data"]
                
                # 保存模拟数据
                st.subheader("保存模拟数据")
                
                # 创建模拟数据保存目录
                import os
                sim_data_dir = "simulation_data"
                if not os.path.exists(sim_data_dir):
                    os.makedirs(sim_data_dir)
                
                # 保存文件名输入
                save_name = st.text_input("保存文件名", value="模拟数据_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
                
                if st.button("保存当前模拟数据"):
                    # 保存到文件
                    save_path = os.path.join(sim_data_dir, f"{save_name}.csv")
                    sim_df.to_csv(save_path, index=False, encoding="utf-8-sig")
                    st.success(f"模拟数据已保存到：{save_path}")
                
                # 使用expander展示所有模拟数据
                with st.expander("查看所有模拟数据", expanded=True):
                    st.dataframe(sim_df, use_container_width=True)
                    
                # 提供下载选项
                csv = sim_df.to_csv(index=False, encoding="utf-8-sig")
                st.download_button(
                    label="下载模拟数据",
                    data=csv,
                    file_name="simulated_stocks.csv",
                    mime="text/csv"
                )
            
            # 加载保存的模拟数据
            st.subheader("加载保存的模拟数据")
            
            # 检查是否有保存的模拟数据
            import os
            sim_data_dir = "simulation_data"
            if os.path.exists(sim_data_dir):
                # 获取所有保存的模拟数据文件
                saved_files = [f for f in os.listdir(sim_data_dir) if f.endswith(".csv")]
                
                if saved_files:
                    # 选择要加载的文件
                    selected_file = st.selectbox("选择要加载的模拟数据", saved_files)
                    
                    if st.button("加载选中的模拟数据"):
                        # 加载数据
                        load_path = os.path.join(sim_data_dir, selected_file)
                        loaded_df = pd.read_csv(load_path, encoding="utf-8-sig")
                        
                        # 保存到会话状态
                        st.session_state["simulated_data"] = loaded_df
                        
                        # 同时保存到分析工具需要的文件
                        loaded_df.to_csv("selected_stocks_for_analysis.csv", index=False, encoding="utf-8-sig")
                        
                        st.success(f"已加载模拟数据：{selected_file}（共{len(loaded_df)}只股票）")
                        
                        # 显示加载的数据
                        with st.expander("查看加载的模拟数据", expanded=True):
                            st.dataframe(loaded_df, use_container_width=True)
                else:
                    st.info("还没有保存的模拟数据")
            else:
                st.info("还没有保存的模拟数据")
        
        # 选股模式选择
        selection_mode = st.radio(
            "选股模式",
            options=['comprehensive', 'price_trend'],
            format_func=lambda x: "综合模式" if x == 'comprehensive' else "简单涨幅模式",
            index=0
        )
        
        limit = st.slider("选股数量", min_value=5, max_value=30, value=10)
        
        if selection_mode == 'price_trend':
            # 简单涨幅模式参数
            st.subheader("涨幅参数")
            price_trend_days = st.slider("涨幅计算周期(天)", min_value=5, max_value=120, value=20, step=5)
            price_trend_min = st.number_input("最小涨幅(%)", min_value=-100.0, max_value=100.0, value=0.0, step=1.0)
            price_trend_max = st.number_input("最大涨幅(%)", min_value=-100.0, max_value=1000.0, value=50.0, step=1.0)
            
        else:
            # 综合模式参数
            # 基本面参数
            st.subheader("基本面参数")
            pe_min = st.number_input("最小市盈率(PE)", min_value=0.0, max_value=100.0, value=0.0, step=0.1)
            pe_max = st.number_input("最大市盈率(PE)", min_value=0.0, max_value=100.0, value=30.0, step=0.1)
            pb_max = st.number_input("最大市净率(PB)", min_value=0.0, max_value=20.0, value=5.0, step=0.1)
            
            # 技术面参数
            st.subheader("技术面参数")
            ma_days = st.slider("均线周期(天)", min_value=30, max_value=180, value=120, step=10)
            
        # 运行按钮
        run_button = st.button("开始选股")
    
    # 主内容区
    if run_button:
        with st.spinner("正在获取股票数据..."):
            # 根据选股模式准备参数
            if selection_mode == 'price_trend':
                # 简单涨幅模式
                stock_report = generate_stock_selection_report(
                    limit=limit, 
                    selection_mode=selection_mode,
                    price_trend_days=price_trend_days,
                    price_trend_min=price_trend_min,
                    price_trend_max=price_trend_max
                )
            else:
                # 综合模式
                stock_report = generate_stock_selection_report(
                    limit=limit, 
                    selection_mode=selection_mode,
                    pe_min=pe_min,
                    pe_max=pe_max,
                    pb_max=pb_max
                )
        
        if not stock_report.empty:
            st.success(f"选股完成！共选中{len(stock_report)}只股票")
            
            # 显示选股结果
            st.subheader("选股结果")
            
            # 显示数据表格
            st.dataframe(stock_report, use_container_width=True)
            
            # 保存到CSV
            csv_data = stock_report.to_csv(index=False)
            st.download_button(
                label="下载选股结果",
                data=csv_data,
                file_name=f"selected_stocks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
            # 与main.py交互的选项
            st.subheader("后续操作")
            if st.button("使用选中股票进行详细分析"):
                # 将选股结果保存到一个固定名称的文件，以便main.py可以读取
                stock_report.to_csv("selected_stocks_for_analysis.csv", index=False)
                st.success("选股结果已保存，您可以在股票数据分析工具中查看详细分析")
        else:
            st.error("未选到符合条件的股票，请调整选股参数后重试")
    else:
        st.info("请设置选股参数并点击'开始选股'按钮")

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    main()