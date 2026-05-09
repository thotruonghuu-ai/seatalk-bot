from flask import Flask, request
import requests
import os
import json

app = Flask(__name__)

APP_ID = "MTc4OTk3MjE4NjYw"
APP_SECRET = "1lNck7WR6ABC1yWmbw1diVIhCEsO-Vih"
GROQ_API_KEY = "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"
GEMINI_API_KEY = "AIzaSyBGMW1Pum5Q9oEJHUuOfshBRx21XZNYSSw"

COMPANY_INFO = """
Bạn là bot hỗ trợ nội bộ tên "Khủng Long 5 Canh" của công ty SPX Express.
Hãy trả lời ngắn gọn, thân thiện, chuyên nghiệp bằng tiếng Việt.
Nếu câu hỏi không liên quan đến thông tin bên dưới, hãy dùng kiến thức chung để trả lời.
Nếu hoàn toàn không biết, hãy nói: "Tôi chưa có thông tin này, vui lòng liên hệ HR hoặc IT."

=== THÔNG TIN Trương Hữu Thọ ===
- Tên công ty: SPX Express
- Email Chủ Khủng Long: tho.truonghuu@spxexpress.com
- Seatalk: https://link.seatalk.io/profile/open?seatalk_id=1382308472

=== GIỜ LÀM VIỆC ===
- Thứ 2 - Thứ 7: 9:00 - 18:00
- Chủ nhật: Nghỉ và sẽ tàng hình
- 

=== QUY TRÌNH XIN NGHỈ PHÉP ===
- Báo trước ít nhất 3 ngày làm việc
- Gửi đơn xin nghỉ phép qua form HR
- Cần được quản lý trực tiếp phê duyệt
- Liên hệ: đến các Sup trong ca
- nam.nguyenhoang01@spxexpress.com	Nguyễn Hoàng Nam
tan.truongminh@spxexpress.com	Trương Minh Tân
truoc.truongviet@spxexpress.com	Trương Việt Trước

=== SỰ CỐ BOT KHUNG LONG ===
- Email Chủ Khủng Long: tho.truonghuu@spxexpress.com
- Seatalk: https://link.seatalk.io/profile/open?seatalk_id=1382308472
- đâng hoàn thiện

=== Bé BOT ===
- Tôi không biết đến haha!

=== Xuân Nhi, Liễu Thị Xuân Nhi ===
Bạn này là Lead SOC rất dữ
"""

def get_access_token():
    url = "https://openapi.seatalk.io/auth/app_access_token"
    try:
        r = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=10)
        return r.json().get("app_access_token", "")
    except Exception as e:
        print(f"TOKEN ERROR: {e}")
        return ""

def send_message(employee_code, text):
    token = get_access_token()
    if not token:
        return
    url = "https://openapi.seatalk.io/messaging/v2/single_chat"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "employee_code": str(employee_code),
        "message": {
            "tag": "text",
            "text": {"content": text}
        }
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"SEND RESULT: {r.status_code} {r.text}")
    except Exception as e:
        print(f"SEND ERROR: {e}")

def ask_groq(message_text):
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "llama3-8b-8192",
            "messages": [
                {"role": "system", "content": COMPANY_INFO},
                {"role": "user", "content": message_text}
            ],
            "max_tokens": 800,
            "temperature": 0.7
        }
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        result = r.json()
        print(f"GROQ STATUS: {r.status_code}")
        if "error" in result:
            print(f"GROQ ERROR: {result['error']}")
            return None
        choices = result.get("choices", [])
        if choices:
            print("GROQ REPLY OK")
            return choices[0]["message"]["content"]
    except Exception as e:
        print(f"GROQ EXCEPTION: {e}")
    return None

def ask_gemini(message_text):
    models = ["gemini-2.0-flash-lite", "gemini-2.0-flash-exp", "gemini-1.0-pro"]
    for model in models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": f"{COMPANY_INFO}\n\nNgười dùng hỏi: {message_text}"}]
                    }
                ],
                "generationConfig": {"maxOutputTokens": 800, "temperature": 0.7}
            }
            r = requests.post(url, headers=headers, json=payload, timeout=30)
            result = r.json()
            print(f"GEMINI [{model}] STATUS: {r.status_code}")
            if "error" in result:
                print(f"GEMINI [{model}] ERROR: {result['error'].get('message','')[:80]}")
                continue
            candidates = result.get("candidates", [])
            if candidates:
                print(f"GEMINI REPLY OK from {model}")
                return candidates[0]["content"]["parts"][0]["text"]
        except Exception as e:
            print(f"GEMINI [{model}] EXCEPTION: {e}")
            continue
    return None

def fallback_reply(message_text):
    msg = message_text.lower().strip()
    if any(w in msg for w in ["xin chào", "hello", "hi", "chào", "hey"]):
        return "Xin chào! 👋 Tôi là bot Khủng Long 5 Canh của SPX Express. Tôi có thể giúp gì cho bạn?"
    elif any(w in msg for w in ["giờ làm việc", "mấy giờ", "làm việc"]):
        return "⏰ Giờ làm việc:\n- Thứ 2 - Thứ 6: 8:00 - 17:30\n- Thứ 7: 8:00 - 12:00\n- Chủ nhật: Nghỉ"
    elif any(w in msg for w in ["nghỉ phép", "xin nghỉ"]):
        return "📋 Xin nghỉ phép:\n1. Báo trước ít nhất 3 ngày\n2. Gửi đơn qua form HR\n3. Chờ quản lý phê duyệt\nLiên hệ: hr@spxexpress.com"
    elif any(w in msg for w in ["it", "máy tính", "mật khẩu", "lỗi"]):
        return "🖥️ Hỗ trợ IT:\nEmail: it-support@spxexpress.com"
    elif any(w in msg for w in ["lương", "hóa đơn", "kế toán"]):
        return "💰 Nộp hóa đơn cho kế toán trước ngày 25 hàng tháng."
    elif any(w in msg for w in ["help", "giúp", "menu"]):
        return "📋 Tôi có thể giúp:\n- Giờ làm việc\n- Xin nghỉ phép\n- Sự cố IT\n- Thanh toán\nCứ hỏi tự nhiên nhé! 😊"
    else:
        return "Liên hệ hỗ trợ:\n- IT: it-support@spxexpress.com\n- HR: hr@spxexpress.com"

def get_reply(message_text):
    print("Trying GROQ...")
    reply = ask_groq(message_text)
    if reply:
        return reply
    print("GROQ failed, trying GEMINI...")
    reply = ask_gemini(message_text)
    if reply:
        return reply
    print("Both AI failed, using FALLBACK")
    return fallback_reply(message_text)

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
        data = json.loads(raw)
        event = data.get("event", {})

        if "seatalk_challenge" in event:
            challenge = event["seatalk_challenge"]
            return json.dumps({"seatalk_challenge": challenge}), 200, {"Content-Type": "application/json"}

        if "seatalk_challenge" in data:
            challenge = data["seatalk_challenge"]
            return json.dumps({"seatalk_challenge": challenge}), 200, {"Content-Type": "application/json"}

        event_type = data.get("event_type", "")
        if event_type == "message_from_bot_subscriber":
            employee_code = event.get("employee_code", "")
            message_text = event.get("message", {}).get("text", {}).get("content", "")
            print(f"EMPLOYEE_CODE: {employee_code}, MSG: {message_text}")
            if employee_code and message_text:
                reply = get_reply(message_text)
                send_message(employee_code, reply)

    except Exception as e:
        print(f"ERROR: {e}")

    return json.dumps({"status": "ok"}), 200, {"Content-Type": "application/json"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
