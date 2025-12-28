import os
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator
import asyncio
from telegram import Bot
import pandas as pd
from datetime import datetime

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


def check_tom_strategy():
    """
    Prüft die "Turn of Month" Strategie für folgende 13 ETFs: EWC,EWZ,IHI,IVE,IWS,IYF,SLYV,XLB,XLY,ENZL,EWT,IYR,GLD
    Bedingungen:
    1. Zeitraum ist zwischen 24. und 28. eines Monats.
    2. Der Monat ist NICHT September.
    3. RSI(2) < 40.
    4. Die gefilterten ETFs werden nach dem Verhältnis 'Schlusskurs / SMA(60)' absteigend sortiert.
    5. Kauf Signal für die Top 3 ETFs in der Liste."""
    errors = []
    message = ""

    today = datetime.today()

    # 1. Zeitraum ist zwischen 24. und 28. eines Monats.
    if not 24 <= today.day <= 28:
        message = f"❌ Kein Signal: Heute ist der {today.day}., nicht zwischen dem 24. und 28. des Monats."
        # No need to send a message if it's not the right time
        # asyncio.run(send_telegram_message(message))
        print(message)
        return

    # 2. Der Monat ist NICHT September.
    if today.month == 9:
        message = "❌Kein Signal: Die Strategie wird im September nicht angewendet."
        # No need to send a message if it's not the right time
        # asyncio.run(send_telegram_message(message))
        print(message)
        return

    etfs = ["EWC", "EWZ", "IHI", "IVE", "IWS", "IYF",
            "SLYV", "XLB", "XLY", "ENZL", "EWT", "IYR", "GLD"]
    qualified_etfs = []

    for ticker in etfs:
        try:
            # Fetch enough data for 60-day SMA and 2-day RSI
            data = yf.download(ticker, period="4mo", progress=False)
            if data.empty or len(data) < 61:
                errors.append(
                    f"Nicht genügend historische Daten für {ticker} gefunden.")
                continue

            # Ensure data is a 1D Series
            close_prices = data["Close"].squeeze()

            # 3. RSI(2) < 40.
            rsi_indicator = RSIIndicator(close=close_prices, window=2)
            rsi_value = rsi_indicator.rsi().iloc[-1]

            if pd.isna(rsi_value):
                errors.append(
                    f"RSI-Berechnung für {ticker} fehlgeschlagen (NaN).")
                continue

            if rsi_value < 40:
                # 4. Verhältnis 'Schlusskurs / SMA(60)'
                sma_indicator = SMAIndicator(close=close_prices, window=60)
                sma_value = sma_indicator.sma_indicator().iloc[-1]
                last_close = close_prices.iloc[-1]

                if pd.isna(sma_value) or sma_value <= 0:
                    errors.append(
                        f"SMA-Berechnung für {ticker} fehlgeschlagen (NaN oder <=0).")
                    continue

                ratio = last_close / sma_value
                qualified_etfs.append(
                    {"ticker": ticker, "ratio": ratio, "rsi": rsi_value})

        except Exception as e:
            errors.append(f"FEHLER bei der Verarbeitung von {ticker}: {e}")

    if not qualified_etfs:
        message = "❌Kein ETF erfüllt die RSI < 40 Bedingung."
    else:
        # 4. absteigend sortiert.
        qualified_etfs.sort(key=lambda x: x["ratio"], reverse=True)

        # 5. Kauf Signal für die Top 3 ETFs
        top_3_etfs = qualified_etfs[:3]

        if top_3_etfs:
            message_lines = ["✅ Turn of the Month Signale:"]
            for etf in top_3_etfs:
                message_lines.append(
                    f"  - Kaufsignal für {etf['ticker']} (Ratio: {etf['ratio']:.2f}, RSI: {etf['rsi']:.2f})")
            message = "\n".join(message_lines)
        else:
            # This case should not be reached if qualified_etfs is not empty
            message = "❌Kein Turn of the Month Signal."

    # Finale Nachricht erstellen und senden
    final_message = ""
    if errors:
        error_header = "Das Skript 'tom.py' wurde mit Fehlern ausgeführt:"
        error_messages = "\n- ".join(errors)
        final_message = f"{error_header}\n- {error_messages}"
        if message:
            # Add results even if some errors occurred
            final_message += "\n\nZusätzliche Informationen:\n" + message
    elif message:
        final_message = message
    else:
        # This state should ideally not be reached
        final_message = "Unbekannter Zustand in 'tom.py': Weder Erfolgs- noch Fehlermeldung generiert."

    print(final_message)
    asyncio.run(send_telegram_message(final_message))


if __name__ == "__main__":
    check_tom_strategy()
