import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from data import (
    TICKERS,
    TICKER_LABELS,
    fetch_stock_data,
    get_close,
    get_volume,
    get_ohlcv,
    normalize_prices,
    compute_metrics,
)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="B3 Dashboard 2025",
    page_icon="📈",
    layout="wide",
)

st.title("📈 B3 Dashboard 2025")
st.caption("Cotações de PETR4, ITUB4 e VALE3 ao longo de 2025 — dados via yfinance")

# ── Load data ──────────────────────────────────────────────────────────────────
with st.spinner("Buscando dados do mercado…"):
    raw_df = fetch_stock_data()

close_all = get_close(raw_df)
volume_all = get_volume(raw_df)
labels = list(TICKER_LABELS.values())  # ['PETR4', 'ITUB4', 'VALE3']

if close_all.empty:
    st.error("Não foi possível carregar os dados do Yahoo Finance. Aguarde alguns segundos e recarregue a página (F5).")
    st.stop()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filtros")

    # Date range slider
    valid_index = close_all.index.dropna()
    min_date = valid_index.min().date()
    max_date = valid_index.max().date()
    date_range = st.slider(
        "Período",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="DD/MM/YYYY",
    )
    start_date, end_date = date_range

    # Ticker checkboxes
    st.subheader("Ações")
    selected = [label for label in labels if st.checkbox(label, value=True)]

    if not selected:
        st.warning("Selecione ao menos uma ação.")
        st.stop()

# ── Filter by date and selected tickers ───────────────────────────────────────
mask = (close_all.index.date >= start_date) & (close_all.index.date <= end_date)
close_filtered = close_all.loc[mask, selected]
volume_filtered = volume_all.loc[mask, selected]

# ── Metrics row ────────────────────────────────────────────────────────────────
st.subheader("Métricas do Período")
cols = st.columns(len(selected))

for col, label in zip(cols, selected):
    # Find the SA ticker key for this label
    ticker_sa = next(k for k, v in TICKER_LABELS.items() if v == label)
    metrics = compute_metrics(close_filtered, volume_filtered, label)

    if metrics:
        col.metric(
            label=f"**{label}**",
            value=f"R$ {metrics['current_price']:.2f}",
            delta=f"{metrics['returns_pct']:+.2f}% no período",
        )
        col.caption(
            f"Máx: R$ {metrics['max_price']:.2f} | "
            f"Mín: R$ {metrics['min_price']:.2f} | "
            f"Vol. anualizada: {metrics['annualized_vol']:.1f}% | "
            f"Vol. médio: {metrics['avg_volume']:,.0f}"
        )

st.divider()

# ── Chart 1: Normalized prices ─────────────────────────────────────────────────
st.subheader("Preço Normalizado (base 100)")
st.caption("Permite comparar a performance relativa das ações em escalas diferentes.")

norm = normalize_prices(close_filtered)
norm_melted = norm.reset_index().melt(id_vars="Date", var_name="Ação", value_name="Índice")

fig1 = px.line(
    norm_melted,
    x="Date",
    y="Índice",
    color="Ação",
    labels={"Date": "Data", "Índice": "Índice (base 100)"},
    template="plotly_dark",
)
fig1.add_hline(y=100, line_dash="dash", line_color="gray", opacity=0.5)
fig1.update_layout(legend_title_text="Ação", hovermode="x unified")
st.plotly_chart(fig1, use_container_width=True)

st.divider()

# ── Chart 2: Daily volume ──────────────────────────────────────────────────────
st.subheader("Volume Diário")
vol_ticker_label = st.selectbox(
    "Selecione a ação para o volume",
    options=selected,
    key="volume_select",
)

vol_df = volume_filtered[[vol_ticker_label]].reset_index()
vol_df.columns = ["Date", "Volume"]

fig2 = px.bar(
    vol_df,
    x="Date",
    y="Volume",
    labels={"Date": "Data", "Volume": "Volume"},
    title=f"Volume diário — {vol_ticker_label}",
    template="plotly_dark",
    color_discrete_sequence=["#00b4d8"],
)
fig2.update_layout(hovermode="x unified")
st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Chart 3: Candlestick OHLC ──────────────────────────────────────────────────
st.subheader("Candlestick OHLC")
candle_label = st.selectbox(
    "Selecione a ação para o candlestick",
    options=selected,
    key="candle_select",
)

candle_ticker_sa = next(k for k, v in TICKER_LABELS.items() if v == candle_label)
ohlcv = get_ohlcv(raw_df, candle_ticker_sa)

# Filter ohlcv to selected period
ohlcv_mask = (ohlcv.index.date >= start_date) & (ohlcv.index.date <= end_date)
ohlcv_filtered = ohlcv.loc[ohlcv_mask]

fig3 = go.Figure(
    data=[
        go.Candlestick(
            x=ohlcv_filtered.index,
            open=ohlcv_filtered["Open"],
            high=ohlcv_filtered["High"],
            low=ohlcv_filtered["Low"],
            close=ohlcv_filtered["Close"],
            name=candle_label,
            increasing_line_color="#26a641",
            decreasing_line_color="#e63946",
        )
    ]
)
fig3.update_layout(
    title=f"Candlestick OHLC — {candle_label}",
    xaxis_title="Data",
    yaxis_title="Preço (R$)",
    template="plotly_dark",
    xaxis_rangeslider_visible=False,
    hovermode="x unified",
)
st.plotly_chart(fig3, use_container_width=True)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Dados fornecidos por [Yahoo Finance](https://finance.yahoo.com) via yfinance. "
    "Apenas para fins informativos, não constitui recomendação de investimento."
)
