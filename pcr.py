import io
from datetime import datetime
import requests
import yfinance as yf
import pandas as pd
from ta.momentum import ROCIndicator

PCR_URL = "http://styxgate.info/data/PCR_Index.TXT"


def perform_strategy_check():
    """
    Führt die Hauptstrategieprüfung durch:
    1. PCR-Daten von URL laden und Indikatoren berechnen.
    2. QQQ-Momentum prüfen.
    3. Signale basierend auf den kombinierten Bedingungen generieren.
    """
    percentage_diff = None
    last_pcr_value = None
    last_pcr_date = None
    prev_pcr_value = None
    prev_pcr_date = None

    # Schritt 1: PCR-Analyse durchführen
    try:
        # Lese PCR-Daten von der URL
        response = requests.get(PCR_URL)
        response.raise_for_status()  # Stellt sicher, dass der Request erfolgreich war
        pcr_content = response.text

        # Lese PCR.txt und konvertiere sie in einen Pandas DataFrame
        pcr_df = pd.read_csv(io.StringIO(pcr_content), sep='	', header=None, names=[
                             'Date', 'Value'], decimal=',')

        # Konvertiere 'Date' Spalte in String für die Verarbeitung
        pcr_df['Date'] = pcr_df['Date'].astype(str)

        if len(pcr_df) < 200:
            print(
                f"Nicht genügend Daten von der URL für SMA(200). Benötigt: 200, Vorhanden: {len(pcr_df)}. Strategie wird nicht ausgeführt.")
            return

        # Berechne SMAs
        pcr_df['SMA2'] = pcr_df['Value'].rolling(window=2).mean()
        pcr_df['SMA200'] = pcr_df['Value'].rolling(window=200).mean()

        last_sma2 = pcr_df['SMA2'].iloc[-1]
        last_sma200 = pcr_df['SMA200'].iloc[-1]

        # Vermeide Division durch Null
        if last_sma200 == 0:
            print("FEHLER: SMA200 ist Null, eine Division ist nicht möglich.")
            return

        ratio = last_sma2 / last_sma200
        percentage_diff = (ratio - 1) * 100

        # Hole die letzten beiden PCR-Werte und Daten für die Ausgabe
        last_pcr_value = pcr_df['Value'].iloc[-1]
        last_pcr_date_str = pcr_df['Date'].iloc[-1]
        last_pcr_date = datetime.strptime(
            last_pcr_date_str, '%Y%m%d').strftime('%d.%m.%Y')

        prev_pcr_value = pcr_df['Value'].iloc[-2]
        prev_pcr_date_str = pcr_df['Date'].iloc[-2]
        prev_pcr_date = datetime.strptime(
            prev_pcr_date_str, '%Y%m%d').strftime('%d.%m.%Y')

    except requests.exceptions.RequestException as e:
        print(f"FEHLER beim Abrufen der PCR-Daten von der URL: {e}")
        return
    except Exception as e:
        print(f"FEHLER bei der PCR-Analyse: {e}")
        return

    # Schritt 2: QQQ Momentum prüfen
    last_roc = None
    try:
        qqq = yf.Ticker("QQQ")
        hist = qqq.history(period="6mo", auto_adjust=True)
        if hist.empty:
            print("FEHLER: Keine historischen Daten für QQQ gefunden.")
            return

        roc_60 = ROCIndicator(close=hist['Close'], window=60).roc()
        last_roc = roc_60.iloc[-1]

    except Exception as e:
        print(f"FEHLER bei der QQQ-Momentum-Prüfung: {e}")
        return

    # --- Ausgabe der gesammelten Daten ---
    if percentage_diff is not None and last_roc is not None:
        print(f"PCR Signal: {percentage_diff:+.2f}%")
        print(
            f"Last PCR: {last_pcr_value} ({last_pcr_date}); {prev_pcr_value} ({prev_pcr_date})")
        print(f"QQQ ROC(60) = {last_roc:.2f}%")
    else:
        print("Konnte nicht alle notwendigen Daten für eine Entscheidung sammeln.")
        return

    # Schritt 3: Signale basierend auf den kombinierten Bedingungen generieren
    if percentage_diff > 7 and last_roc > 0:
        print("-" * 20)
        print("Signal: BUY ON OPEN")
    elif percentage_diff < -4:
        print("-" * 20)
        print("Signal: SELL ON OPEN")
    else:
        print("-" * 20)
        print("Signal: HOLD / FLAT")


# --- Hauptlogik ---
if __name__ == "__main__":
    perform_strategy_check()
