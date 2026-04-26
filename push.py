import requests
import os


def pushplus_send(title, content):
    token = os.environ.get("PUSHPLUS_TOKEN")
    if not token:
        raise ValueError("PUSHPLUS_TOKEN is not set.")
    url = "http://www.pushplus.plus/send"
    data = {
        "token": token,
        "title": title,
        "content": content,
    }
    response = requests.post(url, json=data, timeout=10)
    return response.status_code == 200


if __name__ == "__main__":
    success = pushplus_send("BTC sell alert", "Test message from push.py")
    print("Push sent successfully" if success else "Push failed")
