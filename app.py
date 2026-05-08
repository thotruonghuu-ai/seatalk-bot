from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

# ==== CẤU HÌNH BOT CỦA BẠN ====
APP_ID = MTc4OTk3MjE4NjYw
APP_SECRET = 1lNck7WR6ABC1yWmbw1diVlhCEsO-Vih
# ================================

def get_access_token()
    Lấy access token từ SeaTalk
    url = httpsopenapi.seatalk.ioauthapp_access_token
    payload = {
        app_id APP_ID,
        app_secret APP_SECRET
    }
    response = requests.post(url, json=payload)
    data = response.json()
    return data.get(app_access_token, )

def send_message(user_id, text)
    Gửi tin nhắn trả lời cho user
    token = get_access_token()
    url = httpsopenapi.seatalk.iomessagingv2single_chat
    headers = {
        Authorization fBearer {token},
        Content-Type applicationjson
    }
    payload = {
        receiver_id user_id,
        message_type text,
        text {
            content text
        }
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

def generate_reply(message_text)
    
    Xử lý tin nhắn và tạo câu trả lời
    Bạn có thể chỉnh sửa phần này để bot trả lời theo ý muốn
    
    message_text = message_text.lower().strip()

    if any(word in message_text for word in [xin chào, hello, hi, chào])
        return Xin chào! Tôi là bot Khủng Long 5 Canh 🦖 Tôi có thể giúp gì cho bạn

    elif any(word in message_text for word in [giờ làm việc, giờ mở cửa, làm việc])
        return ⏰ Giờ làm việc Thứ 2 - Thứ 6, 800 - 1730nThứ 7 800 - 1200

    elif any(word in message_text for word in [liên hệ, contact, hotline, điện thoại])
        return 📞 Liên hệ hỗ trợn- Hotline 1900-xxxxn- Email support@company.com

    elif any(word in message_text for word in [giúp, help, hướng dẫn, menu])
        return (
            📋 Tôi có thể giúp bạnn
            1️⃣ Gõ 'xin chào' - Chào hỏin
            2️⃣ Gõ 'giờ làm việc' - Xem giờ làmn
            3️⃣ Gõ 'liên hệ' - Thông tin liên hện
            4️⃣ Gõ 'help' - Xem menu này
        )

    else
        return (
            fBạn vừa nhắn '{message_text}'nn
            Tôi chưa hiểu câu hỏi này 🤔n
            Gõ 'help' để xem những gì tôi có thể giúp nhé!
        )

@app.route(webhookseatalk, methods=[POST])
def webhook()
    data = request.json

    # Xử lý SeaTalk Challenge (xác thực URL)
    if seatalk_challenge in data
        challenge = data[seatalk_challenge]
        print(f✅ Challenge received {challenge})
        return jsonify({seatalk_challenge challenge})

    # Xử lý tin nhắn từ user
    try
        event = data.get(event, {})
        event_type = data.get(type, )

        if event_type == bot.receive_message
            from_user = event.get(from_user_id, )
            message = event.get(message, {})
            message_text = message.get(text, {}).get(content, )

            print(f📨 Tin nhắn từ {from_user} {message_text})

            # Tạo câu trả lời
            reply = generate_reply(message_text)

            # Gửi trả lời
            result = send_message(from_user, reply)
            print(f📤 Đã gửi trả lời {result})

    except Exception as e
        print(f❌ Lỗi {e})

    return jsonify({status ok})

@app.route(, methods=[GET])
def home()
    return 🦖 Khủng Long 5 Canh Bot đang chạy!

if __name__ == __main__
    port = int(os.environ.get(PORT, 5000))
    app.run(host=0.0.0.0, port=port)