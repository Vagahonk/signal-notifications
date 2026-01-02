import os
import yfinance as yf
import pandas as pd
from ta.trend import SMAIndicator
from datetime import datetime
import asyncio
from telegram import Bot

# --- Telegram Setup ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


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


def run_bm_strategy(symbols):
    """Führt die Bond-Momentum-Strategie aus und gibt eine Nachricht und Fehler zurück."""
    if not symbols:
        return "FEHLER: Keine Symbole zum Analysieren gefunden.", []

    above_sma_count = 0
    total_symbols = len(symbols)
    errors = []

    for symbol in symbols:
        try:
            # Lade Daten. 6 Monate sind ausreichend für SMA(100) + Puffer.
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="6mo", auto_adjust=True)

            if len(data) < 100:
                errors.append(
                    f"Nicht genügend historische Daten für {symbol} (braucht 100, hat {len(data)}).")
                continue

            # Berechne SMA(100)
            last_close = data['Close'].iloc[-1]
            sma_100 = SMAIndicator(
                close=data['Close'], window=100).sma_indicator().iloc[-1]

            if pd.isna(sma_100):
                errors.append(
                    f"SMA-Berechnung für {symbol} fehlgeschlagen (NaN).")
                continue

            # Bedingung prüfen
            if last_close > sma_100:
                above_sma_count += 1

        except Exception as e:
            errors.append(f"FEHLER bei der Analyse von {symbol}: {e}")

    # Finale Auswertung
    percentage_above = (
        above_sma_count / total_symbols) * 100 if total_symbols > 0 else 0

    message_lines = []

    if above_sma_count >= 7:
        signal_line = "✅ 'LBM' Signal: BUY CWB+HYD+BAB, PT 3%"
        condition_line = "Signal-Bedingung (>= 7) erfüllt."
    else:
        signal_line = "❌ Kein 'LBM' Signal:"
        condition_line = "- Bedingung (>= 7) nicht erfüllt."

    message_lines.append(signal_line)
    message_lines.append("-" * 20)
    message_lines.append(
        f"{above_sma_count} von {total_symbols} ETFs über SMA(100) ({percentage_above:.2f}%)"
    )
    message_lines.append(condition_line)

    return "\n".join(message_lines), errors


# --- Hauptlogik ---
if __name__ == "__main__":
    today = datetime.now()
    # weekday() gibt für Freitag 4 zurück (Montag=0, ..., Sonntag=6)
    if today.weekday() != 4:
        print(
            f"Heute ist kein Freitag ({today.strftime('%A')}). Skript 'bm.py' wird nicht ausgeführt.")
    else:
        # Hardcoded list of bond ETF symbols as per previous request
        symbols = [
            "BAB", "CWB", "EMB", "HYD", "IEF", "JNK",
            "LQD", "MUB", "PCY", "PICB", "TIP", "TLT"
        ]

        message, errors = run_bm_strategy(symbols)

        # Finale Nachricht erstellen und senden
        final_message = ""
        if errors:
            error_header = "Das Skript 'bm.py' wurde mit Fehlern ausgeführt:"
            error_messages = "\n- ".join(errors)
            final_message = f"{error_header}\n- {error_messages}"
            if message:
                final_message += "\n\nZusätzliche Informationen:\n" + message
        elif message:
            final_message = message
        else:
            final_message = "Unbekannter Zustand in 'bm.py': Weder Erfolgs- noch Fehlermeldung generiert."

        print(final_message)
        asyncio.run(send_telegram_message(final_message))
