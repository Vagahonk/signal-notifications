import os
import yfinance as yf
from ta.momentum import RSIIndicator
from datetime import datetime


def check_spy_monday_strategy():
    """
    Prüft die "Turnaround Tuesday" Strategie für SPY.
    Bedingungen:
    1. Montags Schlusskurs < Freitags Schlusskurs
    2. RSI(2) < 35
    """

# Prüfe ob Montag ist

# Lade die historischen Daten für SPY. 10 Tage.

# Hol die letzten beiden Schlusskurse

# Prüfe die Bedingungen

# Falls beide Bedingungen erfüllt sind, print "Turnaround Tuesday Signal erkannt!"
