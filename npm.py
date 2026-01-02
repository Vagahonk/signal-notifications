import os
import yfinance as yf
import asyncio
from telegram import Bot

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


def check_qqq_vix_strategy():
    """
    Prüft die "No Panic Model" Strategie für QQQ, sammelt Fehler und sendet
    eine einzelne, zusammenfassende Benachrichtigung.
    Bedingungen: VIX > 30$
    """
    errors = []
    message = ""

    try:
        vix = yf.Ticker("^VIX")
        hist = vix.history(period="10d")

        if hist.empty:
            errors.append(
                "Keine historischen Daten für ^VIX von yfinance gefunden.")
        else:
            last_vix_close = hist['Close'].iloc[-1]
            condition = last_vix_close > 30

            if condition:
                message = (
                    f"✅ 'LNPM' Signal: BUY QQQ ON CLOSE, PT 6%\n"
                    f"- VIX ({last_vix_close:.2f}) > 30\n"
                    f"Time Stop +9days"
                )
            else:
                message = (
                    f"❌ Kein 'LNPM' Signal:\n"
                    f"- VIX ({last_vix_close:.2f}) nicht über 30"
                )

    except Exception as e:
        errors.append(
            f"FEHLER bei der 'No Panic Model' Strategieprüfung (yfinance): {e}")

    # Finale Nachricht erstellen und senden
    final_message = ""
    if errors:
        error_header = "Das Skript 'npm.py' wurde mit Fehlern ausgeführt:"
        error_messages = "\n- ".join(errors)
        final_message = f"{error_header}\n- {error_messages}"
    elif message:
        final_message = message
    else:
        final_message = "Unbekannter Zustand in 'npm.py': Weder Erfolgs- noch Fehlermeldung generiert."

    print(final_message)
    asyncio.run(send_telegram_message(final_message))


if __name__ == "__main__":
    check_qqq_vix_strategy()
