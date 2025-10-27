import yfinance as yf
import pandas as pd
from ta.momentum import ROCIndicator, RSIIndicator
from ta.trend import ADXIndicator
import threading
from flask import Flask, render_template_string, request, redirect, url_for

# ----------------------------------------------------------------------
# 1. Konfiguration
# ----------------------------------------------------------------------
tickers_by_list = {
    "NASDAQ100": [
        "AAPL","ABNB","ADBE","ADI","ADP","ADSK","AEP","AMAT","AMD","AMGN",
        "AMZN","APP","ARM","ASML","AVGO","AXON","AZN","BIIB","BKNG","BKR",
        "CCEP","CDNS","CDW","CEG","CHTR","CMCSA","COST","CPRT","CRWD","CSCO",
        "CSGP","CSX","CTAS","CTSH","DASH","DDOG","DXCM","EA","EXC","FANG",
        "FAST","FTNT","GEHC","GFS","GILD","GOOG","GOOGL","HON","IDXX","INTC",
        "INTU","ISRG","KDP","KHC","KLAC","LIN","LRCX","LULU","MAR","MCHP",
        "MDLZ","MELI","META","MNST","MRVL","MSFT","MSTR","MU","NFLX","NVDA",
        "NXPI","ODFL","ON","ORLY","PANW","PAYX","PCAR","PDD","PEP","PLTR",
        "PYPL","QCOM","REGN","ROP","ROST","SBUX","SHOP","SNPS","TEAM","TMUS",
        "TRI","TSLA","TTD","TTWO","TXN","VRSK","VRTX","WBD","WDAY","XEL","ZS"
    ],
    "LEVERAGE_ETF": [
        "CURE", "DPST", "EDC", "EDZ", "FAS", "FAZ", "FNGU", "RXD", "SOXL", 
        "SOXS", "SPXL", "SPXU", "SQQQ", "TNA", "TQQQ", "TYD", "TZA", "YANG", "YINN"
    ],
    "IBD": [#Liste 25.Okt
        "AAPL", "AEIS", "AEM", "AFRM", "AIR", "AMAT", "AMD", "AMSC", "ANET", "ANIP", 
        "APH", "APP", "ARGX", "ARQT", "ASML", "ATAT", "AU", "AVGO", "BELFB", "BETR", 
        "BTSG", "CBRE", "CDE", "CIEN", "CLS", "CLSK", "CMI", "COHR", "CRDO", "CRS", 
        "CSTM", "CVNA", "CW", "DASH", "DAVE", "DDOG", "DELL", "ECG", "EME", "EXPE", 
        "FIX", "FTAI", "FUTU", "GE", "GFI", "GH", "GILT", "GLXY", "GOOG", "GOOGL", 
        "GSK", "GTX", "HG", "HIMS", "HOOD", "HWM", "IDCC", "IESC", "INOD", "KGC", 
        "KLAC", "KRMN", "LITE", "LRCX", "MCK", "MDB", "MEDP", "MEG", "MKSI", "MPWR", 
        "MU", "MYRG", "NUTX", "NVDA", "NVMI", "NXT", "ORA", "ORLA", "OUST", "PAHC", 
        "PLTR", "PTRN", "REZI", "RIOT", "RKLB", "RMBS", "RYTM", "SEI", "SHOP", "SIG", 
        "SNDK", "SNOW", "SOFI", "SOUN", "STNE", "STOK", "STX", "SUPN", "SXI", "TARS", 
        "TBBK", "TEL", "TEM", "TFPM", "THC", "TIGR", "TMDX", "TPC", "TSM", "TVTX", 
        "VMI", "VRT", "VSEC", "WDC", "WGS", "ZS"
    ]
}

# ----------------------------------------------------------------------
# 2. Datenabruf und Filterlogik
# ----------------------------------------------------------------------

# Globale Variable für yfinance-Fehlermeldungen
YFINANCE_ERRORS = []
YFINANCE_LOCK = threading.Lock()

def download_data(all_tickers):
    """
    Lädt historische Daten für alle Ticker im Massen-Download herunter. 
    Korrigeirte Version: Verwendet wieder den Massen-Download, um Timeouts zu vermeiden.
    """
    global YFINANCE_ERRORS
    with YFINANCE_LOCK:
        YFINANCE_ERRORS.clear() # Fehler bei jedem Scan zurücksetzen
        
    try:
        # Massen-Download der Daten
        all_data = yf.download(all_tickers, period="251d", auto_adjust=False, progress=False)
        
        if all_data.empty:
            raise Exception("No data could be retrieved from yfinance (empty DataFrame).")

        # Prüfe auf fehlgeschlagene Downloads und protokolliere sie
        downloaded_tickers = all_data.columns.get_level_values(1).unique()
        missing_tickers = [t for t in all_tickers if t not in downloaded_tickers]
        
        if missing_tickers:
            # yfinance zeigt die Timeouts/Fehler in der Konsole an. Wir müssen hier 
            # nur die Ticker protokollieren, die nicht im Ergebnis-DF sind.
            for ticker in missing_tickers:
                with YFINANCE_LOCK:
                    YFINANCE_ERRORS.append(f"Skipped/Missing data for {ticker} (possible Timeout/Error during bulk download).")

        return all_data
        
    except Exception as e:
        # Fängt allgemeine Verbindungsfehler/Timeouts ab, die den gesamten Bulk-Download verhindern
        raise Exception(f"Failed to download data from yfinance. (Details: {e})")

def run_filter(all_data_df, list_name, ticker_list):
    """Führt den technischen Filter für eine Liste von Tickern aus."""
    filtered_list = []
    
    # Ermittle alle erfolgreich geladenen Ticker im MultiIndex
    available_tickers = all_data_df.columns.get_level_values(1).unique()

    for ticker in ticker_list:
        try:
            # Ticker überspringen, wenn er nicht erfolgreich geladen wurde
            if ticker not in available_tickers:
                continue

            data = all_data_df.xs(ticker, axis=1, level=1, drop_level=False)
            data.columns = [col[0] for col in data.columns]
            data = data.dropna(subset=["Open", "High", "Low", "Close"])
            if len(data) < 251:  
                continue

            # Indikatoren berechnen
            roc_250 = ROCIndicator(close=data["Close"], window=250)
            roc_120 = ROCIndicator(close=data["Close"], window=120) 
            rsi = RSIIndicator(close=data["Close"], window=2)
            adx = ADXIndicator(high=data["High"], low=data["Low"], close=data["Close"], window=14, fillna=False)
            
            data["ROC_250"] = roc_250.roc().round(2)
            data["ROC_120"] = roc_120.roc().round(2) 
            data["RSI_2"] = rsi.rsi().round(2)
            data["ADX_14"] = adx.adx().round(2)
            
            last_row = data.iloc[-1]
            
            # Filter anwenden: RSI < 10 AND ADX > 20 AND ROC_250 > 0
            if last_row["RSI_2"] < 10 and last_row["ADX_14"] > 20 and last_row["ROC_250"] > 0:
                filtered_list.append({
                    "Ticker": ticker,
                    "Price": round(last_row["Close"], 2),
                    "RSI": round(last_row["RSI_2"], 2),
                    "ROC250": round(last_row["ROC_250"], 1), 
                    "ADX": round(last_row["ADX_14"], 1),
                    "ROC120": round(last_row["ROC_120"], 1) 
                })
        
        except KeyError:
            continue
        except Exception:
            continue

    return pd.DataFrame(filtered_list)

# ----------------------------------------------------------------------
# 3. Flask UI und Logik
# ----------------------------------------------------------------------
app = Flask(__name__)

# Globale Variable für den Scan-Status und die Ergebnisse
scan_status = {"message": "Select a list to start the scan.", "results": None, "error": "", "scanning": False, "last_scan_list": None}

def run_full_scan_thread(list_name):
    """Führt den Scan und die Filterung aus und aktualisiert den globalen Status."""
    global scan_status
    
    try:
        # Status setzen: Download-Start 
        scan_status = {"message": "Downloading data... please wait", "results": None, "error": "", "scanning": True, "last_scan_list": list_name}

        # Laden ALLER Ticker-Daten
        all_tickers = [ticker for sublist in tickers_by_list.values() for ticker in sublist]
        all_data = download_data(all_tickers) # NEUE, effizientere Funktion
        
        # Status setzen: Scanning
        scan_status["message"] = f"Scanning {list_name.replace('_', ' ')}..."

        ticker_list = tickers_by_list[list_name]
        result_df = run_filter(all_data, list_name, ticker_list)
        
        # Ergebnisse formatieren und speichern
        if result_df.empty:
            results_content = f"<p class='text-center mt-3 no-signal'>No signals found for {list_name.replace('_', ' ')}.</p>"
        else:
            # Sortierung nach ROC120, absteigend (highest first)
            df_sorted = result_df.sort_values(by="ROC120", ascending=False)
            
            # Header-Zeile
            header_row = """
                <tr>
                    <th class="text-start">Ticker</th>
                    <th class="text-end">Price</th>
                    <th class="text-end">RSI</th>
                    <th class="text-end">ROC250</th>
                    <th class="text-end">ADX</th>
                    <th class="text-end desc">ROC120</th>
                </tr>
            """
            
            # Pandas HTML body
            body_html = df_sorted.to_html(
                classes='trade-table', 
                index=False,
                header=False,
                float_format=lambda x: f'{x:.1f}' if x in df_sorted[['ROC250', 'ADX', 'ROC120']].values else (f'{x:.2f}' if x in df_sorted['Price'].values else f'{x:.2f}'),
                justify='center'
            )
            
            # Zusammenfügen
            results_content = f"""
            <table class='trade-table' id='resultsTable'>
                <thead>
                    {header_row}
                </thead>
                {body_html.replace('<table class="trade-table">', '').replace('</table>', '')}
            </table>
            """

        scan_status["results"] = results_content
        scan_status["message"] = f"Scan for {list_name.replace('_', ' ')} finished."
        
    except Exception as e:
        scan_status["error"] = str(e)
        scan_status["message"] = f"Scan for {list_name.replace('_', ' ')} FAILED! (General Download Error)"
        scan_status["results"] = None
        
    finally:
        scan_status["scanning"] = False


@app.route("/", methods=["GET", "POST"])
def index():
    """Startseite und Hauptansicht."""
    global scan_status
    global YFINANCE_ERRORS
    
    if request.method == "POST":
        list_name = request.form.get("list_name")
        if list_name and list_name in tickers_by_list and not scan_status["scanning"]:
            # Scan in einem separaten Thread starten
            thread = threading.Thread(target=run_full_scan_thread, args=(list_name,))
            thread.start()
            # Weiterleitung zur Startseite (wird durch JS-Polling aktualisiert)
            return redirect(url_for('index'))

    # HTML-Template
    html_template = """ 
    <!doctype html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
        <title>Grodt Tradefinder</title>
        <link href="https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;700&display=swap" rel="stylesheet">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            /* -------------------------------------- */
            /* Global & Typography */
            /* -------------------------------------- */
            body { 
                background-color: #1a1a1a; 
                color: #e5e9f0; 
                font-family: 'Roboto Mono', monospace; 
            }
            .container { max-width: 650px; padding: 20px; }
            
            .main-header { 
                color: #92b4cc; 
                font-weight: 700; 
                margin-bottom: 0;
            }
            .status-container {
                padding: 20px;
                margin-bottom: 25px;
                background-color: #212529;
                border-radius: 10px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.6);
            }

            /* -------------------------------------- */
            /* Status & Errors */
            /* -------------------------------------- */
            .status-text { 
                font-size: 1.1rem; 
                font-weight: bold; 
                color: #ffffff;
                margin-top: 15px; 
            }
            .error-text { 
                color: #ff5252; 
                font-weight: bold; 
                font-size: 0.85rem; 
                min-height: 20px; 
            }
            .no-signal {
                 color: #999;
                 font-style: italic;
                 margin-top: 20px !important;
            }
            .yfinance-error-container {
                margin-top: 25px;
                padding: 15px;
                background-color: #331f1f; /* Dunkelrot/Braun */
                border: 1px solid #ff5252;
                border-radius: 10px;
                text-align: left;
                font-size: 0.75rem;
                color: #ffbaba;
            }
            .yfinance-error-container p {
                margin-bottom: 5px;
                color: #ff5252;
            }
            .yfinance-error-container ul {
                list-style: none;
                padding-left: 0;
            }
            .yfinance-error-container li {
                margin-bottom: 2px;
                word-wrap: break-word; /* Lange Ticker-Namen brechen */
            }


            /* -------------------------------------- */
            /* Buttons */
            /* -------------------------------------- */
            .btn-custom { 
                background-color: #3e6d99; /* Grundfarbe: Wie alter Hover */
                border: none;
                color: white; 
                font-weight: 600;
                border-radius: 8px;
                transition: background-color 0.2s;
                padding: 10px 15px;
                font-family: 'Roboto Mono', monospace; 
            }
            .btn-custom:hover:not(:disabled) { 
                background-color: #325a7d; /* Hover: Noch dunkler */
                color: white;
            }
            .btn-custom:disabled {
                background-color: #343a40 !important;
                color: #a9a9a9;
            }
            .button-container {
                padding: 15px;
                background-color: #212529;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.4);
            }

            /* -------------------------------------- */
            /* Results Table & Sorting */
            /* -------------------------------------- */
            .result-container {
                background-color: #212529;
                padding: 20px;
                border-radius: 10px;
                margin-top: 25px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.6);
            }
            
            .trade-table { 
                width: 100%;
                margin-bottom: 0;
                color: #e5e9f0; 
                border-radius: 8px;
                overflow: hidden; 
                background-color: #1a1a1a;
                font-family: 'Roboto Mono', monospace; 
            }
            .trade-table thead th {
                background-color: #343a40; 
                color: #fff;
                border-bottom: 2px solid #4f89b9; 
                font-size: 0.9rem;
                padding: 10px 8px;
                position: relative;
            }
            .trade-table thead th:hover {
                background-color: #3e6d99; 
            }
            /* Sortier-Symbole (nur für ROC120 angezeigt) */
            .desc:after {
                content: '';
                display: inline-block;
                width: 0;
                height: 0;
                margin-left: 5px;
                vertical-align: middle;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid #fff;
            }

            .trade-table tbody tr {
                transition: background-color 0.1s;
            }
            .trade-table tbody tr:hover {
                background-color: #383e45 !important;
            }
            
            .trade-table td {
                padding: 8px 8px;
                border-top: 1px solid #444;
                font-size: 0.85rem;
                vertical-align: middle;
            }
            
            /* Text-Ausrichtung innerhalb der Tabelle korrigieren */
            .text-start { text-align: left !important; }
            .text-end { text-align: right !important; }
            .trade-table td:nth-child(1) { text-align: left !important; } 
        </style>
    </head>
    <body>
        <div class="container text-center pt-5">
            
            <div class="status-container">
                <h4 class="main-header">Grodt Tradefinder</h4>
                
                <div class="d-flex justify-content-center align-items-center">
                    <p class="status-text me-3">{{ scan_status['message'] }}</p>
                    {% if scan_status['scanning'] %}
                        <div class="spinner-border spinner-border-sm text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                    {% endif %}
                </div>
            </div>
            
            <div class="error-text mb-3">{{ scan_status['error'] }}</div>
            
            <form method="POST" class="d-flex justify-content-center gap-3 button-container">
                {% for key, name in tickers_by_list.items() %}
                    <button type="submit" name="list_name" value="{{ key }}" 
                            class="btn btn-custom" 
                            {% if scan_status['scanning'] %}disabled{% endif %}>
                        {{ key.replace('_', ' ') }} 
                    </button>
                {% endfor %}
            </form>
            
            {% if YFINANCE_ERRORS %}
                <div class="yfinance-error-container">
                    <p class="mb-2" style="font-weight: bold; color: #ff5252;">⚠️ Yfinance Errors/Timeouts: The following tickers were skipped due to missing data during bulk download:</p>
                    <ul>
                    {% for error in YFINANCE_ERRORS %}
                        <li>{{ error }}</li>
                    {% endfor %}
                    </ul>
                </div>
            {% endif %}

            {% if scan_status['results'] %}
                <div class="result-container text-start">
                    {{ scan_status['results']|safe }}
                </div>
            {% endif %}

        </div>

        {% if scan_status['scanning'] %}
            <script>
                setTimeout(function(){
                    window.location.href = window.location.href; 
                }, 2000);
            </script>
        {% endif %}

        <script>
            document.addEventListener('DOMContentLoaded', () => {
                const table = document.getElementById('resultsTable');
                if (!table) return;
                
                const tbody = table.querySelector('tbody');
                if (tbody) {
                    const rows = Array.from(tbody.querySelectorAll('tr'));
                    rows.forEach((row, index) => {
                        row.style.backgroundColor = (index % 2 === 0) ? '#333333' : '#2a2a2a';
                    });
                }
            });
        </script>
    </body>
    </html>
    """
    
    return render_template_string(html_template, scan_status=scan_status, tickers_by_list=tickers_by_list, YFINANCE_ERRORS=YFINANCE_ERRORS)

# ----------------------------------------------------------------------
# 4. Die App starten
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # HOST='0.0.0.0' erlaubt Zugriff aus dem lokalen Netzwerk (z.B. Handy/Tablet)
    app.run(debug=True, threaded=False, host='0.0.0.0')