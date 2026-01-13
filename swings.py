# coding: utf-8
import warnings
import requests
from bs4 import BeautifulSoup
import re
import sys
import yfinance as yf
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from ta.momentum import RSIIndicator
from ta.trend import ADXIndicator

# Suppress pandas warnings
warnings.filterwarnings('ignore', category=pd.errors.PerformanceWarning)


def scrape_finviz_tickers(screener_url="mid_cap"):
    """
    Scrapes ticker symbols from a specific Finviz screener URL.
    This version is adapted to only use one pre-defined URL.
    """
    # URL for all-time high scan
    url = "https://finviz.com/screener.ashx?v=411&f=cap_midover,ipodate_more5,sh_avgvol_o300,sh_opt_option,ta_alltime_b0to10h&ft=4"

    # Finviz requires a User-Agent header
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        print(f"Starte Ticker-Scraping von Finviz...", file=sys.stderr)
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        tickers = []
        # The tickers are in 'a' tags with class 'screener-link-primary'
        for link in soup.find_all('a', class_='screener-link-primary'):
            tickers.append(link.get_text())

        # Fallback for pages with a different structure
        if not tickers:
            tickers_container = soup.find('td', class_='screener_tickers')
            if tickers_container:
                for span in tickers_container.find_all('span'):
                    onclick_attr = span.get('onclick')
                    if onclick_attr:
                        match = re.search(
                            r"quote\.ashx\?t=([^&]+)", onclick_attr)
                        if match:
                            tickers.append(match.group(1))

        print(
            f"Erfolgreich {len(tickers)} Ticker von Finviz gescraped.", file=sys.stderr)
        return list(set(tickers))  # Return unique tickers

    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Abrufen der Finviz-URL: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(
            f"Ein unerwarteter Fehler beim Scrapen ist aufgetreten: {e}", file=sys.stderr)
        return []


def run_analysis(tickers):
    """
    Downloads data, calculates R2, and filters for signals based on R2, ADX, and RSI.
    """
    if not tickers:
        print("Keine Ticker zum Analysieren vorhanden.", file=sys.stderr)
        return

    print(
        f"Lade historische Daten für {len(tickers)} Ticker herunter...", file=sys.stderr)
    try:
        # Download 500 days of data for all tickers at once
        all_data = yf.download(tickers, period="500d",
                               threads=True, progress=False)
        if all_data.empty:
            print(
                "Fehler: Keine Daten für die angegebenen Ticker erhalten.", file=sys.stderr)
            return
    except Exception as e:
        print(
            f"Kritischer Fehler beim Herunterladen der Daten: {e}", file=sys.stderr)
        return

    # Handle single vs. multi-ticker download format
    if len(tickers) == 1:
        all_data.columns = pd.MultiIndex.from_product(
            [all_data.columns, [tickers[0]]])

    print("Daten-Download abgeschlossen. Starte Analyse...", file=sys.stderr)
    signal_count = 0

    for i, ticker in enumerate(tickers):
        print(
            f"Analysiere {ticker} ({i+1}/{len(tickers)})...", file=sys.stderr)
        try:
            # --- R2 Calculation ---
            close_prices = all_data['Close'][ticker].dropna()
            if len(close_prices) < 100:
                continue

            best_r2 = -np.inf
            for length in range(100, len(close_prices) + 1):
                y = close_prices[-length:].values.reshape(-1, 1)
                x = np.arange(length).reshape(-1, 1)
                model = LinearRegression().fit(x, y)
                r2 = model.score(x, y)
                if r2 > best_r2:
                    best_r2 = r2

            # Normalize R2 score to be between 0 and 100
            r2_score = best_r2 * 100

            # --- Signal Condition Check (R2 > 90) ---
            if r2_score <= 90:
                continue

            # --- Indicator Calculation (ADX & RSI) ---
            stock_data = all_data.loc[:, (slice(None), ticker)]
            stock_data.columns = stock_data.columns.droplevel(1)
            stock_data = stock_data.dropna()

            if len(stock_data) < 20:  # Need enough data for ADX
                continue

            rsi_series = RSIIndicator(
                close=stock_data['Close'], window=2).rsi()
            adx_series = ADXIndicator(
                high=stock_data['High'], low=stock_data['Low'], close=stock_data['Close'], window=14).adx()

            if rsi_series.empty or adx_series.empty:
                continue

            latest_rsi = rsi_series.iloc[-1]
            latest_adx = adx_series.iloc[-1]

            if np.isnan(latest_rsi) or np.isnan(latest_adx):
                continue

            # --- Final Signal Condition Check ---
            if latest_rsi < 10 and latest_adx > 20:
                signal_count += 1
                print(f"--- SIGNAL ---")
                print(f"Ticker: {ticker}")
                print(f"  R2: {r2_score:.2f}")
                print(f"  ADX: {latest_adx:.2f}")
                print(f"  RSI(2): {latest_rsi:.2f}")
                print(f"--------------")

        except KeyError:
            # This can happen if a ticker download fails among many
            # print(f"Warnung: Unvollständige Daten für Ticker {ticker}, wird übersprungen.", file=sys.stderr)
            continue
        except Exception as e:
            print(
                f"Fehler bei der Analyse von Ticker {ticker}: {e}", file=sys.stderr)
            continue

    print(
        f"\nAnalyse abgeschlossen. {signal_count} Signale gefunden.", file=sys.stderr)


if __name__ == "__main__":
    # 1. Scrape tickers from Finviz
    tickers_to_analyze = scrape_finviz_tickers()

    # 2. Run analysis on the scraped tickers
    if tickers_to_analyze:
        run_analysis(tickers_to_analyze)
    else:
        print("Keine Ticker von Finviz erhalten. Analyse wird nicht gestartet.", file=sys.stderr)
