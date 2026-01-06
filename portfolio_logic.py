import pandas as pd
import json
import yfinance as yf
from datetime import datetime
import os
import streamlit as st


# Konfiguration
ISIN_MAP = {
    "IE00B4L5Y983": "SWDA.SW",
    "IE00B4L5YC18": "SEMA.SW"
}


PORTFOLIO_FILE = 'portfolio.json'


@st.cache_data(ttl=600) # Speichert die Daten für 10 Minuten im RAM
def calculate_portfolio_data():
    if not os.path.exists(PORTFOLIO_FILE):
        raise Exception(f"Die Datei '{PORTFOLIO_FILE}' wurde nicht gefunden.")


    with open(PORTFOLIO_FILE, 'r') as f:
        data = json.load(f)


    transactions = data.get('transactions', [])
    cash_chf = data.get('cash', 0)
   
    # Aktuelle Preise abrufen
    prices = {}
    for isin, ticker in ISIN_MAP.items():
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1d")
            prices[isin.upper()] = hist['Close'].iloc[-1] if not hist.empty else 0
        except:
            prices[isin.upper()] = 0
   
    # Aktuellen Wechselkurs abrufen
    try:
        fx_rate = yf.Ticker("USDCHF=X").history(period="1d")['Close'].iloc[-1]
    except:
        fx_rate = 1.0


    results = []
    total_stock_val = 0
    total_invested = 0
    total_fees = 0


    for t in transactions:
        t_isin = t['isin'].strip().upper()
        price_now = prices.get(t_isin, 0)
       
        val_buy = t['quantity'] * t['price'] * t['currency_rate']
        mult = fx_rate if t['currency_rate'] != 1.0 else 1.0
        val_now = t['quantity'] * price_now * mult
       
        t_fees = t.get('fees', 0)
        total_gain = val_now - val_buy - t_fees
        stock_gain = (price_now - t['price']) * t['quantity'] * t['currency_rate']
        fx_gain = total_gain - stock_gain


        total_stock_val += val_now
        total_invested += val_buy
        total_fees += t_fees
       
        results.append({
            "Name": t_isin,
            "Ticker": ISIN_MAP.get(t_isin, "N/A"),
            "Menge": t['quantity'],
            "Wert (CHF)": round(val_now, 2),
            "Investiert (CHF)": round(val_buy, 2),
            "Stock Gain": round(stock_gain, 2),
            "FX Gain": round(fx_gain, 2),
            "Total Gain": round(total_gain, 2),
            "Gebühren": t_fees
        })


    net_worth = (total_stock_val + cash_chf)


    return {
        "df": pd.DataFrame(results),
        "total_stock_val": total_stock_val,
        "total_invested": total_invested,
        "cash": cash_chf,
        "total_val_with_fees": net_worth,
        "fx_rate": fx_rate,
        "total_fees": total_fees
    }


@st.cache_data(ttl=600)
def get_historical_performance():
    if not os.path.exists(PORTFOLIO_FILE):
        return pd.DataFrame()
    with open(PORTFOLIO_FILE, 'r') as f:
        data = json.load(f)
    transactions = data.get('transactions', [])
   
    if not transactions:
        return pd.DataFrame()
    
    # WICHTIG: Finde das ERSTE Kaufdatum aus den Transaktionen
    first_transaction_date = min(pd.to_datetime(t['datetime']) for t in transactions)
    start_str = first_transaction_date.strftime("%Y-%m-%d")
    start_date = first_transaction_date
    
    tickers = list(ISIN_MAP.values())
   
    # --- DYNAMISCHES INTERVALL LOGIK ---
    days_diff = (datetime.now() - start_date).days
   
    # Nutze 15m für Details wenn < 60 Tage, sonst 1h Fallback
    chosen_interval = "15m" if days_diff < 60 else "1h"
   
    try:
        raw_data = yf.download(
            tickers + ["USDCHF=X"],
            start=start_str,
            interval=chosen_interval
        )['Close']
    except:
        raw_data = yf.download(tickers + ["USDCHF=X"], start=start_str, interval="1h")['Close']
       
    raw_data = raw_data.ffill()
   
    history_list = []
    for timestamp in raw_data.index:
        current_day_val = 0
        current_day_invested = 0
        compare_ts = timestamp.tz_localize(None) if timestamp.tzinfo else timestamp
        
        # NEU: Überspringe alle Zeitpunkte VOR dem ersten Kauf
        if compare_ts < first_transaction_date:
            continue
       
        for t in transactions:
            t_date = pd.to_datetime(t['datetime'])
            if t_date <= compare_ts:
                ticker = ISIN_MAP.get(t['isin'].strip().upper())
                current_day_invested += (t['quantity'] * t['price'] * t['currency_rate'])
               
                if ticker in raw_data.columns:
                    p = raw_data.loc[timestamp, ticker]
                    f = raw_data.loc[timestamp, "USDCHF=X"] if t['currency_rate'] != 1.0 else 1.0
                   
                    if pd.notna(p) and pd.notna(f):
                        current_day_val += (t['quantity'] * p * f)
       
        if current_day_val > 0:
            history_list.append({
                "Datum": timestamp,
                "Marktwert_CHF": current_day_val,
                "Einsatz_CHF": current_day_invested
            })
           
    return pd.DataFrame(history_list)