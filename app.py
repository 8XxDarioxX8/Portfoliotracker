import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from portfolio_logic import calculate_portfolio_data, get_historical_performance, ISIN_MAP

# --- CONFIG ---
st.set_page_config(page_title="Portfolio Terminal", layout="wide")

# --- CUSTOM STYLING (Helles Beige & Erdtöne) ---
st.markdown("""
    <style>
    /* Haupt-Hintergrund auf ein edles helles Beige */
    .stApp {
        background-color: #fFFFFF; /* Helles Beige */
        color: #102820; /* Dunkelgrüne Schrift für hohen Kontrast */
    }

    /* Sidebar: Dunkelgrün für den starken Kontrast zum Beige */
    [data-testid="stSidebar"] {
        background-color: #102820 !important;
    }
    [data-testid="stSidebar"] * {
        color: #FFFFFF !important;
    }

    /* Metrik-Karten: Weißer Hintergrund auf Beige wirkt sehr sauber */
    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #CABA9C; /* Khaki-Rahmen */
        padding: 20px;
        border-radius: 12px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
    }
    
    /* Metrik-Werte (Zahlen) in Dunkelgrün */
    [data-testid="stMetricValue"] {
        color: #102820 !important;
    }
    
    /* Metrik-Labels (Titel) in Hunter Green */
    [data-testid="stMetricLabel"] p {
        color: #4C6444 !important;
        font-weight: bold;
    }

    /* Buttons: Hunter Green mit weißer Schrift */
    .stButton>button {
        background-color: #4C6444 !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px;
        font-weight: bold;
    }

    .stButton>button:hover {
        background-color: #102820 !important;
        color: #CABA9C !important;
    }

    /* Überschriften in Dunkelgrün */
    h1, h2, h3 {
        color: #102820 !important;
    }

    /* Trennlinien dezent in Khaki */
    hr {
        border-top: 1px solid #CABA9C !important;
    }

    /* Tabellen-Styling */
    .stDataFrame {
        background-color: #FFFFFF;
        border-radius: 10px;
    }
    </style>
    """,
      unsafe_allow_html=True)

# ISIN zu Name Mapping
ISIN_NAME_MAP = {
    'IE00B4L5YC18': 'MSCI Emerging Markets',
    'IE00B4L5Y983': 'MSCI World'
}

# Daten laden mit Spinner-Animation
with st.spinner('Lade Marktdaten...'):
    try:
        data_pkg = calculate_portfolio_data()
        df = data_pkg['df']
        h_df = get_historical_performance()
        cash = data_pkg['cash']
        
        # ISINs durch Namen ersetzen in allen relevanten Spalten
        if 'Name' in df.columns:
            df['Name'] = df['Name'].replace(ISIN_NAME_MAP)
        if 'Ticker' in df.columns:
            df['Ticker_Original'] = df['Ticker']  # Original behalten für Links
        
        # WICHTIG: Transaktionen gruppieren (gleiche ISINs zusammenfassen)
        if not df.empty:
            # Spalten die summiert werden sollen
            sum_cols = ['Menge', 'Wert (CHF)', 'Investiert (CHF)']
            if 'Stock Gain' in df.columns:
                sum_cols.append('Stock Gain')
            if 'FX Gain' in df.columns:
                sum_cols.append('FX Gain')
            if 'Total Gain' in df.columns:
                sum_cols.append('Total Gain')
            if 'Gebühren' in df.columns:
                sum_cols.append('Gebühren')
            
            # Gruppiere nach Name (oder Ticker falls vorhanden)
            group_by = 'Name'
            agg_dict = {col: 'sum' for col in sum_cols if col in df.columns}
            
            # Behalte erste Werte für Ticker
            if 'Ticker' in df.columns:
                agg_dict['Ticker'] = 'first'
            if 'Ticker_Original' in df.columns:
                agg_dict['Ticker_Original'] = 'first'
            
            df = df.groupby(group_by, as_index=False).agg(agg_dict)
        
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
h_left, h_mid, h_right = st.columns([1, 3, 1])
with h_mid:
    st.markdown("<h1 style='text-align: center;'>💰 Portfolio Terminal 💰</h1>", unsafe_allow_html=True)

with h_right:
    st.write("##")
    if st.button("🔄 Aktualisieren", use_container_width=True):
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

# GEÄNDERT: Tagesperformance seit erstem Datenpunkt des Tages
daily_delta_pct = 0.0
daily_delta_abs = 0.0
if len(h_df) >= 2:
    h_copy = h_df.copy()
    h_copy['Datum'] = pd.to_datetime(h_copy['Datum'])
    
    # Heutiges Datum (ohne Uhrzeit)
    today = pd.Timestamp.now().normalize()
    
    # Alle Einträge von heute
    today_data = h_copy[h_copy['Datum'].dt.normalize() == today]
    
    if len(today_data) > 0:
        # Erster Wert von heute (Tagesbeginn)
        first_today = today_data['Marktwert_CHF'].iloc[0]
        # Aktueller Wert (letzter Eintrag von heute)
        current_val_h = today_data['Marktwert_CHF'].iloc[-1]
        
        daily_delta_abs = current_val_h - first_today
        daily_delta_pct = (daily_delta_abs / first_today) * 100
    else:
        # Fallback: Vergleich zum letzten verfügbaren Tag
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
st.subheader("📈 Performance Verlauf 📈")

if not h_df.empty:
    # WICHTIG: Daten ab 06.12.2025 filtern
    h_df_filtered = h_df.copy()
    h_df_filtered['Datum'] = pd.to_datetime(h_df_filtered['Datum'])
    start_date = pd.to_datetime('2025-12-06').tz_localize('UTC')  # UTC Timezone hinzufügen
    h_df_filtered = h_df_filtered[h_df_filtered['Datum'] >= start_date].copy()
    
    h_df_filtered['Gain_ABS'] = (h_df_filtered['Marktwert_CHF'] - h_df_filtered['Einsatz_CHF']).round(2)
    h_df_filtered['Perf_PCT'] = ((h_df_filtered['Marktwert_CHF'] / h_df_filtered['Einsatz_CHF'] - 1) * 100).round(2)

    fig_line = go.Figure()

    # --- LEGENDEN-TRICK (Rot & Grün Übereinander erzwingen) ---
    fig_line.add_trace(go.Scatter(
        x=[None], y=[None], mode='lines',
        line=dict(color="#2E6C2E", width=4),
        name='Marktwert (Profit)', 
        legendgroup="mw",
        showlegend=True
    ))
    fig_line.add_trace(go.Scatter(
        x=[None], y=[None], mode='lines',
        line=dict(color="#BE0404", width=4),
        name='Marktwert (Loss)', 
        legendgroup="mw",
        showlegend=True
    ))

    # 1. Einsatz-Linie (Grau)
    fig_line.add_trace(go.Scatter(
        x=h_df_filtered['Datum'], y=h_df_filtered['Einsatz_CHF'], name="Einsatz-Basis",
        line=dict(width=3, color="#000000"),
        showlegend=True
    ))

    # --- LAYOUT ANPASSUNG FÜR VERTIKALE LEGENDE ---
    fig_line.update_layout(
        template="plotly_white",
        paper_bgcolor='white', 
        plot_bgcolor='white',
        height=450, 
        margin=dict(l=40, r=150, t=30, b=20),
        hovermode="x unified",
        legend=dict(
            orientation="v",
            yanchor="top", 
            y=1, 
            xanchor="left", 
            x=1.02,
            font=dict(size=12)
        ),
        yaxis=dict(
            gridcolor='#f0f0f0', 
            tickformat=",.0f",
            separatethousands=True
        ),
        xaxis=dict(
            gridcolor='#f0f0f0',
            type="date",
            rangebreaks=[
                dict(bounds=["sat", "mon"]),  # Wochenenden ausblenden
            ]
        )
    )

    marktwert = h_df_filtered['Marktwert_CHF']
    einsatz = h_df_filtered['Einsatz_CHF']

    # 2. Grün-Fläche
    y_above = [m if m >= e else e for m, e in zip(marktwert, einsatz)]
    fig_line.add_trace(go.Scatter(
        x=h_df_filtered['Datum'], 
        y=y_above,
        fill='tonexty', 
        fillcolor='rgba(0, 255, 0, 0.5)', 
        line=dict(width=0),
        showlegend=False,
        hoverinfo='skip'
    ))

    # 3. Rot-Fläche
    y_below = [m if m <= e else e for m, e in zip(marktwert, einsatz)]
    fig_line.add_trace(go.Scatter(
        x=h_df_filtered['Datum'], y=y_below,
        fill='tonexty', 
        fillcolor='rgba(220, 38, 38, 0.3)',
        line=dict(width=0),
        showlegend=False,
        hoverinfo='skip'
    ))

    # 4. Die Performance-LINIE (Optimiert: Grüne und rote Segmente getrennt)
    # Identifiziere Bereiche über und unter der Einsatz-Linie
    is_above = marktwert >= einsatz
    
    # Erstelle separate Listen für grüne und rote Segmente
    x_green, y_green = [], []
    x_red, y_red = [], []
    
    for i in range(len(h_df_filtered)):
        datum = h_df_filtered['Datum'].iloc[i]
        wert = marktwert.iloc[i]
        
        if is_above.iloc[i]:
            x_green.append(datum)
            y_green.append(wert)
            # Trenne rote Segmente mit None
            if x_red and x_red[-1] is not None:
                x_red.append(None)
                y_red.append(None)
        else:
            x_red.append(datum)
            y_red.append(wert)
            # Trenne grüne Segmente mit None
            if x_green and x_green[-1] is not None:
                x_green.append(None)
                y_green.append(None)
    
    # Nur 2 Traces statt hunderte!
    if x_green:
        fig_line.add_trace(go.Scatter(
            x=x_green, y=y_green,
            mode='lines',
            line=dict(width=3, color="#2E7D32"),
            showlegend=False,
            hoverinfo='skip',
            connectgaps=False
        ))
    
    if x_red:
        fig_line.add_trace(go.Scatter(
            x=x_red, y=y_red,
            mode='lines',
            line=dict(width=3, color="#DC2626"),
            showlegend=False,
            hoverinfo='skip',
            connectgaps=False
        ))

    # 5. Hover-Layer
    fig_line.add_trace(go.Scatter(
        x=h_df_filtered['Datum'], y=marktwert,
        name="",
        line=dict(width=0), 
        customdata=h_df_filtered[['Gain_ABS', 'Perf_PCT']],
        hovertemplate="<b>Marktwert: %{y:,.2f} CHF</b><br>Gain: %{customdata[0]:+,.2f} CHF<br>Perf: %{customdata[1]:+.2f}%<extra></extra>"
    ))

    # Layout mit optimiertem Rangeselector
    fig_line.update_layout(
        xaxis=dict(
            gridcolor='#f0f0f0',
            type="date",
            rangebreaks=[
                dict(bounds=["sat", "mon"]),  # Wochenenden ausblenden
            ],
            rangeselector=dict(
                buttons=list([
                    # 'todate' stellt sicher, dass nur Daten ab 00:00 Uhr des heutigen Tages gezeigt werden
                    dict(count=1, label="1D", step="day", stepmode="todate"),
                    dict(count=7, label="1W", step="day", stepmode="backward"),
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                    dict(step="all", label="ALL")
                ]),
                bgcolor="#FFFFFF",
                activecolor="#CABA9C"
            )
        )
    )
    
    st.markdown("""
        <style>
        .graph-container {
            background-color: white;
            padding: 10px;
            border-radius: 12px;
            border: 1px solid #CABA9C;
        }
        </style>
        """, unsafe_allow_html=True)
    
    with st.container():
        st.plotly_chart(fig_line, use_container_width=True)

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
            if val > 0: return 'color: #2E7D32; font-weight: bold;'
            if val < 0: return 'color: #D32F2F; font-weight: bold;'
        return ''

    st.dataframe(
        df[cols].style.map(style_positive_negative, subset=[c for c in ["Stock Gain", "FX Gain", "Total Gain"] if c in cols]).format(precision=2),
        use_container_width=True, height=108
    )

    # --- SCHNELL-LINKS BEREICH ---
    st.write("##")
    st.subheader("🔗 Schnell-Links (Yahoo Finance)")
    link_cols = st.columns(len(ISIN_MAP))
    for i, (isin, ticker) in enumerate(ISIN_MAP.items()):
        url = f"https://finance.yahoo.com/quote/{ticker}"
        ticker_df = df[df['Ticker'] == ticker]
        if not ticker_df.empty:
            display_name = ticker_df['Name'].iloc[0]
            display_name = ISIN_NAME_MAP.get(display_name, display_name)
        else:
            display_name = ISIN_NAME_MAP.get(isin, ticker)
        
        with link_cols[i]:
            st.markdown(f"**{display_name}**")
            st.page_link(url, label="Yahoo", icon="📈")

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
        fig_heat.update_layout(height=200, margin=dict(t=30, b=10, l=10, r=10), template="plotly_white")
        st.plotly_chart(fig_heat, use_container_width=True)

with col_side:
    st.subheader("🥧 Diversifikation")
    val_col = 'Wert (CHF)' if pie_mode == "Marktwert" else 'Investiert (CHF)'
    pie_df = pd.concat([df[['Name', val_col]], pd.DataFrame([{"Name": "CASH", val_col: cash}])])
    
    colors = ['#102820', '#4C6444', '#CABA9C', '#8A6240']
    
    fig_pie = go.Figure(data=[go.Pie(
        labels=pie_df['Name'], 
        values=pie_df[val_col], 
        hole=.4,
        marker=dict(colors=colors)
    )])
    
    fig_pie.update_layout(
        margin=dict(t=30, b=0, l=0, r=0), 
        height=450, 
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        template="plotly_white"
    )
    st.plotly_chart(fig_pie, use_container_width=True)
