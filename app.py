import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from portfolio_logic import calculate_portfolio_data, get_historical_performance


# --- CONFIG ---
st.set_page_config(page_title="Portfolio Terminal", layout="wide")


# Daten laden mit Spinner-Animation
with st.spinner('Lade Marktdaten...'):
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


# --- HEADER (Zentriert mit Geldsäcken) ---
h_left, h_mid, h_right = st.columns([1, 3, 1])
with h_mid:
    st.markdown("<h1 style='text-align: center;'>💰 Portfolio Terminal 💰</h1>", unsafe_allow_html=True)


with h_right:
    st.write("##")
    if st.button("🔄 Aktualisieren", width='stretch'):
        st.cache_data.clear()
        st.rerun()


# --- METRIKEN ---
m1, m2, m3 = st.columns(3)


stock_val = data_pkg['total_stock_val']
total_invested_all_in = data_pkg['total_invested'] + data_pkg['total_fees']
total_net_worth = stock_val + cash


if total_invested_all_in > 0:
    total_perf_pct = ((stock_val / total_invested_all_in) - 1) * 100
    total_perf_abs = stock_val - total_invested_all_in
else:
    total_perf_pct = 0.0
    total_perf_abs = 0.0


daily_delta_pct = 0.0
daily_delta_abs = 0.0
if len(h_df) >= 2:
    prev_val_h = h_df['Marktwert_CHF'].iloc[-2]
    current_val_h = h_df['Marktwert_CHF'].iloc[-1]
    daily_delta_abs = current_val_h - prev_val_h
    daily_delta_pct = (daily_delta_abs / prev_val_h) * 100


m1.metric(
    label="Net Worth (Gesamt)",
    value=f"{total_net_worth:,.2f} CHF".replace(",", "'"),
    delta=f"{total_perf_pct:.2f}% ({total_perf_abs:+.2f} CHF)"
)


m2.metric(
    label="Equity (Heute)",
    value=f"{stock_val:,.2f} CHF".replace(",", "'"),
    delta=f"{daily_delta_pct:.2f}% ({daily_delta_abs:+.2f} CHF)"
)


m3.metric("Liquidity", f"{cash:,.2f} CHF".replace(",", "'"))


st.divider()


# --- GRAPH BEREICH ---
st.subheader("📈 Performance Verlauf")


if not h_df.empty:
    h_df['Gain_ABS'] = (h_df['Marktwert_CHF'] - h_df['Einsatz_CHF']).round(2)
    h_df['Perf_PCT'] = ((h_df['Marktwert_CHF'] / h_df['Einsatz_CHF'] - 1) * 100).round(2)


    latest_val = h_df['Marktwert_CHF'].iloc[-1]
    latest_invested = h_df['Einsatz_CHF'].iloc[-1]
   
    perf_line_color = "#2E7D32" if latest_val >= latest_invested else "#DC2626"
    fill_color = "rgba(46, 125, 50, 0.3)" if latest_val >= latest_invested else "rgba(220, 38, 38, 0.3)"


    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(
        x=h_df['Datum'], y=h_df['Einsatz_CHF'], name="Einsatz",
        line=dict(width=4, color="#5D6D7E"),
        hovertemplate="Einsatz: %{y:,.2f} CHF<extra></extra>"
    ))
    fig_line.add_trace(go.Scatter(
        x=h_df['Datum'], y=h_df['Marktwert_CHF'], name="Marktwert",
        fill='tonexty', fillcolor=fill_color, line=dict(width=3, color=perf_line_color),
        customdata=h_df[['Gain_ABS', 'Perf_PCT']],
        hovertemplate="<b>Marktwert: %{y:,.2f} CHF</b><br>Gain: %{customdata[0]:+,.2f} CHF<br>Perf: %{customdata[1]:+.2f}%<extra></extra>"
    ))


    fig_line.update_layout(
        template="plotly_white", height=450, margin=dict(l=20, r=20, t=30, b=20),
        hovermode="x unified",
        yaxis=dict(title="Wert in CHF", tickformat=",.0f", separatethousands=True),
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1T", step="day", stepmode="backward"),
                    dict(count=7, label="1W", step="day", stepmode="backward"),
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                    dict(step="all", label="ALL")
                ])
            ),
            type="date"
        )
    )
    st.plotly_chart(fig_line, width='stretch')


st.divider()


# --- UNTERER BEREICH ---
col_main, col_side = st.columns([2, 1])


with col_main:
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
        df[cols].style.map(style_positive_negative, subset=[c for c in ["Stock Gain", "FX Gain", "Total Gain"] if c in cols]).format(precision=2),
        width='stretch', height=105
    )


    st.write("##")


    st.subheader("🗓️ Monatliche Performance & YTD")
    if not h_df.empty:
        h_copy = h_df.copy()
        h_copy['Datum'] = pd.to_datetime(h_copy['Datum'])
        h_copy['Jahr'] = h_copy['Datum'].dt.year
        h_copy['Monat'] = h_copy['Datum'].dt.month
       
        m_df = h_copy.groupby(['Jahr', 'Monat']).agg({'Marktwert_CHF': 'last', 'Einsatz_CHF': 'last'}).reset_index()
        m_df['Returns'] = m_df['Marktwert_CHF'].pct_change() * 100
        idx0 = m_df.index[0]
        m_df.loc[idx0, 'Returns'] = ((m_df.loc[idx0, 'Marktwert_CHF'] / m_df.loc[idx0, 'Einsatz_CHF']) - 1) * 100
       
        pivot_heat = m_df.pivot(index='Jahr', columns='Monat', values='Returns')
        pivot_heat['YTD'] = pivot_heat.sum(axis=1)
        m_names = {1:"Jan", 2:"Feb", 3:"Mär", 4:"Apr", 5:"Mai", 6:"Jun", 7:"Jul", 8:"Aug", 9:"Sep", 10:"Okt", 11:"Nov", 12:"Dez"}
        pivot_heat = pivot_heat.rename(columns=m_names)


        fig_heat = go.Figure(data=go.Heatmap(
            z=pivot_heat.values, x=pivot_heat.columns, y=pivot_heat.index,
            colorscale='RdYlGn', zmid=0, text=pivot_heat.values, texttemplate="%{text:.2f}%",
            hoverongaps=False, showscale=False
        ))
        fig_heat.update_layout(height=200, margin=dict(t=30, b=10, l=10, r=10), xaxis=dict(side="top", dtick=1), yaxis=dict(dtick=1))
        st.plotly_chart(fig_heat, width='stretch')


with col_side:
    st.subheader("🥧 Diversifikation")
    val_col = 'Wert (CHF)' if pie_mode == "Marktwert" else 'Investiert (CHF)'
    pie_df = pd.concat([df[['Name', val_col]], pd.DataFrame([{"Name": "CASH", val_col: cash}])])
    fig_pie = go.Figure(data=[go.Pie(labels=pie_df['Name'], values=pie_df[val_col], hole=.4)])
    fig_pie.update_layout(margin=dict(t=30, b=0, l=0, r=0), height=450, legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
    st.plotly_chart(fig_pie, width='stretch')