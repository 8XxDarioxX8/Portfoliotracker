import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from portfolio_logic import calculate_portfolio_data, get_historical_performance

# --- CONFIG ---
st.set_page_config(page_title="Portfolio Terminal", layout="wide")

# Daten laden
try:
    data_pkg = calculate_portfolio_data()
    df = data_pkg['df']
    h_df = get_historical_performance()
    cash = data_pkg['cash']
except Exception as e:
    st.error(f"Fehler beim Laden: {e}")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Steuerung")
    show_ticker = st.toggle("Ticker anzeigen", value=False)
    show_details = st.toggle("FX/Stock Details anzeigen", value=True)
    show_fees = st.toggle("Gebühren anzeigen", value=True)
    st.divider()
    pie_mode = st.radio("Fokus Diversifikation:", ["Investiert", "Marktwert"])

# --- HEADER ---
head_col1, head_col2 = st.columns([4, 1])
with head_col1:
    st.title("📊 Portfolio Terminal")
with head_col2:
    st.write("##") 
    if st.button("🔄 Aktualisieren", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# --- METRIKEN ---
m1, m2, m3 = st.columns(3)
total_val = data_pkg['total_val_with_fees']
daily_delta_pct = 0.0 
if len(h_df) >= 2:
    prev_val = h_df['Marktwert_CHF'].iloc[-2]
    current_val = h_df['Marktwert_CHF'].iloc[-1]
    daily_delta_pct = ((current_val - prev_val) / prev_val) * 100

m1.metric("Net Worth", f"{total_val:,.2f} CHF".replace(",", "'"), delta=f"{daily_delta_pct:.2f}%")
m2.metric("Equity", f"{data_pkg['total_stock_val']:,.2f} CHF".replace(",", "'"))
m3.metric("Liquidity", f"{cash:,.2f} CHF".replace(",", "'"))

st.divider()

# --- GRAPH BEREICH ---
st.subheader("📈 Performance Verlauf")

if not h_df.empty:
    latest_val = h_df['Marktwert_CHF'].iloc[-1]
    latest_invested = h_df['Einsatz_CHF'].iloc[-1]
    
    # Bestimmung der Farben basierend auf Performance
    # Grün wenn Marktwert >= Einsatz, sonst Rot
    perf_line_color = "#2E7D32" if latest_val >= latest_invested else "#DC2626"
    fill_color = "rgba(46, 125, 50, 0.3)" if latest_val >= latest_invested else "rgba(220, 38, 38, 0.3)"

    fig_line = go.Figure()
    
    # 1. Einsatz-Linie: DICKE Linie (width=4)
    fig_line.add_trace(go.Scatter(
        x=h_df['Datum'], y=h_df['Einsatz_CHF'], 
        name="Einsatz", 
        line=dict(width=4, color="#5D6D7E")
    ))
    
    # 2. Marktwert-Linie mit dynamischer Füllung zum Einsatz hin
    fig_line.add_trace(go.Scatter(
        x=h_df['Datum'], y=h_df['Marktwert_CHF'], 
        name="Marktwert", 
        fill='tonexty',          # Füllt den Bereich zur vorherigen Spur (Einsatz)
        fillcolor=fill_color, 
        line=dict(width=3, color=perf_line_color)
    ))

    fig_line.update_layout(
        template="plotly_white", 
        height=450, 
        margin=dict(l=20, r=20, t=30, b=20),
        hovermode="x unified",
        xaxis=dict(rangeselector=dict(
            buttons=list([
                dict(count=1, label="1T", step="day", stepmode="backward"),
                dict(count=7, label="1W", step="day", stepmode="backward"),
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(step="all", label="ALL")
            ])
        ))
    )
    st.plotly_chart(fig_line, use_container_width=True)

st.divider()

# --- UNTERER BEREICH ---
col_table, col_pie = st.columns([2, 1])

with col_table:
    st.subheader("📋 Asset Übersicht")
    
    cols = ["Name"]
    if show_ticker: cols.append("Ticker")
    cols.extend(["Menge", "Wert (CHF)", "Investiert (CHF)"])
    if show_details: cols.extend(["Stock Gain", "FX Gain"])
    cols.append("Total Gain")
    if show_fees: cols.append("Gebühren")

    def style_positive_negative(val):
        if isinstance(val, (int, float)):
            if val > 0: return 'color: green; font-weight: bold;'
            if val < 0: return 'color: red; font-weight: bold;'
        return ''

    st.dataframe(
        df[cols].style.applymap(style_positive_negative, subset=[c for c in ["Stock Gain", "FX Gain", "Total Gain"] if c in cols]).format(precision=2),
        use_container_width=True, 
        height=110
    )

with col_pie:
    st.subheader("🥧 Diversifikation")
    val_col = 'Wert (CHF)' if pie_mode == "Marktwert" else 'Investiert (CHF)'
    pie_df = pd.concat([df[['Name', val_col]], pd.DataFrame([{"Name": "CASH", val_col: cash}])])
    
    fig_pie = go.Figure(data=[go.Pie(
        labels=pie_df['Name'], 
        values=pie_df[val_col], 
        hole=.4
    )])
    fig_pie.update_layout(
        margin=dict(t=30, b=0, l=0, r=0), 
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_pie, use_container_width=True)