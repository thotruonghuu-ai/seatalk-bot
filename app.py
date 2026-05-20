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
        print(f"FETCHING: {url}")
        r = requests.get(url, timeout=15)
        print(f"FETCH STATUS: {r.status_code} | len={len(r.text)}")
        raw = r.text

        # Kiểm tra lỗi access (sheet chưa public)
        if r.status_code != 200:
            print(f"FETCH ERROR: HTTP {r.status_code}")
            return [], []
        if "Invalid credentials" in raw or "PERMISSION_DENIED" in raw or "You need access" in raw:
            print(f"FETCH ERROR: Sheet chưa được chia sẻ công khai!")
            return [], []

        # Tách JSON khỏi JSONP callback: google.visualization.Query.setResponse({...})
        # Tìm từ dấu { đầu tiên đến } cuối cùng
        start = raw.index('{')
        end = raw.rindex('}') + 1
        raw_json = raw[start:end]
        data = json.loads(raw_json)

        # Kiểm tra lỗi trong JSON
        if data.get("status") == "error":
            errs = data.get("errors", [])
            print(f"SHEET JSON ERROR: {errs}")
            return [], []

        rows = data.get("table", {}).get("rows", [])
        cols = data.get("table", {}).get("cols", [])
        print(f"SHEET [{sheet_name}]: {len(rows)} rows, {len(cols)} cols")

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

        # Debug: in 3 dòng đầu để kiểm tra
        for i, r2 in enumerate(result[:3]):
            print(f"  row[{i}]: {r2[:8]}")

        return result, cols

    except Exception as e:
        print(f"SHEET FETCH EXCEPTION [{sheet_name}]: {e}")
        import traceback; traceback.print_exc()
        return [], []

def safe_col(row, idx):
    try:
        return row[idx] if idx < len(row) else ""
    except:
        return ""

# ===================== GOOGLE SHEETS QUERIES =====================

def query_oe_profile(query_text):
    """
    Sheet: OE team profile
    Cột F (idx 5)  = Full Name  ← TÌM KIẾM
    Cột G (idx 6)  = Email
    Cột C (idx 2)  = Rank
    Cột K (idx 10) = Area
    Cột D (idx 3)  = ID
    """
    rows, _ = fetch_sheet_data(SHEET_OE_PROFILE)
    if not rows:
        print("PROFILE: no rows returned — sheet có thể chưa public!")
        return None

    q = normalize(query_text)
    print(f"PROFILE SEARCH: '{q}'")
    matches = []

    for i, row in enumerate(rows):
        col_f = safe_col(row, 5)   # Full Name
        col_g = safe_col(row, 6)   # Email
        col_c = safe_col(row, 2)   # Rank
        col_k = safe_col(row, 10)  # Area
        col_d = safe_col(row, 3)   # ID

        # Bỏ dòng trống hoặc dòng header
        if not col_f or normalize(col_f) in ("full name", "fullname", "ten", "name", "họ và tên"):
            continue

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
            print(f"  MATCH row[{i}]: '{col_f}'")
            matches.append({"ten": col_f, "email": col_g, "rank": col_c, "area": col_k, "id": col_d})

    if not matches:
        print(f"  No match for '{q}' in {len(rows)} rows")
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
    rows, _ = fetch_sheet_data(SHEET_TASK_CALENDAR)
    if not rows:
        return None
    q = normalize(query_text)
    matches = []
    for row in rows:
        col_e = safe_col(row, 4)
        col_h = safe_col(row, 7)
        if not col_e and not col_h:
            continue
        if q in normalize(col_e) or q in normalize(col_h) or normalize(col_e) in q or normalize(col_h) in q:
            matches.append({"task": col_e, "pic": col_h})
    if not matches:
        return None
    by_pic = {}
    for m in matches:
        by_pic.setdefault(m["pic"] or "Chưa phân công", []).append(m["task"])
    lines = [f"👷 {pic}\n   • " + "\n   • ".join(tasks[:10]) for pic, tasks in list(by_pic.items())[:5]]
    return "📅 Task Calendar OE:\n\n" + "\n\n".join(lines)


def query_oe_library(query_text):
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
    lines = [f"📄 {m['ten']}" + (f"\n   🔗 {m['link']}" if m['link'] else "") for m in matches[:5]]
    return "📚 OE Library:\n\n" + "\n\n".join(lines)


def query_onboarding(query_text):
    results = []
    for sheet_name, label in [(SHEET_ONBOARDING_33, "3.3 Onboarding SOC OE"), (SHEET_ONBOARDING_34, "3.4 Onboarding AOM")]:
        rows, _ = fetch_sheet_data(sheet_name)
        if not rows:
            results.append(f"❌ Không lấy được dữ liệu sheet {label}")
            continue
        lines = [" | ".join(c for c in row if c.strip()) for row in rows if any(c.strip() for c in row)]
        preview = "\n".join(lines[:20])
        results.append(f"📋 {label}:\n{preview}" if lines else f"📋 {label}: (Không có dữ liệu)")
    return "\n\n".join(results)


# ===================== INTENT DETECTION =====================

FILLER_WORDS = {
    "la", "ai", "o", "dau", "the", "nao", "gi", "khong", "co",
    "tim", "hoi", "bot", "cho", "biet", "ve", "cua", "voi",
    "toi", "minh", "ban", "oi", "nhe", "nha", "duoc"
}

def detect_intent(message_text):
    msg = normalize(message_text)
    print(f"DETECT INTENT: '{msg}'")

    if any(kw in msg for kw in ["onboar", "onboard", "3.3", "3.4", "nhap mon"]):
        return "onboarding"
    if re.search(r'\bob\b', msg):
        return "onboarding"
    if any(kw in msg for kw in ["link", "tai lieu", "huong dan", "quy trinh", "library", "thu vien"]):
        return "library"
    if any(kw in msg for kw in ["task", "cong viec", "pic", "phu trach", "ai lam", "lam gi", "lich", "calendar"]):
        return "task"
    if any(kw in msg for kw in ["la ai", "ai la", "gioi thieu", "thong tin ve", "email cua", "thanh vien", "nhan vien", "oe team", "team oe"]):
        return "profile"

    # Heuristic: câu ngắn → thử profile
    words = msg.strip().split()
    real_words = [w for w in words if w not in FILLER_WORDS and len(w) >= 2]
    print(f"  real_words: {real_words}")
    if 1 <= len(real_words) <= 3:
        return "profile"

    return None


def extract_search_term(message_text, intent):
    msg = message_text.strip()
    stopwords = [
        "cho tôi biết", "cho mình biết", "tìm kiếm", "tìm", "kiếm", "hỏi",
        "ai là", "ai đang", "thông tin về", "thông tin của",
        "task của", "công việc của", "pic của", "phụ trách",
        "link của", "tài liệu về", "tài liệu của",
        "là ai", "là gì", "ở đâu", "như thế nào",
        "cho xin", "cho hỏi", "mình hỏi",
        "oe team", "team oe", "onboarding", "onboard",
        "@khủng long", "@khung long", "bot",
    ]
    result = msg
    for sw in stopwords:
        result = re.sub(re.escape(sw), "", result, flags=re.IGNORECASE)
    result = result.strip(" ?.,!-")
    return result if len(result) >= 2 else msg


def query_sheets(message_text):
    intent = detect_intent(message_text)
    search_term = extract_search_term(message_text, intent)
    print(f"INTENT={intent} | SEARCH='{search_term}'")

    if intent == "onboarding":
        return query_onboarding(search_term)
    if intent == "library":
        return query_oe_library(search_term) or query_oe_library(message_text)
    if intent == "task":
        return query_task_calendar(search_term) or query_task_calendar(message_text)
    if intent == "profile":
        return query_oe_profile(search_term) or query_oe_profile(message_text)

    # Không rõ intent → thử tuần tự
    return (query_oe_profile(search_term)
            or query_task_calendar(search_term)
            or query_oe_library(search_term))


# ===================== DEBUG ENDPOINT =====================

@app.route("/debug/sheet", methods=["GET"])
def debug_sheet():
    """
    Test trực tiếp: /debug/sheet?q=Quý
    Trả về raw JSON để debug
    """
    q = request.args.get("q", "test")
    rows, cols = fetch_sheet_data(SHEET_OE_PROFILE)
    if not rows:
        return json.dumps({"error": "Không lấy được dữ liệu. Sheet chưa public hoặc tên sheet sai.", "rows": 0}, ensure_ascii=False), 200
    
    # Tìm theo query
    q_norm = normalize(q)
    matches = []
    sample = []
    for i, row in enumerate(rows[:5]):
        sample.append({"row": i, "col_F_idx5": safe_col(row, 5), "col_G_idx6": safe_col(row, 6)})
    
    for row in rows:
        col_f = safe_col(row, 5)
        if col_f and q_norm in normalize(col_f):
            matches.append({"name": col_f, "email": safe_col(row, 6), "rank": safe_col(row, 2)})
    
    return json.dumps({
        "total_rows": len(rows),
        "total_cols": len(cols),
        "query": q,
        "matches": matches,
        "sample_rows_0_to_4": sample
    }, ensure_ascii=False, indent=2), 200, {"Content-Type": "application/json"}


# ===================== COMPANY INFO & AI =====================

COMPANY_INFO = """
Bạn là bot hỗ trợ nội bộ tên "Khủng Long 5 Canh" của OE Team!
Hãy trả lời ngắn gọn, thân thiện, chuyên nghiệp bằng tiếng Việt.
Nếu không biết, hãy nói: "Tôi chưa có thông tin này, vui lòng liên hệ HR hoặc IT."

=== THÔNG TIN CÔNG TY ===
- Tên công ty: SPX Express
- Email IT: it-support@spxexpress.com
- Email HR: hr@spxexpress.com

=== GIỜ LÀM VIỆC ===
- Thứ 2 - Thứ 6: 8:00 - 17:30 | Thứ 7: 8:00 - 12:00 | Chủ nhật: Nghỉ

=== QUY TRÌNH XIN NGHỈ PHÉP ===
- Báo trước ít nhất 3 ngày | Gửi đơn qua form HR | Chờ quản lý phê duyệt

=== NHÂN VẬT NỔI BẬT ===
- Kate (Liêu Ngọc Mỹ): Lead team OE! ngocmy.lieu@spxexpress.com
- Thọ (Trương Hữu Thọ): Chủ Nhân Của Tôi! tho.truonghuu@spxexpress.com

=== VUI VẺ ===
- Nhậu / uống bia: Đô bất tử hahaha!
"""

CUSTOM_REPLIES = [
    {
        "keywords": ["kate", "kec", "kéc", "ngoc my", "ngọc mỹ", "lieu ngoc my", "liêu ngọc mỹ"],
        "reply": "Chị Kate (Liêu Ngọc Mỹ) — Lead Team OE! 👑\n📧 ngocmy.lieu@spxexpress.com"
    },
    {
        "keywords": ["thọ", "huu tho", "hữu thọ", "truong huu tho", "trương hữu thọ", "tho.truonghuu", "chu nhan", "chủ nhân"],
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
    payload = {"employee_code": str(employee_code), "message": {"tag": "text", "text": {"content": text}}}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"SEND DIRECT: {r.status_code}")
    except Exception as e:
        print(f"SEND DIRECT ERROR: {e}")

def send_message_group(group_id, text):
    token = get_access_token()
    if not token:
        return
    url = "https://openapi.seatalk.io/messaging/v2/group_chat"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"group_id": str(group_id), "message": {"tag": "text", "text": {"content": text}}}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"SEND GROUP: {r.status_code}")
    except Exception as e:
        print(f"SEND GROUP ERROR: {e}")

def check_custom_reply(message_text):
    msg_norm = normalize(message_text)
    for item in CUSTOM_REPLIES:
        for kw in item["keywords"]:
            if normalize(kw) in msg_norm:
                print(f"CUSTOM REPLY matched: '{kw}'")
                return item["reply"]
    return None

def ask_groq(message_text):
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "llama3-8b-8192",
            "messages": [{"role": "system", "content": COMPANY_INFO}, {"role": "user", "content": message_text}],
            "max_tokens": 800, "temperature": 0.7
        }
        r = requests.post(url, headers=headers, json=payload, timeout=30)
        result = r.json()
        if "error" in result:
            return None
        choices = result.get("choices", [])
        return choices[0]["message"]["content"] if choices else None
    except Exception as e:
        print(f"GROQ EXCEPTION: {e}")
        return None

def ask_gemini(message_text):
    for model in ["gemini-2.0-flash-lite", "gemini-2.0-flash-exp", "gemini-1.0-pro"]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "contents": [{"role": "user", "parts": [{"text": f"{COMPANY_INFO}\n\nNgười dùng hỏi: {message_text}"}]}],
                "generationConfig": {"maxOutputTokens": 800, "temperature": 0.7}
            }
            r = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=30)
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
        return "⏰ Giờ làm việc:\n- Thứ 2 - Thứ 7: 9:00 - 18:00\n- Chủ nhật & Lễ: Nghỉ"
    elif any(w in msg for w in ["nghỉ phép", "xin nghỉ"]):
        return "📋 Xin nghỉ phép:\n1. Báo trước ít nhất 3 ngày\n2. Gửi đơn qua form HR\n3. Chờ quản lý phê duyệt"
    elif any(w in msg for w in ["help", "giúp", "menu"]):
        return (
            "📋 Tôi có thể giúp:\n"
            "- 👤 Thông tin thành viên OE (gõ tên người)\n"
            "- 📅 Task & PIC ('task của ai', 'ai phụ trách...')\n"
            "- 📚 Tài liệu & link ('link...', 'tài liệu...')\n"
            "- 🎓 Onboarding ('OB', 'onboarding', '3.3', '3.4')\n"
            "Cứ hỏi tự nhiên nhé! 😊"
        )
    else:
        return "Liên hệ hỗ trợ:\n- THỌ: tho.truonghuu@spxexpress.com"


def get_reply(message_text):
    print(f"\n===== MSG: '{message_text}' =====")

    # 1. Custom reply
    custom = check_custom_reply(message_text)
    if custom:
        return custom

    # 2. Google Sheets
    sheet_result = query_sheets(message_text)
    if sheet_result:
        return sheet_result

    # 3. AI
    reply = ask_groq(message_text) or ask_gemini(message_text)
    if reply:
        return reply

    return fallback_reply(message_text)


def extract_group_message(event):
    msg = event.get("message", {})
    text = msg.get("text", {}).get("plain_text", "") or msg.get("text", {}).get("content", "") or msg.get("plain_text", "")
    return re.sub(r'@[^\s]+\s*', '', text).strip()


@app.route("/", methods=["GET"])
def home():
    return "Khung Long 5 Canh Bot dang chay!", 200

@app.route("/webhook/seatalk", methods=["GET"])
def webhook_get():
    return json.dumps({"status": "ok"}), 200, {"Content-Type": "application/json"}

@app.route("/webhook/seatalk", methods=["POST"])
def webhook_post():
    try:
        data = json.loads(request.data)
        event = data.get("event", {})

        if "seatalk_challenge" in event:
            return json.dumps({"seatalk_challenge": event["seatalk_challenge"]}), 200, {"Content-Type": "application/json"}
        if "seatalk_challenge" in data:
            return json.dumps({"seatalk_challenge": data["seatalk_challenge"]}), 200, {"Content-Type": "application/json"}

        event_type = data.get("event_type", "")
        print(f"EVENT_TYPE: {event_type}")

        if event_type == "message_from_bot_subscriber":
            employee_code = event.get("employee_code", "")
            message_text = event.get("message", {}).get("text", {}).get("content", "")
            print(f"DIRECT: employee={employee_code} msg='{message_text}'")
            if employee_code and message_text:
                send_message_direct(employee_code, get_reply(message_text))

        elif event_type == "new_mentioned_message_received_from_group_chat":
            group_id = event.get("group_id", "")
            message_text = extract_group_message(event)
            print(f"GROUP: group={group_id} msg='{message_text}'")
            if group_id and message_text:
                send_message_group(group_id, get_reply(message_text))
        else:
            print(f"UNHANDLED: {event_type}")

    except Exception as e:
        print(f"WEBHOOK ERROR: {e}")
        import traceback; traceback.print_exc()

    return json.dumps({"status": "ok"}), 200, {"Content-Type": "application/json"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
