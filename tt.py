import os
import yfinance as yf
from ta.momentum import RSIIndicator
from datetime import datetime, timedelta
import asyncio
from telegram import Bot

# --- Configuration ---
# TOKEN = "8206293301:AAF6bg9TfesbodsfpFC6Z4Ce5sOhLCgyBPU"
# CHAT_ID = "1460988872"
# IMPORTANT: Your credentials should be set as environment variables for security.
# On Windows (Command Prompt):
# set TELEGRAM_BOT_TOKEN=your_token_here
# set TELEGRAM_CHAT_ID=your_chat_id_here
#
# On Windows (PowerShell):
# $env:TELEGRAM_BOT_TOKEN="your_token_here"
# $env:TELEGRAM_CHAT_ID="your_chat_id_here"
#
# On Linux/macOS:
# export TELEGRAM_BOT_TOKEN='your_token_here'
# export TELEGRAM_CHAT_ID='your_chat_id_here'

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_telegram_message(text):
    """Sends a message via Telegram if the library is enabled and configured."""
    if not TELEGRAM_ENABLED:
        print("Telegram notifications are disabled. Skipping.")
        return
    if not TOKEN or not CHAT_ID:
        print("Telegram TOKEN or CHAT_ID not set in environment variables. Skipping notification.")
        return

    try:
        bot = Bot(token=TOKEN)
        bot.send_message(chat_id=CHAT_ID, text=text)
        print("Telegram notification sent successfully.")
    except Exception as e:
        print(f"Failed to send Telegram notification: {e}")


def check_spy_monday_strategy():
    """
    Prüft die "Turnaround Tuesday" Strategie für SPY.
    Bedingungen:
    1. Montags Schlusskurs < Freitags Schlusskurs
    2. RSI(2) < 35
    """

    spy = yf.Ticker("SPY")
    hist = spy.history(period="10d")

    try:
        today_close = hist['Close'].iloc[0]
        last_close = hist['Close'].iloc[-1]
    except IndexError:
        print("Nicht genügend historische Daten vorhanden, um die Strategie zu prüfen.")
        return

    if len(hist['Close']) < 3:
        print("Nicht genügend Daten für die RSI-Berechnung (benötigt 3 Tage).")
        return

    rsi_indicator = RSIIndicator(close=hist["Close"], window=2)
    rsi_value = rsi_indicator.rsi().iloc[-1]

    print(f"Letzter Schlusskurs: {today_close:.2f}")
    print(f"Vorheriger Schlusskurs: {last_close:.2f}")
    print(f"RSI(2): {rsi_value:.2f}")

    condition1 = today_close < last_close
    condition2 = rsi_value < 35

    if condition1 and condition2:
        message = (
            "Turnaround Tuesday Signal erkannt!\n"
            f"- Montags Schlusskurs ({today_close:.2f}) < Freitags Schlusskurs ({last_close:.2f})\n"
            f"- RSI(2) ({rsi_value:.2f}) < 35"
        )
        print(message)
        # Telegram Nachricht senden
        asyncio.run(send_telegram_message(message))
    else:
        print("\nKein Turnaround Tuesday Signal erkannt.")
        if not condition1:
            print(
                f"- Montags Schlusskurs ({today_close:.2f}) ist nicht niedriger als Freitags Schlusskurs ({last_close:.2f}).")
        if not condition2:
            print(f"- RSI(2) ({rsi_value:.2f}) ist nicht unter 35.")


if __name__ == "__main__":
    check_spy_monday_strategy()
