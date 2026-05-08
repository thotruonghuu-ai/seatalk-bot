from flask import Flask, request, jsonify
import requests
import os
import json

app = Flask(__name__)

APP_ID = "MTc4OTk3MjE4NjYw"
APP_SECRET = "1lNck7WR6ABC1yWmbw1diVlhCEsO-Vih"

def get_access_token():
    url = "https://openapi.seatalk.io/auth/app_access_token"
    payload = {"app_id": APP_ID, "app_secret": APP_SECRET}
    try:
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        return data.get("app_access_token", "")
    except:
        return ""

def send_message(user_id, text):
    token = get_access_token()
    if not token:
        return {"error": "no token"}
    url = "https://openapi.seatalk.io/messaging/v2/single_chat"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "receiver_id": user_id,
        "message_type": "text",
        "text": {"content": text}
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        return response.json()
    except:
        return {"error": "send failed"}

def generate_reply(message_text):
    message_text = message_text.lower().strip()
    if any(w in message_text for w in ["xin chào", "hello", "hi", "chào"]):
        return "Xin chào! Tôi là bot Khủng Long 5 Canh 🦖"
    elif any(w in message_text for w in ["giờ làm việc", "làm việc"]):
        return "⏰ Thứ 2-6: 8:00-17:30 | Thứ 7: 8:00-12:00"
    elif any(w in message_text for w in ["liên hệ", "hotline"]):
        return "📞 Hotline: 1900-xxxx\nEmail: support@company.com"
    elif any(w in message_text for w in ["help", "giúp", "menu"]):
        return "📋 Menu:\n- xin chào\n- giờ làm việc\n- liên hệ\n- help"
    else:
        return f"Tôi chưa hiểu '{message_text}'. Gõ 'help' để xem menu!"

@app.route("/", methods=["GET"])
def home():
    return "Khung Long 5 Canh Bot dang chay!", 200

@app.route("/webhook/seatalk", methods=["GET"])
def webhook_get():
    return jsonify({"status": "ok"}), 200

@app.route("/webhook/seatalk", methods=["POST"])
def webhook_post():
    try:
        raw = request.data
        print(f"RAW DATA: {raw}")
        data = json.loads(raw)
        print(f"PARSED: {data}")

        if "seatalk_challenge" in data:
            challenge = data["seatalk_challenge"]
            print(f"CHALLENGE: {challenge}")
            resp = json.dumps({"seatalk_challenge": challenge})
            return resp, 200, {"Content-Type": "application/json"}

        event = data.get("event", {})
        event_type = data.get("type", "")
        if event_type == "bot.receive_message":
            from_user = event.get("from_user_id", "")
            message_text = event.get("message", {}).get("text", {}).get("content", "")
            print(f"MSG from {from_user}: {message_text}")
            reply = generate_reply(message_text)
            send_message(from_user, reply)

    except Exception as e:
        print(f"ERROR: {e}")

    return json.dumps({"status": "ok"}), 200, {"Content-Type": "application/json"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
