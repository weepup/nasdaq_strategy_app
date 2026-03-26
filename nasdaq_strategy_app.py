import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- 页面配置 ---
st.set_page_config(page_title="纳指双轨趋势择时工具", layout="wide")
st.title("📈 QQQ 纳指双轨趋势择时信号灯")
st.caption("基于方案 1：双轨趋势层进策略 | 自动获取最新收盘价")

# --- 1. 数据获取 ---
@st.cache_data(ttl=3600)  # 缓存 1 小时，避免频繁请求
def get_data(ticker="QQQ"):
    df = yf.download(ticker, period="2y", interval="1d")
    # 清洗多级索引（yfinance新版特性）
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

try:
    data = get_data()
    
    # --- 2. 指标计算 ---
    data['MA50'] = ta.sma(data['Close'], length=50)
    data['MA200'] = ta.sma(data['Close'], length=200)
    data['RSI'] = ta.rsi(data['Close'], length=14)
    
    last_price = data['Close'].iloc[-1]
    last_ma50 = data['MA50'].iloc[-1]
    last_ma200 = data['MA200'].iloc[-1]
    last_rsi = data['RSI'].iloc[-1]
    prev_price = data['Close'].iloc[-2]
    
    # --- 3. 信号逻辑判定 ---
    # 规则 A: 价格 > MA200 (40%)
    cond_a = last_price > last_ma200
    # 规则 B: MA50 > MA200 (30%)
    cond_b = last_ma50 > last_ma200
    # 规则 C: RSI < 45 且处于牛市 (30%)
    cond_c = cond_a and (last_rsi < 45)

    # 计算目标总仓位
    target_position = 0
    if cond_a:
        target_position += 40
        if cond_b:
            target_position += 30
        if cond_c:
            target_position += 30

    # 减仓逻辑
    exit_signal = "无"
    if last_price < last_ma200:
        exit_signal = "【清仓】跌破 200 日线"
    elif last_price < last_ma50:
        exit_signal = "【预警】跌破 50 日线，建议减持至 50% 基准仓位"

    # --- 4. 仪表盘布局 ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("最新价格 (QQQ)", f"${last_price:.2f}", f"{((last_price/prev_price)-1)*100:.2f}%")
    col2.metric("200日牛熊线", f"${last_ma200:.2f}", f"乖离: {((last_price/last_ma200)-1)*100:.1f}%")
    col3.metric("RSI (14)", f"{last_rsi:.1f}")
    col4.metric("建议目标仓位", f"{target_position}%")

    # --- 5. 交互式图表 ---
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index, y=data['Close'], name='QQQ 收盘价', line=dict(color='white', width=1.5)))
    fig.add_trace(go.Scatter(x=data.index, y=data['MA50'], name='50日中期线', line=dict(color='orange', dash='dot')))
    fig.add_trace(go.Scatter(x=data.index, y=data['MA200'], name='200日牛熊线', line=dict(color='red', width=2)))
    
    fig.update_layout(height=500, template="plotly_dark", title="趋势分析图（日线）",
                      xaxis_rangeslider_visible=False, margin=dict(l=20, r=20, t=50, b=20))
    st.plotly_chart(fig, use_container_width=True)

    # --- 6. 决策建议区 ---
    st.subheader("🛠 交易执行指令")
    
    if target_position > 0:
        c1, c2 = st.columns([1, 3])
        with c1:
            st.success(f"当前建议总仓位：{target_position}%")
        with c2:
            detail = []
            if cond_a: detail.append("✅ 价格高于200日线 (基础仓位 40% OK)")
            if cond_b: detail.append("✅ 均线金叉 (加仓 30% OK)")
            if cond_c: detail.append("🎯 RSI低位回踩 (触发补仓 30%)")
            st.write(" | ".join(detail))
    else:
        st.error("🚨 当前处于空仓区间或等待信号中")

    if exit_signal != "无":
        st.warning(f"卖出预警：{exit_signal}")

    with st.expander("查看策略规则说明"):
        st.markdown("""
        - **建仓 1 (40%)**: 收盘价 > 200日均线。
        - **建仓 2 (30%)**: 50日均线 > 200日均线（趋势确认）。
        - **建仓 3 (30%)**: 满足前两条时，若 RSI < 45 触发超卖买入。
        - **减仓**: 跌破 50 日均线减半；跌破 200 日均线清仓。
        """)

except Exception as e:
    st.error(f"数据加载失败，请检查网络连接。错误详情: {e}")