import requests
import pandas as pd
from datetime import datetime, timedelta
import os

FUNDS = [
    {"code": "150797", "name": "WhiteOak Capital Large Cap Fund", "threshold": 6},
    {"code": "151796", "name": "360 ONE FLEXICAP FUND", "threshold": 9},
    {"code": "148990", "name": "ICICI Prudential Flexicap Fund", "threshold": 9},
    {"code": "153859", "name": "JioBlackRock Flexi Cap Fund", "threshold": 9},
    {"code": "119775", "name": "Kotak Midcap Fund", "threshold": 9},
    {"code": "150915", "name": "Mahindra Manulife Small Cap Fund", "threshold": 12},
    {"code": "152600", "name": "HDFC Manufacturing fund", "threshold": 12},
    {"code": "152237", "name": "Motilal Oswal Small Cap Fund", "threshold": 12},
    {"code": "149870", "name": "HDFC Nifty 100 Equal Weight Index Fund", "threshold": 9},
    {"code": "151895", "name": "Bajaj Finserv Flexi Cap Fund", "threshold": 9}
]

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("Missing BOT_TOKEN or CHAT_ID GitHub secrets")

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


def get_fund_status(fund):
    df = fetch_nav(fund["code"])

    latest_nav = df.iloc[0]["nav"]
    cutoff_date = datetime.today() - timedelta(days=365)
    high_52w = df[df["date"] >= cutoff_date]["nav"].max()

    drawdown_pct = (high_52w - latest_nav) / high_52w * 100
    drawdown_abs = high_52w - latest_nav

    triggered = drawdown_pct >= fund["threshold"]

    return {
        "name": fund["name"],
        "latest_nav": latest_nav,
        "high_52w": high_52w,
        "drawdown_pct": drawdown_pct,
        "drawdown_abs": drawdown_abs,
        "threshold": fund["threshold"],
        "triggered": triggered
    }


def main():
    state = load_state()

    triggered_funds = []
    normal_funds = []

    for fund in FUNDS:
        status = get_fund_status(fund)
        if status["triggered"]:
            triggered_funds.append(status)
        else:
            normal_funds.append(status)

        state[fund["code"]] = status["triggered"]

    today = datetime.today().strftime("%d %b %Y")

    message_lines = [f"📊 Mutual Fund NAV Status ({today})\n"]

    if triggered_funds:
        message_lines.append("🚨 Triggered")
        for f in triggered_funds:
            message_lines.append(
                f"• {f['name']}\n"
                f"  NAV: ₹{f['latest_nav']:.2f} | 52W High: ₹{f['high_52w']:.2f}\n"
                f"  ↓ ₹{f['drawdown_abs']:.2f} ({f['drawdown_pct']:.2f}%) | Threshold: {f['threshold']}%\n"
            )

    if normal_funds:
        message_lines.append("ℹ️ Not Triggered")
        for f in normal_funds:
            message_lines.append(
                f"• {f['name']}\n"
                f"  NAV: ₹{f['latest_nav']:.2f} | 52W High: ₹{f['high_52w']:.2f}\n"
                f"  ↓ ₹{f['drawdown_abs']:.2f} ({f['drawdown_pct']:.2f}%) | Threshold: {f['threshold']}%\n"
            )

    send_alert("\n".join(message_lines))
    save_state(state)


if __name__ == "__main__":
    main()
