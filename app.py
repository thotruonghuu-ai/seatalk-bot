from flask import Flask, request
import requests
import os
import json

app = Flask(__name__)

APP_ID = "MTc4OTk3MjE4NjYw"
APP_SECRET = "1lNck7WR6ABC1yWmbw1diVIhCEsO-Vih"
GEMINI_API_KEY = "AIzaSyBGMW1Pum5Q9oEJHUuOfshBRx21XZNYSSw"

# ====================================================
# THÔNG TIN CÔNG TY - BẠN CHỈ CẦN CHỈNH SỬA PHẦN NÀY
# Thêm bất kỳ thông tin gì ở đây, bot sẽ tự hiểu và trả lời
# ====================================================
COMPANY_INFO = """
Bạn là bot hỗ trợ nội bộ tên "Khủng Long 5 Canh" của công ty SPX Express.
Hãy trả lời ngắn gọn, thân thiện, chuyên nghiệp bằng tiếng Việt.
Nếu câu hỏi không liên quan đến thông tin bên dưới, hãy dùng kiến thức chung của bạn để trả lời.
Nếu hoàn toàn không biết, hãy nói: "Tôi chưa có thông tin này, vui lòng liên hệ HR hoặc IT để được hỗ trợ."

=== THÔNG TIN CÔNG TY ===
- Tên công ty: SPX Express
- Website: spxexpress.com
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
- Liên hệ: hr@spxexpress.com

=== SỰ CỐ IT ===
- Email: it-support@spxexpress.com
- Máy tính hỏng, mất mật khẩu, lỗi hệ thống → liên hệ IT
- Ngoài giờ làm việc: gửi email, IT sẽ phản hồi sáng hôm sau

=== THANH TOÁN & CHI PHÍ ===
- Nộp hóa đơn gốc cho phòng kế toán
- Hạn nộp: trước ngày 25 hàng tháng
- Liên hệ kế toán để biết thêm chi tiết

=== [THÊM THÔNG TIN KHÁC TẠI ĐÂY] ===
Ví dụ:
- Chính sách bảo hiểm: ...
- Phúc lợi nhân viên: ...
- Danh sách phòng ban: ...
- Nội quy công ty: ...
"""
# ====================================================

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
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [
                {
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
        print(f"GEMINI RESULT: {result}")
        candidates = result.get("candidates", [])
        if candidates:
            return candidates[0]["content"]["parts"][0]["text"]
        return "Xin lỗi, tôi không thể trả lời lúc này. Vui lòng thử lại!"
    except Exception as e:
        print(f"GEMINI ERROR: {e}")
        return "Xin lỗi, có lỗi xảy ra. Vui lòng thử lại!"

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
