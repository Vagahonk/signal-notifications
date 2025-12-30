import os
import yfinance as yf
from ta.momentum import RSIIndicator
import asyncio
from telegram import Bot

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
"""ID Guppe: -5203280402"""


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


def check_spy_monday_strategy():
    """
    Prüft die "Turnaround Tuesday" Strategie für SPY, sammelt Fehler und sendet
    eine einzelne, zusammenfassende Benachrichtigung.
    Bedingungen:
    1. Montags Schlusskurs < Freitags Schlusskurs
    2. RSI(2) < 35
    """
    errors = []
    message = ""

    try:
        spy = yf.Ticker("SPY")
        hist = spy.history(period="10d")

        if hist.empty or len(hist) < 3:
            errors.append(
                "Nicht genügend historische Daten für SPY von yfinance gefunden.")
        else:
            last_day = hist.index[-1]
            if last_day.weekday() != 0:  # 0 ist Montag
                message = f"Kein Signal: Letzter Handelstag war ein {last_day.strftime('%A')}, kein Montag."
            else:
                monday_close = hist['Close'].iloc[-1]
                friday_close = hist['Close'].iloc[-2]
                friday_date = hist.index[-2]

                rsi_indicator = RSIIndicator(close=hist["Close"], window=2)
                rsi_value = rsi_indicator.rsi().iloc[-1]

                print(
                    f"Montag Schlusskurs ({last_day.date()}): {monday_close:.2f}")
                print(
                    f"Freitag Schlusskurs ({friday_date.date()}): {friday_close:.2f}")
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
                    reasons = []
                    if not condition1:
                        reasons.append(
                            f"Montagsschluss ({monday_close:.2f}) nicht niedriger als Freitagsschluss ({friday_close:.2f})")
                    if not condition2:
                        reasons.append(
                            f"RSI(2) ({rsi_value:.2f}) nicht unter 35")
                    message = "❌ Kein Turnaround Tuesday Signal:\n- " + \
                        "\n- ".join(reasons)

    except Exception as e:
        errors.append(f"FEHLER bei der Strategieprüfung (yfinance): {e}")

    # Finale Nachricht erstellen und senden
    final_message = ""
    if errors:
        error_header = "Das Skript 'tt.py' wurde mit Fehlern ausgeführt:"
        error_messages = "\n- ".join(errors)
        final_message = f"{error_header}\n- {error_messages}"
    elif message:
        final_message = message
    else:
        final_message = "Unbekannter Zustand in 'tt.py': Weder Erfolgs- noch Fehlermeldung generiert."

    print(final_message)
    asyncio.run(send_telegram_message(final_message))


if __name__ == "__main__":
    check_spy_monday_strategy()
