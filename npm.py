import os
import yfinance as yf
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


def check_qqq_vix_strategy():
    """
    Prüft die "No Panic Model" Strategie für QQQ.
    Bedingungen:
    VIX > 30$
    """

    vix = yf.Ticker("^VIX")
    hist = vix.history(period="10d")
    last_vix_close = hist['Close'].iloc[-1]

    condition = last_vix_close > 30

    if condition:
        message = (
            f"✅ NPM Signal erkannt!\n"
            f"- VIX ({last_vix_close:.2f}) > 30"
        )
    else:
        message = (
            f"❌ Kein 'No Panic Model' Signal:\n"
            f"- VIX ({last_vix_close:.2f}) nicht über 30"
        )

    print(message)
    # Call the async function using asyncio.run
    asyncio.run(send_telegram_message(message))


if __name__ == "__main__":
    check_qqq_vix_strategy()
