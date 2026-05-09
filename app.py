from flask import Flask, request
import requests
import os
import json

app = Flask(__name__)

APP_ID = "MTc4OTk3MjE4NjYw"
APP_SECRET = "1lNck7WR6ABC1yWmbw1diVIhCEsO-Vih"
GEMINI_API_KEY = "AIzaSyBGMW1Pum5Q9oEJHUuOfshBRx21XZNYSSw"

COMPANY_INFO = """
Bạn là bot hỗ trợ nội bộ tên "Khủng Long 5 Canh" của công ty SPX Express.
Hãy trả lời ngắn gọn, thân thiện, chuyên nghiệp bằng tiếng Việt.
Nếu câu hỏi không liên quan đến thông tin bên dưới, hãy dùng kiến thức chung để trả lời.
Nếu hoàn toàn không biết, hãy nói: "Tôi chưa có thông tin này, vui lòng liên hệ HR hoặc IT."

=== THÔNG TIN CÔNG TY ===
- Tên công ty: SPX Express
- Email IT: it-support@spxexpress.com
- Email HR: hr@spxexpress.com

=== GIỜ LÀM VIỆC ===
- Thứ 2 - Thứ 6: 8:00 - 17:30
- Thứ 7: 8:00 - 12:00
- Chủ nhật: Nghỉ

=== QUY TRÌNH XIN NGHỈ PHÉP ===
- Báo trước ít nhất 3 ngày làm việc
- Gửi đơn xin nghỉ phép qua form HR
- Cần được quản lý trực tiếp phê duyệt

=== SỰ CỐ IT ===
- Email: it-support@spxexpress.com
- Máy tính hỏng, mất mật khẩu, lỗi hệ thống liên hệ IT

=== THANH TOÁN & CHI PHÍ ===
- Nộp hóa đơn gốc cho phòng kế toán trước ngày 25 hàng tháng
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

def ask_gemini(message_text):
    # Thử gemini-2.0-flash trước
    models = [
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest"
    ]
    
    for model in models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": f"{COMPANY_INFO}\n\nNgười dùng hỏi: {message_text}"
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "maxOutputTokens": 800,
                    "temperature": 0.7
                }
            }
            r = requests.post(url, headers=headers, json=payload, timeout=30)
            result = r.json()
            print(f"GEMINI [{model}] STATUS: {r.status_code}")
            print(f"GEMINI [{model}] RESULT: {result}")
            
            # Kiểm tra lỗi
            if "error" in result:
                print(f"MODEL {model} ERROR: {result['error']}")
                continue
                
            candidates = result.get("candidates", [])
            if candidates:
                text_reply = candidates[0]["content"]["parts"][0]["text"]
                print(f"REPLY: {text_reply}")
                return text_reply
                
        except Exception as e:
            print(f"GEMINI [{model}] EXCEPTION: {e}")
            continue
    
    # Fallback: trả lời theo keyword nếu Gemini lỗi hết
    return fallback_reply(message_text)

def fallback_reply(message_text):
    msg = message_text.lower().strip()
    if any(w in msg for w in ["xin chào", "hello", "hi", "chào", "hey"]):
        return "Xin chào! 👋 Tôi là bot Khủng Long 5 Canh của SPX Express. Tôi có thể giúp gì cho bạn?"
    elif any(w in msg for w in ["giờ làm việc", "giờ mở cửa", "làm việc mấy giờ"]):
        return "⏰ Giờ làm việc:\n- Thứ 2 - Thứ 6: 8:00 - 17:30\n- Thứ 7: 8:00 - 12:00\n- Chủ nhật: Nghỉ"
    elif any(w in msg for w in ["nghỉ phép", "xin nghỉ", "nghỉ"]):
        return "📋 Quy trình xin nghỉ phép:\n1. Báo trước ít nhất 3 ngày\n2. Gửi đơn qua form HR\n3. Chờ quản lý phê duyệt\nLiên hệ: hr@spxexpress.com"
    elif any(w in msg for w in ["it", "máy tính", "mật khẩu", "lỗi", "sự cố"]):
        return "🖥️ Hỗ trợ IT:\nEmail: it-support@spxexpress.com\nMô tả sự cố và gửi email, IT sẽ phản hồi sớm nhất!"
    elif any(w in msg for w in ["lương", "thanh toán", "hóa đơn", "kế toán"]):
        return "💰 Thanh toán chi phí:\nNộp hóa đơn gốc cho kế toán trước ngày 25 hàng tháng."
    elif any(w in msg for w in ["help", "giúp", "menu", "hướng dẫn"]):
        return "📋 Tôi có thể giúp bạn về:\n- Giờ làm việc\n- Xin nghỉ phép\n- Sự cố IT\n- Thanh toán chi phí\n- Và nhiều câu hỏi khác!\n\nCứ hỏi tự nhiên nhé 😊"
    else:
        return f"Tôi nhận được câu hỏi của bạn về '{message_text}'.\nHiện tôi đang gặp sự cố kết nối AI. Vui lòng liên hệ:\n- IT: it-support@spxexpress.com\n- HR: hr@spxexpress.com"

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
                reply = ask_gemini(message_text)
                send_message(employee_code, reply)

    except Exception as e:
        print(f"ERROR: {e}")

    return json.dumps({"status": "ok"}), 200, {"Content-Type": "application/json"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
