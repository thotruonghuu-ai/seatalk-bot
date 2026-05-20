from flask import Flask, request
import requests
import os
import json
import re
import unicodedata

app = Flask(__name__)

APP_ID = "MTc4OTk3MjE4NjYw"
APP_SECRET = "1lNck7WR6ABC1yWmbw1diVIhCEsO-Vih"
GROQ_API_KEY = "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"
GEMINI_API_KEY = "AIzaSyBGMW1Pum5Q9oEJHUuOfshBRx21XZNYSSw"

# ===================== GOOGLE SHEETS CONFIG =====================
SPREADSHEET_ID = "1rcZFt0rb1hMpYSY_4S3sGdnIOFLaUiVWt2FLgEI0wbE"
SHEETS_BASE_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:json&sheet="

SHEET_OE_PROFILE    = "OE team profile"
SHEET_TASK_CALENDAR = "OE Task Calendar"
SHEET_OE_LIBRARY    = "OE Library"
SHEET_ONBOARDING_33 = "3.3 Onboarding SOC OE"
SHEET_ONBOARDING_34 = "3.4 Onboarding AOM"

# ===================== UTILS =====================
def remove_accents(text):
    if not text:
        return ""
    text = str(text)
    nfkd = unicodedata.normalize('NFKD', text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()

def normalize(text):
    return remove_accents(text)

def fetch_sheet_data(sheet_name):
    try:
        import urllib.parse
        encoded = urllib.parse.quote(sheet_name)
        url = SHEETS_BASE_URL + encoded
        r = requests.get(url, timeout=15)
        text = r.text
        start = text.index('{')
        end = text.rindex('}') + 1
        raw_json = text[start:end]
        data = json.loads(raw_json)
        rows = data.get("table", {}).get("rows", [])
        cols = data.get("table", {}).get("cols", [])
        result = []
        for row in rows:
            cells = row.get("c", [])
            row_data = []
            for cell in cells:
                if cell is None:
                    row_data.append("")
                else:
                    val = cell.get("v", "") or cell.get("f", "") or ""
                    row_data.append(str(val).strip() if val else "")
            result.append(row_data)
        return result, cols
    except Exception as e:
        print(f"SHEET FETCH ERROR [{sheet_name}]: {e}")
        return [], []

def safe_col(row, idx):
    try:
        return row[idx] if idx < len(row) else ""
    except:
        return ""

# ===================== GOOGLE SHEETS QUERIES =====================

def query_oe_profile(query_text):
    """
    Sheet: OE team profile (Sheet 0)
    Cột A (idx 0)  = Status
    Cột B (idx 1)  = Onboard date
    Cột C (idx 2)  = Rank
    Cột D (idx 3)  = ID (SPXVN...)
    Cột E (idx 4)  = Size
    Cột F (idx 5)  = Full Name  ← TÌM KIẾM TÊN TẠI ĐÂY
    Cột G (idx 6)  = Email
    Cột H (idx 7)  = onboarding plan (link)
    Cột I (idx 8)  = DOB
    Cột J (idx 9)  = YOB
    Cột K (idx 10) = Area
    Cột L (idx 11) = Remark
    """
    rows, _ = fetch_sheet_data(SHEET_OE_PROFILE)
    if not rows:
        print("SHEET PROFILE: no rows returned")
        return None

    q = normalize(query_text)
    print(f"PROFILE QUERY normalized: '{q}' (from: '{query_text}')")
    matches = []

    for row in rows:
        col_f = safe_col(row, 5)   # Full Name
        col_g = safe_col(row, 6)   # Email
        col_c = safe_col(row, 2)   # Rank
        col_k = safe_col(row, 10)  # Area
        col_d = safe_col(row, 3)   # ID

        if not col_f or col_f.strip() == "Full Name":
            continue  # bỏ dòng header

        name_norm = normalize(col_f)
        name_parts = name_norm.split()
        short_name = name_parts[-1] if name_parts else ""
        last_two = " ".join(name_parts[-2:]) if len(name_parts) >= 2 else name_norm

        matched = (
            q == name_norm
            or q == short_name
            or q in name_norm
            or name_norm in q
            or q in last_two
            or (len(q) >= 2 and any(part == q for part in name_parts))
            or (len(q) >= 3 and any(q in part for part in name_parts))
            or (len(q) >= 3 and short_name.startswith(q))
        )

        if matched:
            print(f"  MATCHED: {col_f}")
            matches.append({
                "ten": col_f,
                "email": col_g,
                "rank": col_c,
                "area": col_k,
                "id": col_d,
            })

    if not matches:
        print(f"  No profile match for '{q}'")
        return None

    lines = []
    for m in matches[:5]:
        line = f"👤 {m['ten']}"
        if m['rank']:
            line += f"\n   🏷️ Rank: {m['rank']}"
        if m['email']:
            line += f"\n   📧 {m['email']}"
        if m['area']:
            line += f"\n   📍 Area: {m['area']}"
        if m['id']:
            line += f"\n   🪪 ID: {m['id']}"
        lines.append(line)

    return "📋 Thông tin thành viên OE:\n\n" + "\n\n".join(lines)


def query_task_calendar(query_text):
    """
    Sheet: OE Task Calendar
    Cột E (idx 4) = Tên Task
    Cột H (idx 7) = Tên nhân viên (không dấu)
    """
    rows, _ = fetch_sheet_data(SHEET_TASK_CALENDAR)
    if not rows:
        return None

    q = normalize(query_text)
    matches = []

    for row in rows:
        col_e = safe_col(row, 4)  # Task
        col_h = safe_col(row, 7)  # Tên NV

        if not col_e and not col_h:
            continue

        task_norm = normalize(col_e)
        pic_norm  = normalize(col_h)

        if (q in task_norm or q in pic_norm or
                task_norm in q or pic_norm in q):
            matches.append({"task": col_e, "pic": col_h})

    if not matches:
        return None

    by_pic = {}
    for m in matches:
        pic = m["pic"] or "Chưa phân công"
        by_pic.setdefault(pic, []).append(m["task"])

    lines = []
    for pic, tasks in list(by_pic.items())[:5]:
        task_list = "\n   • ".join(tasks[:10])
        lines.append(f"👷 {pic}\n   • {task_list}")

    return "📅 Task Calendar OE:\n\n" + "\n\n".join(lines)


def query_oe_library(query_text):
    """
    Sheet: OE Library
    Cột C (idx 2) = Tên tài liệu
    Cột E (idx 4) = Link
    """
    rows, _ = fetch_sheet_data(SHEET_OE_LIBRARY)
    if not rows:
        return None

    q = normalize(query_text)
    matches = []

    for row in rows:
        col_c = safe_col(row, 2)
        col_e = safe_col(row, 4)

        if not col_c:
            continue

        name_norm = normalize(col_c)
        if q in name_norm or name_norm in q or any(w in name_norm for w in q.split() if len(w) >= 3):
            matches.append({"ten": col_c, "link": col_e})

    if not matches:
        return None

    lines = []
    for m in matches[:5]:
        line = f"📄 {m['ten']}"
        if m['link']:
            line += f"\n   🔗 {m['link']}"
        lines.append(line)

    return "📚 OE Library - Tài liệu tìm thấy:\n\n" + "\n\n".join(lines)


def query_onboarding(query_text):
    results = []
    for sheet_name, label in [
        (SHEET_ONBOARDING_33, "3.3 Onboarding SOC OE"),
        (SHEET_ONBOARDING_34, "3.4 Onboarding AOM"),
    ]:
        rows, _ = fetch_sheet_data(sheet_name)
        if not rows:
            results.append(f"❌ Không lấy được dữ liệu sheet {label}")
            continue

        lines = []
        for row in rows:
            non_empty = [c for c in row if c.strip()]
            if non_empty:
                lines.append(" | ".join(non_empty))

        if lines:
            preview = "\n".join(lines[:20])
            results.append(f"📋 {label}:\n{preview}")
        else:
            results.append(f"📋 {label}: (Không có dữ liệu)")

    return "\n\n".join(results)


# ===================== INTENT DETECTION =====================

# Danh sách từ dừng để lọc khi phân tích câu ngắn
FILLER_WORDS = {
    "la", "ai", "o", "dau", "the", "nao", "gi", "khong", "co",
    "tim", "hoi", "bot", "cho", "biet", "ve", "cua", "voi",
    "toi", "minh", "ban", "oi", "nhe", "nha", "duoc", "khong"
}

def detect_intent(message_text):
    msg = normalize(message_text)
    print(f"DETECT INTENT for: '{msg}'")

    # --- Onboarding ---
    if any(kw in msg for kw in ["onboar", "onboard", "3.3", "3.4", "nhap mon", "nhan mon"]):
        return "onboarding"
    if re.search(r'\bob\b', msg):
        return "onboarding"

    # --- Library ---
    if any(kw in msg for kw in ["link", "tai lieu", "huong dan", "quy trinh", "library", "thu vien"]):
        return "library"

    # --- Task / PIC ---
    if any(kw in msg for kw in ["task", "cong viec", "pic", "phu trach", "ai lam", "lam gi", "lich", "calendar"]):
        return "task"

    # --- Profile (tường minh) ---
    if any(kw in msg for kw in ["la ai", "ai la", "gioi thieu", "ten la", "thong tin ve",
                                  "email cua", "thanh vien", "nhan vien", "oe team", "team oe"]):
        return "profile"

    # --- Heuristic: câu ngắn → thử profile ---
    # Lọc bỏ filler words, nếu chỉ còn 1-2 từ thực có nghĩa → đây là tên người
    words = msg.strip().split()
    real_words = [w for w in words if w not in FILLER_WORDS and len(w) >= 2]
    print(f"  real_words after filter: {real_words}")
    if 1 <= len(real_words) <= 3:
        return "profile"

    return None


def extract_search_term(message_text, intent):
    msg = message_text.strip()
    stopwords = [
        "cho tôi biết", "cho mình biết", "tìm", "kiếm", "hỏi",
        "ai là", "ai đang", "thông tin về", "thông tin của",
        "task của", "công việc của", "pic của", "phụ trách",
        "link của", "tài liệu về", "tài liệu của",
        "là ai", "ở đâu", "như thế nào", "là gì",
        "cho xin", "cho hỏi", "mình hỏi",
        "oe team", "team oe", "onboarding", "onboard",
        "@", "bot", "khủng long", "khung long",
    ]
    result = msg
    for sw in stopwords:
        result = re.sub(re.escape(sw), "", result, flags=re.IGNORECASE)
    result = result.strip(" ?.,!-")
    if len(result) < 2:
        return msg
    return result


def query_sheets(message_text):
    intent = detect_intent(message_text)
    search_term = extract_search_term(message_text, intent)
    print(f"INTENT: {intent} | SEARCH_TERM: '{search_term}'")

    if intent == "onboarding":
        return query_onboarding(search_term)

    if intent == "library":
        return query_oe_library(search_term) or query_oe_library(message_text)

    if intent == "task":
        return query_task_calendar(search_term) or query_task_calendar(message_text)

    if intent == "profile":
        return (
            query_oe_profile(search_term)
            or query_oe_profile(message_text)
        )

    # Không detect được → thử tuần tự
    return (
        query_oe_profile(search_term)
        or query_task_calendar(search_term)
        or query_oe_library(search_term)
    )


# ===================== COMPANY INFO & AI =====================

COMPANY_INFO = """
Bạn là bot hỗ trợ nội bộ tên "Khủng Long 5 Canh" của OE Team!.
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
- Liên hệ: hr@spxexpress.com

=== SỰ CỐ IT ===
- Email: it-support@spxexpress.com
- Máy tính hỏng, mật khẩu, lỗi hệ thống liên hệ IT

=== THANH TOÁN & CHI PHÍ ===
- Nộp hóa đơn gốc cho phòng kế toán trước ngày 25 hàng tháng

=== NHÂN VẬT NỔI BẬT ===
- Kate: Lead team OE!
- Thọ / Hữu Thọ / Tho / Trương Hữu Thọ / tho.truonghuu@spxexpress.com: Chủ Nhân Của Tôi!

=== VUI VẺ ===
- Nhậu / uống rượu / uống bia: Đô bất tử hahaha!
"""

# CUSTOM_REPLIES: tất cả keyword đều lowercase để khớp với msg.lower()
CUSTOM_REPLIES = [
    {
        # Kate / KATE / Kéc / Kec / Mỹ / My
        "keywords": ["kate", "kec", "kéc", "ngoc my", "ngọc mỹ"],
        "reply": "Chị Kate (Liêu Ngọc Mỹ) — Lead Team OE! 👑\n📧 ngocmy.lieu@spxexpress.com"
    },
    {
        "keywords": ["thọ là ai", "hữu thọ", "trương hữu thọ", "tho.truonghuu", "chủ nhân", "tho la ai"],
        "reply": "Anh Thọ (Trương Hữu Thọ) — Chủ Nhân Của Tôi! 🦖\n📧 tho.truonghuu@spxexpress.com"
    },
    {
        "keywords": ["nhậu", "uống bia", "uống rượu", "nhau"],
        "reply": "Đô bất tử hahaha! 🍺🔥"
    },
]


def get_access_token():
    url = "https://openapi.seatalk.io/auth/app_access_token"
    try:
        r = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=10)
        return r.json().get("app_access_token", "")
    except Exception as e:
        print(f"TOKEN ERROR: {e}")
        return ""

def send_message_direct(employee_code, text):
    token = get_access_token()
    if not token:
        return
    url = "https://openapi.seatalk.io/messaging/v2/single_chat"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "employee_code": str(employee_code),
        "message": {"tag": "text", "text": {"content": text}}
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"SEND DIRECT: {r.status_code} {r.text}")
    except Exception as e:
        print(f"SEND DIRECT ERROR: {e}")

def send_message_group(group_id, text):
    token = get_access_token()
    if not token:
        return
    url = "https://openapi.seatalk.io/messaging/v2/group_chat"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "group_id": str(group_id),
        "message": {"tag": "text", "text": {"content": text}}
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"SEND GROUP: {r.status_code} {r.text}")
    except Exception as e:
        print(f"SEND GROUP ERROR: {e}")

def check_custom_reply(message_text):
    # So sánh lowercase để không bị lỗi hoa/thường
    msg = message_text.lower().strip()
    # Cũng normalize để bắt cả "Kéc" → "kec"
    msg_norm = normalize(message_text)
    for item in CUSTOM_REPLIES:
        for kw in item["keywords"]:
            kw_norm = normalize(kw)
            if kw_norm in msg_norm or kw_norm in msg:
                print(f"CUSTOM REPLY matched: '{kw}'")
                return item["reply"]
    return None

def ask_groq(message_text):
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
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
        if "error" in result:
            return None
        choices = result.get("choices", [])
        if choices:
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
                "contents": [{"role": "user", "parts": [{"text": f"{COMPANY_INFO}\n\nNgười dùng hỏi: {message_text}"}]}],
                "generationConfig": {"maxOutputTokens": 800, "temperature": 0.7}
            }
            r = requests.post(url, headers=headers, json=payload, timeout=30)
            result = r.json()
            if "error" in result:
                continue
            candidates = result.get("candidates", [])
            if candidates:
                return candidates[0]["content"]["parts"][0]["text"]
        except Exception:
            continue
    return None

def fallback_reply(message_text):
    msg = message_text.lower().strip()
    if any(w in msg for w in ["xin chào", "hello", "hi", "chào", "hey"]):
        return "Xin chào! 👋 Tôi là bot Khủng Long 5 Canh của OE Team. Tôi có thể giúp gì cho bạn?"
    elif any(w in msg for w in ["giờ làm việc", "mấy giờ", "làm việc"]):
        return "⏰ Giờ làm việc:\n- Thứ 2 - Thứ 7: 9:00 - 18:00\n- Chủ nhật: Nghỉ\n- Lễ: Nghỉ"
    elif any(w in msg for w in ["nghỉ phép", "xin nghỉ"]):
        return "📋 Xin nghỉ phép:\n1. Báo trước ít nhất 3 ngày\n2. Gửi đơn qua form HR\n3. Chờ quản lý phê duyệt"
    elif any(w in msg for w in ["help", "giúp", "menu"]):
        return (
            "📋 Tôi có thể giúp:\n"
            "- 👤 Thông tin thành viên OE (gõ tên người)\n"
            "- 📅 Task & PIC (hỏi 'task của ai', 'ai phụ trách...')\n"
            "- 📚 Tài liệu & link (hỏi 'link...', 'tài liệu...')\n"
            "- 🎓 Onboarding (hỏi 'OB', 'onboarding', '3.3', '3.4')\n"
            "- ⏰ Giờ làm việc\n"
            "- 📋 Xin nghỉ phép\n"
            "Cứ hỏi tự nhiên nhé! 😊"
        )
    else:
        return "Liên hệ hỗ trợ:\n- THỌ: tho.truonghuu@spxexpress.com"


def get_reply(message_text):
    print(f"\n===== NEW MESSAGE: '{message_text}' =====")

    # 1. Custom reply (hardcoded, ưu tiên cao nhất)
    custom = check_custom_reply(message_text)
    if custom:
        return custom

    # 2. Google Sheets
    sheet_result = query_sheets(message_text)
    if sheet_result:
        return sheet_result

    # 3. AI
    reply = ask_groq(message_text)
    if reply:
        return reply
    reply = ask_gemini(message_text)
    if reply:
        return reply

    # 4. Fallback cứng
    return fallback_reply(message_text)


def extract_group_message(event):
    msg = event.get("message", {})
    text = msg.get("text", {}).get("plain_text", "")
    if not text:
        text = msg.get("text", {}).get("content", "")
    if not text:
        text = msg.get("plain_text", "")
    text = re.sub(r'@[^\s]+\s*', '', text).strip()
    return text


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
        print(f"EVENT_TYPE: {event_type}")

        if event_type == "message_from_bot_subscriber":
            employee_code = event.get("employee_code", "")
            message_text = event.get("message", {}).get("text", {}).get("content", "")
            print(f"DIRECT - EMPLOYEE: {employee_code}, MSG: {message_text}")
            if employee_code and message_text:
                reply = get_reply(message_text)
                send_message_direct(employee_code, reply)

        elif event_type == "new_mentioned_message_received_from_group_chat":
            group_id = event.get("group_id", "")
            sender = event.get("sender", {})
            employee_code = sender.get("employee_code", "")
            message_text = extract_group_message(event)
            print(f"GROUP MENTION - GROUP: {group_id}, EMPLOYEE: {employee_code}, MSG: {message_text}")
            if group_id and message_text:
                reply = get_reply(message_text)
                send_message_group(group_id, reply)

        else:
            print(f"UNHANDLED: {event_type}")

    except Exception as e:
        print(f"ERROR: {e}")

    return json.dumps({"status": "ok"}), 200, {"Content-Type": "application/json"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
