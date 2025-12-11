import pandas as pd
import streamlit as st
import altair as alt

def plot_stock_data(df: pd.DataFrame):
    """绘制股票价格图"""
    if df.empty:
        return
    
    # 确保索引是日期类型
    if not isinstance(df.index, pd.DatetimeIndex):
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
    
    # 创建Altair图表
    chart = alt.Chart(df.reset_index()).mark_line().encode(
        x=alt.X('date:T', title='日期'),
        y=alt.Y('close:Q', title='价格'),
        tooltip=['date:T', 'close:Q']
    ).properties(
        title='股票价格走势',
        width=800,
        height=300
    ).configure_title(
        fontSize=16
    ).configure_axis(
        labelFontSize=12,
        titleFontSize=14,
        grid=True
    ).configure_view(
        stroke=None
    )
    
    st.altair_chart(chart, use_container_width=True)

def plot_pe_analysis(pe_df: pd.DataFrame, forecast_df: pd.DataFrame):
    """绘制PE分析图"""
    # 确保索引是日期类型
    if not isinstance(pe_df.index, pd.DatetimeIndex):
        pe_df = pe_df.copy()
        pe_df['date'] = pd.to_datetime(pe_df['date'])
        pe_df = pe_df.set_index('date')
    
    # 重置索引以便Altair处理
    pe_df_reset = pe_df.reset_index()
    
    # 创建基础图表
    base = alt.Chart(pe_df_reset).encode(
        x=alt.X('date:T', title='日期'),
        y=alt.Y('PE:Q', title='PE'),
        tooltip=['date:T', 'PE:Q']
    )
    
    # 实际PE线
    actual_pe = base.mark_line(color='#1f77b4', strokeWidth=2).encode(
        y=alt.Y('PE:Q', title='PE')
    )
    
    # PE移动平均线
    pe_ma = base.mark_line(color='#ff7f0e', strokeWidth=2, strokeDash=[5, 5]).encode(
        y=alt.Y('PE_MA:Q', title='PE')
    )
    
    # 组合图表
    chart = alt.layer(actual_pe, pe_ma).properties(
        title='市盈率分析',
        width=800,
        height=300
    ).configure_title(
        fontSize=16
    ).configure_axis(
        labelFontSize=12,
        titleFontSize=14,
        grid=True
    ).configure_view(
        stroke=None
    )
    
    # 如果有预测数据，添加预测PE线
    if not forecast_df.empty:
        # 确保预测数据的索引是日期类型
        if not isinstance(forecast_df.index, pd.DatetimeIndex):
            forecast_df = forecast_df.copy()
            forecast_df['date'] = pd.to_datetime(forecast_df['date'])
            forecast_df = forecast_df.set_index('date')
        
        forecast_df_reset = forecast_df.reset_index()
        
        # 预测PE线
        predicted_pe = alt.Chart(forecast_df_reset).mark_line(
            color='#2ca02c', 
            strokeWidth=2, 
            strokeDash=[3, 3]
        ).encode(
            x='date:T',
            y='predicted_PE:Q',
            tooltip=['date:T', 'predicted_PE:Q']
        )
        
        # 添加到组合图表中
        chart = alt.layer(actual_pe, pe_ma, predicted_pe).properties(
            title='市盈率分析',
            width=800,
            height=300
        ).configure_title(
            fontSize=16
        ).configure_axis(
            labelFontSize=12,
            titleFontSize=14,
            grid=True
        ).configure_view(
            stroke=None
        )
    
    st.altair_chart(chart, use_container_width=True)