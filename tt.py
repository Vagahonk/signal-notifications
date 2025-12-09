import os
import yfinance as yf
from ta.momentum import RSIIndicator
from datetime import datetime, timedelta


def check_spy_monday_strategy():
    """
    Prüft die "Turnaround Tuesday" Strategie für SPY.
    Bedingungen:
    1. Montags Schlusskurs < Freitags Schlusskurs
    2. RSI(2) < 35
    """

    # Prüfe ob Montag ist (Wochentag 0)
    if datetime.today().weekday() != 1:
        print("Heute ist nicht Montag. Die Strategie wird nur Montags ausgeführt.")
        return

    # Lade die historischen Daten für SPY. 10 Tage
    spy = yf.Ticker("SPY")
    hist = spy.history(period="10d")

    # Hol die letzten beiden Schlusskurse (Montag und Freitag)
    try:
        monday_close = hist['Close'][0]
        friday_close = hist['Close'][-1]
    except IndexError:
        print("Nicht genügend historische Daten vorhanden, um die Strategie zu prüfen.")
        return

    # Berechne den RSI(2)
    if len(hist['Close']) < 3:
        print("Nicht genügend Daten für die RSI-Berechnung (benötigt 3 Tage).")
        return

    rsi_indicator = RSIIndicator(close=hist["Close"], window=2)
    rsi_value = rsi_indicator.rsi().iloc[-1]

    print(f"Letzter Schlusskurs (Montag): {monday_close:.2f}")
    print(f"Vorheriger Schlusskurs (Freitag): {friday_close:.2f}")
    print(f"RSI(2): {rsi_value:.2f}")

    # Prüfe die Bedingungen
    condition1 = monday_close < friday_close
    condition2 = rsi_value < 35

    # Falls beide Bedingungen erfüllt sind, print "Turnaround Tuesday Signal erkannt!"
    if condition1 and condition2:
        print("\nTurnaround Tuesday Signal erkannt!")
        print("Bedingungen erfüllt:")
        print(
            f"1. Montags Schlusskurs ({monday_close:.2f}) < Freitags Schlusskurs ({friday_close:.2f})")
        print(f"2. RSI(2) ({rsi_value:.2f}) < 35")
    else:
        print("\nKein Turnaround Tuesday Signal erkannt.")
        if not condition1:
            print(
                f"- Montags Schlusskurs ({monday_close:.2f}) ist nicht niedriger als Freitags Schlusskurs ({friday_close:.2f}).")
        if not condition2:
            print(f"- RSI(2) ({rsi_value:.2f}) ist nicht unter 35.")


if __name__ == "__main__":
    check_spy_monday_strategy()
