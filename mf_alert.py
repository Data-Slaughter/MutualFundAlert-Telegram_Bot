import requests
import pandas as pd
from datetime import datetime, timedelta
import os

FUNDS = [
    {"code": "150797", "name": "WhiteOak Capital Large Cap Fund", "threshold": 6},
    {"code": "151796", "name": "360 ONE FLEXICAP FUND", "threshold": 8},
    {"code": "148990", "name": "ICICI Prudential Flexicap Fund", "threshold": 8},
    {"code": "153859", "name": "JioBlackRock Flexi Cap Fund", "threshold": 8},
    {"code": "119775", "name": "Kotak Midcap Fund", "threshold": 10},
    {"code": "150915", "name": "Mahindra Manulife Small Cap Fund", "threshold": 15},
    {"code": "152600", "name": "HDFC Manufacturing fund", "threshold": 12}
]

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

STATE_FILE = "state.csv"

def send_alert(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": message})

def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    df = pd.read_csv(STATE_FILE)
    return dict(zip(df.code, df.alerted))

def save_state(state):
    pd.DataFrame(
        [{"code": k, "alerted": v} for k, v in state.items()]
    ).to_csv(STATE_FILE, index=False)

def fetch_nav(code):
    url = f"https://api.mfapi.in/mf/{code}"
    data = requests.get(url, timeout=20).json()
    df = pd.DataFrame(data["data"])
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y")
    df["nav"] = df["nav"].astype(float)
    return df

def check_fund(fund, state):
    df = fetch_nav(fund["code"])
    latest_nav = df.iloc[0]["nav"]
    high_52w = df[df["date"] >= datetime.today() - timedelta(days=365)]["nav"].max()
    drawdown = (high_52w - latest_nav) / high_52w * 100

    triggered = drawdown >= fund["threshold"]

    if triggered and not state.get(fund["code"], False):
        msg = (
            f"🚨 MF Alert\n"
            f"{fund['name']}\n"
            f"Drawdown: {drawdown:.2f}%\n"
            f"Threshold: {fund['threshold']}%"
        )
        send_alert(msg)
        state[fund["code"]] = True

    if not triggered:
        state[fund["code"]] = False

def main():
    state = load_state()
    for fund in FUNDS:
        check_fund(fund, state)
    save_state(state)

if __name__ == "__main__":
    main()
