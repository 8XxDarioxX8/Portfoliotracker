import yfinance as yf
import pandas as pd
from datetime import datetime

# Deine ETFs
ETFS = {
    "IE00B4L5Y983": "SWDA.SW",
    "IE00B4L5YC18": "SEMA.SW"
}

def check_live_market():
    print(f"--- Markt-Check vom {datetime.now().strftime('%d.%m.%Y %H:%M:%S')} ---")
    
    # 1. Wechselkurs holen
    usd_chf = yf.Ticker("USDCHF=X").history(period="1d")['Close'].iloc[-1]
    print(f"Aktueller Wechselkurs: 1 USD = {usd_chf:.4f} CHF\n")
    
    print(f"{'ISIN':<15} | {'Ticker':<10} | {'Preis (Original)':<18} | {'Preis (in CHF)':<15}")
    print("-" * 65)

    for isin, ticker in ETFS.items():
        try:
            stock = yf.Ticker(ticker)
            # Wir holen den aktuellsten Preis
            data = stock.history(period="1d")
            if not data.empty:
                current_price = data['Close'].iloc[-1]
                # Da die Ticker auf .SW enden, liefert Yahoo sie meist schon in CHF.
                # Falls du US-Ticker hättest, müsste man hier * usd_chf rechnen.
                # Wir zeigen beides an, um sicher zu gehen:
                price_chf = current_price # SWDA.SW ist bereits CHF
                
                print(f"{isin:<15} | {ticker:<10} | {current_price:>8.2f}          | {price_chf:>8.2f} CHF")
            else:
                print(f"{isin:<15} | {ticker:<10} | Keine Daten gefunden.")
        except Exception as e:
            print(f"{isin:<15} | {ticker:<10} | Fehler: {e}")

if __name__ == "__main__":
    check_live_market()