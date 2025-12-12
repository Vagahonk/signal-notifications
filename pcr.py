import io
import os
from datetime import datetime
import requests
import yfinance as yf
import pandas as pd
from ta.momentum import ROCIndicator
import asyncio
from telegram import Bot

# --- Telegram Setup ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PCR_URL = "http://styxgate.info/data/PCR_Index.TXT"


async def send_telegram_message(text):
    """Sends a message to a Telegram chat."""
    if not TOKEN or not CHAT_ID:
        print("Telegram environment variables (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID) not set. Skipping notification.")
        return
    try:
        bot = Bot(token=TOKEN)
        await bot.send_message(chat_id=CHAT_ID, text=text)
        print("Telegram notification sent successfully.")
    except Exception as e:
        print(f"Failed to send Telegram notification: {e}")


def perform_strategy_check():
    """
    Führt die Hauptstrategieprüfung durch, sammelt alle Fehler oder eine Erfolgsnachricht
    und sendet am Ende eine einzige, zusammenfassende Benachrichtigung an Telegram.
    """
    errors = []
    message_lines = []
    percentage_diff = None
    last_pcr_value = None
    last_pcr_date = None
    prev_pcr_value = None
    prev_pcr_date = None
    last_roc = None

    # Schritt 1: PCR-Analyse durchführen
    try:
        response = requests.get(PCR_URL)
        response.raise_for_status()
        pcr_content = response.text
        pcr_df = pd.read_csv(io.StringIO(pcr_content), sep='\t', header=None, names=[
                             'Date', 'Value'], decimal=',')
        pcr_df['Date'] = pcr_df['Date'].astype(str)

        if len(pcr_df) < 200:
            errors.append(
                f"Nicht genügend Daten von der URL für SMA(200). Benötigt: 200, Vorhanden: {len(pcr_df)}.")
        else:
            pcr_df['SMA2'] = pcr_df['Value'].rolling(window=2).mean()
            pcr_df['SMA200'] = pcr_df['Value'].rolling(window=200).mean()
            last_sma2 = pcr_df['SMA2'].iloc[-1]
            last_sma200 = pcr_df['SMA200'].iloc[-1]

            if last_sma200 == 0:
                errors.append(
                    "SMA200 ist Null, eine Division ist nicht möglich.")
            else:
                ratio = last_sma2 / last_sma200
                percentage_diff = (ratio - 1) * 100

                last_pcr_value = pcr_df['Value'].iloc[-1]
                last_pcr_date_str = pcr_df['Date'].iloc[-1]
                last_pcr_date = datetime.strptime(
                    last_pcr_date_str, '%Y%m%d').strftime('%d.%m.%Y')

                prev_pcr_value = pcr_df['Value'].iloc[-2]
                prev_pcr_date_str = pcr_df['Date'].iloc[-2]
                prev_pcr_date = datetime.strptime(
                    prev_pcr_date_str, '%Y%m%d').strftime('%d.%m.%Y')

    except requests.exceptions.RequestException as e:
        errors.append(f"FEHLER beim Abrufen der PCR-Daten von der URL: {e}")
    except Exception as e:
        errors.append(f"FEHLER bei der PCR-Analyse: {e}")

    # Schritt 2: QQQ Momentum prüfen
    try:
        qqq = yf.Ticker("QQQ")
        hist = qqq.history(period="6mo", auto_adjust=True)
        if hist.empty:
            errors.append(
                "Keine historischen Daten für QQQ von yfinance gefunden.")
        else:
            roc_60 = ROCIndicator(close=hist['Close'], window=60).roc()
            last_roc = roc_60.iloc[-1]

    except Exception as e:
        errors.append(f"FEHLER bei der QQQ-Momentum-Prüfung (yfinance): {e}")

    # Schritt 3: Finale Nachricht basierend auf Erfolg oder Fehlern erstellen
    final_message = ""
    if errors:
        # Fehlermodus: Alle gesammelten Fehler auflisten
        error_header = "Das Skript wurde mit Fehlern ausgeführt:"
        error_messages = "\n- ".join(errors)
        final_message = f"{error_header}\n- {error_messages}"
    elif percentage_diff is not None and last_roc is not None:
        # Erfolgsmodus: Signale generieren
        if percentage_diff < -4:
            message_lines.append("❌ Signal: CLOSE LONG POSITION ON OPEN")
        elif percentage_diff > 7 and last_roc > 0:
            message_lines.append("✅ Signal: BUY LONG POSITION ON OPEN")
        else:
            message_lines.append("❌ Signal: HOLD / FLAT")

        message_lines.append("-" * 20)
        message_lines.append(
            f"Last PCR: {last_pcr_value} ({last_pcr_date}); {prev_pcr_value} ({prev_pcr_date})")
        message_lines.append(f"QQQ ROC(60) = {last_roc:.2f}%")
        message_lines.append(f"PCR Value: {percentage_diff:+.2f}%")

        final_message = "\n".join(message_lines)
    else:
        # Dieser Fall sollte nicht eintreten, wenn die Logik korrekt ist
        final_message = "Unbekannter Zustand: Weder Erfolgsdaten noch Fehler wurden aufgezeichnet. Das Skript wurde ausgeführt."

    # Schritt 4: Finale Nachricht senden
    print(final_message)
    asyncio.run(send_telegram_message(final_message))


# --- Hauptlogik ---
if __name__ == "__main__":
    perform_strategy_check()
