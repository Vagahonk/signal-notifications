import os
import yfinance as yf
from ta.momentum import RSIIndicator
from datetime import datetime, timedelta
import asyncio
from telegram import Bot

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


async def send_telegram_message(text):
    try:
        bot = Bot(token=TOKEN)
        await bot.send_message(chat_id=CHAT_ID, text=text)
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

    # Ensure there's enough data for comparison and RSI calculation
    if len(hist) < 3:
        message = "Kein Signal: Nicht genügend historische Daten für die Strategieprüfung."
        print(message)
        asyncio.run(send_telegram_message(message))
        return

    last_day = hist.index[-1]
    # The strategy requires comparing Monday's close with the previous Friday's close.
    # We check if the last available data point is from a Monday.
    if last_day.weekday() != 0:  # 0 is Monday
        message = f"Kein Signal: Letzter Handelstag war ein {last_day.strftime('%A')}, kein Montag."
        print(message)
        asyncio.run(send_telegram_message(message))
        return

    monday_close = hist['Close'].iloc[-1]
    # Previous trading day in the history
    friday_close = hist['Close'].iloc[-2]
    friday_date = hist.index[-2]

    rsi_indicator = RSIIndicator(close=hist["Close"], window=2)
    rsi_value = rsi_indicator.rsi().iloc[-1]

    print(f"Montag Schlusskurs ({last_day.date()}): {monday_close:.2f}")
    print(f"Freitag Schlusskurs ({friday_date.date()}): {friday_close:.2f}")
    print(f"RSI(2): {rsi_value:.2f}")

    condition1 = monday_close < friday_close
    condition2 = rsi_value < 35

    if condition1 and condition2:
        message = (
            "✅ Turnaround Tuesday Signal erkannt!\n"
            f"- Montags Schlusskurs ({monday_close:.2f}) < Freitags Schlusskurs ({friday_close:.2f})\n"
            f"- RSI(2) ({rsi_value:.2f}) < 35"
        )
    else:
        # Build a detailed "no signal" message
        reasons = []
        if not condition1:
            reasons.append(
                f"Montagsschluss ({monday_close:.2f}) nicht niedriger als Freitagsschluss ({friday_close:.2f})")
        if not condition2:
            reasons.append(f"RSI(2) ({rsi_value:.2f}) nicht unter 35")
        message = "❌ Kein Turnaround Tuesday Signal:\n- " + \
            "\n- ".join(reasons)

    print(message)
    # Call the async function using asyncio.run
    asyncio.run(send_telegram_message(message))


if __name__ == "__main__":
    check_spy_monday_strategy()
