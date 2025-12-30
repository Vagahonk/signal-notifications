import requests

TOKEN = "DEIN_BOT_TOKEN"
url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

print(requests.get(url).json())
