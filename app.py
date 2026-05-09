from flask import Flask, request
import requests
import os
import json

app = Flask(__name__)

APP_ID = "MTc4OTk3MjE4NjYw"
APP_SECRET = "1lNck7WR6ABC1yWmbw1diVIhCEsO-Vih"

def get_access_token():
    url = "https://openapi.seatalk.io/auth/app_access_token"
    try:
        r = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=10)
        print(f"TOKEN RESULT: {r.json()}")
        return r.json().get("app_access_token", "")
    except Exception as e:
        print(f"TOKEN ERROR: {e}")
        return ""

def send_message(employee_code, text):
    token = get_access_token()
    if not token:
        print("NO TOKEN!")
        return

    # Thử endpoint chính thức từ docs
    url = "https://openapi.seatalk.io/messaging/v2/bot/send_to_user"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "employee_code": str(employee_code),
        "message": {
            "tag": "text",
            "text": {"content": text}
        }
    }
    print(f"TRY 1 - payload: {payload}")
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"TRY 1 RESULT: {r.status_code} {r.text}")
    except Exception as e:
        print(f"TRY 1 ERROR: {e}")

    # Thử endpoint thứ 2
    url2 = "https://openapi.seatalk.io/bot/v1/message"
    print(f"TRY 2 - url: {url2}")
    try:
        r2 = requests.post(url2, json=payload, headers=headers, timeout=10)
        print(f"TRY 2 RESULT: {r2.status_code} {r2.text}")
    except Exception as e:
        print(f"TRY 2 ERROR: {e}")

    # Thử endpoint thứ 3 - đúng theo docs
    url3 = "https://openapi.seatalk.io/messaging/v2/single_chat"
    payload3 = {
        "employee_code": str(employee_code),
        "message": {
            "tag": "text",
            "text": {"content": text}
        }
    }
    print(f"TRY 3 - url: {url3}")
    try:
        r3 = requests.post(url3, json=payload3, headers=headers, timeout=10)
        print(f"TRY 3 RESULT: {r3.status_code} {r3.text}")
    except Exception as e:
        print(f"TRY 3 ERROR: {e}")

def generate_reply(message_text):
    msg = message_text.lower().strip()
    if any(w in msg for w in ["xin chào", "hello", "hi", "chào"]):
        return "Xin chào! Tôi là bot Khủng Long 5 Canh 🦖"
    elif any(w in msg for w in ["giờ làm việc", "làm việc"]):
        return "⏰ Thứ 2-6: 8:00-17:30 | Thứ 7: 8:00-12:00"
    elif any(w in msg for w in ["liên hệ", "hotline"]):
        return "📞 Hotline: 1900-xxxx\nEmail: support@company.com"
    elif any(w in msg for w in ["help", "giúp", "menu"]):
        return "📋 Menu:\n- xin chào\n- giờ làm việc\n- liên hệ\n- help"
    else:
        return f"Tôi chưa hiểu '{message_text}'. Gõ 'help' để xem menu!"

@app.route("/", methods=["GET"])
def home():
    return "Khung Long 5 Canh Bot dang chay!", 200

@app.route("/webhook/seatalk", methods=["GET"])
def webhook_get():
    return json.dumps({"status": "ok"}), 200, {"Content-Type": "application/json"}

@app.route("/webhook/seatalk", methods=["POST"])
def webhook_post():
    try:
        raw = request.data
        print(f"RAW: {raw}")
        data = json.loads(raw)
        event = data.get("event", {})

        if "seatalk_challenge" in event:
            challenge = event["seatalk_challenge"]
            return json.dumps({"seatalk_challenge": challenge}), 200, {"Content-Type": "application/json"}

        if "seatalk_challenge" in data:
            challenge = data["seatalk_challenge"]
            return json.dumps({"seatalk_challenge": challenge}), 200, {"Content-Type": "application/json"}

        event_type = data.get("event_type", "")
        print(f"EVENT_TYPE: {event_type}")
        print(f"FULL EVENT: {event}")

        if event_type == "message_from_bot_subscriber":
            employee_code = event.get("employee_code", "")
            message_text = event.get("message", {}).get("text", {}).get("content", "")
            print(f"EMPLOYEE_CODE: {employee_code}, MSG: {message_text}")
            if employee_code and message_text:
                reply = generate_reply(message_text)
                send_message(employee_code, reply)

    except Exception as e:
        print(f"ERROR: {e}")

    return json.dumps({"status": "ok"}), 200, {"Content-Type": "application/json"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
