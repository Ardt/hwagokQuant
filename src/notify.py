"""Notifications: Slack, Discord, Telegram, Email."""

import json
from urllib.request import Request, urlopen
import config as cfg
from src.logger import get

log = get("notify")


def send(message: str, title: str = "Quant Alert"):
    """Send notification to all enabled channels."""
    for channel, conf in cfg.NOTIFICATIONS.items():
        if not conf.get("enabled"):
            continue
        try:
            if channel == "slack":
                _slack(message, conf)
            elif channel == "discord":
                _discord(message, title, conf)
            elif channel == "telegram":
                _telegram(message, conf)
            elif channel == "email":
                _email(message, title, conf)
            log.debug(f"Sent to {channel}")
        except Exception as e:
            log.error(f"{channel} failed: {e}")


def _slack(message: str, conf: dict):
    data = json.dumps({"text": message}).encode()
    req = Request(conf["webhook_url"], data=data, headers={"Content-Type": "application/json"})
    urlopen(req)


def _discord(message: str, title: str, conf: dict):
    data = json.dumps({"content": f"**{title}**\n{message}"}).encode()
    req = Request(conf["webhook_url"], data=data,
                  headers={"Content-Type": "application/json", "User-Agent": "QuantBot/1.0"})
    urlopen(req)


def _telegram(message: str, conf: dict):
    url = f"https://api.telegram.org/bot{conf['bot_token']}/sendMessage"
    data = json.dumps({"chat_id": conf["chat_id"], "text": message, "parse_mode": "HTML"}).encode()
    req = Request(url, data=data, headers={"Content-Type": "application/json"})
    urlopen(req)


def _email(message: str, title: str, conf: dict):
    url = f"https://api.mailgun.net/v3/{conf['domain']}/messages"
    data = {
        "from": conf["sender"],
        "to": conf["recipient"],
        "subject": title,
        "text": message,
    }
    import base64
    from urllib.parse import urlencode
    auth = base64.b64encode(f"api:{conf['api_key']}".encode()).decode()
    encoded = urlencode(data).encode()
    req = Request(url, data=encoded,
                  headers={"Authorization": f"Basic {auth}",
                           "Content-Type": "application/x-www-form-urlencoded"})
    urlopen(req)
