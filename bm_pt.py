import os
import re
import yfinance as yf
import pandas as pd
from ta.trend import SMAIndicator
from datetime import datetime
import asyncio
from telegram import Bot

# --- Telegram Setup ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Hardcoded list of bond ETF symbols as per bm.py
BM_SYMBOLS = [
    "BAB", "CWB", "EMB", "HYD", "IEF", "JNK",
    "LQD", "MUB", "PCY", "PICB", "TIP", "TLT"
]


def run_bm_strategy(symbols):
    """Führt die Bond-Momentum-Strategie aus und gibt die Strategieergebnisse zurück."""
    if not symbols:
        return False, 0, 0, ["FEHLER: Keine Symbole zum Analysieren gefunden."]

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

    is_buy_signal = (above_sma_count >= 7)
    return is_buy_signal, above_sma_count, total_symbols, errors


async def send_telegram_message(text):
    """Sends a message to a Telegram chat."""
    if not TOKEN or not CHAT_ID:
        print("Telegram environment variables (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID) not set. Skipping notification.")
        return
    try:
        bot = Bot(token=TOKEN)
        # Use Markdown for bold text
        await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode='Markdown')
        print("Telegram notification sent successfully.")
    except Exception as e:
        print(f"Failed to send Telegram notification: {e}")


def get_closing_price_and_pt(symbol, pt_percentage=0.03):
    """Fetches the latest closing price and calculates the profit target."""
    try:
        ticker = yf.Ticker(symbol)
        # Fetch data for a slightly longer period to ensure we get a close price,
        # sometimes "1d" can return empty if there's no trading on the current day or API issues.
        data = ticker.history(period="5d", auto_adjust=True)

        if not data.empty:
            last_close = data['Close'].iloc[-1]
            profit_target = last_close * (1 + pt_percentage)
            return last_close, profit_target
        else:
            print(f"No data found for {symbol}")
            return None, None
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None, None


async def main():
    # Run the Bond Momentum strategy
    is_buy_signal, above_sma_count, total_symbols, bm_strategy_errors = run_bm_strategy(
        BM_SYMBOLS)

    telegram_output_lines = []

    if bm_strategy_errors:
        error_header = "Das Skript 'bm_pt.py' hat Fehler in der Strategieausführung:"
        error_messages = "\n- ".join(bm_strategy_errors)
        telegram_output_lines.append(f"{error_header}\n- {error_messages}")

    if is_buy_signal:
        # As per bm.py's logic, if a buy signal is generated, these are the target symbols
        target_symbols_for_pt = ["CWB", "HYD", "BAB"]

        telegram_output_lines.append("📈 **'LBM' Profit Target Calculation** 📈")

        telegram_output_lines.append("")

        for symbol in target_symbols_for_pt:
            close_price, pt_price = get_closing_price_and_pt(symbol)
            if close_price is not None and pt_price is not None:
                telegram_output_lines.append(
                    f"**{symbol}**: Last Close: {close_price:.2f}, PT (+3%): {pt_price:.2f}")
            else:
                telegram_output_lines.append(
                    f"**{symbol}**: Konnte keine Daten abrufen oder PT berechnen.")
    else:
        telegram_output_lines.append("❌ Kein 'LBM' Kaufsignal gefunden.")
        telegram_output_lines.append(
            f"(Bedingung: {above_sma_count} von {total_symbols} ETFs über SMA(100) nicht erfüllt.)")

    final_telegram_message = "\n".join(telegram_output_lines)
    print("\n--- Telegram Message Content ---")
    print(final_telegram_message)
    print("----------------------------\n")
    await send_telegram_message(final_telegram_message)

if __name__ == "__main__":
    # Optional: Add a check for Friday, similar to bm.py, if bm_pt.py should also only run on Fridays.
    # For now, it will run whenever executed.
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())
