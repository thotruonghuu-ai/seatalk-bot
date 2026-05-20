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

# ===================== UTILS =====================
def remove_accents(text):
    if not text:
        return ""
    nfkd = unicodedata.normalize('NFKD', str(text))
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower().strip()

def normalize(text):
    return remove_accents(text)

# ===================== HARDCODED DATA =====================

# OE Team Profile
# Mỗi entry: id, name (đầy đủ có dấu), email, phone, area, yob
OE_TEAM = [
    {"id": "SPXVN22306", "name": "Liêu Ngọc Mỹ (Kate)", "email": "ngocmy.lieu@spxexpress.com",       "phone": "0971546606", "area": "HCM", "yob": "1991"},
    {"id": "SPXVN15214", "name": "Đoàn Như Huynh",       "email": "huynh.doannhu@spxexpress.com",    "phone": "0974203749", "area": "HCM", "yob": "2000"},
    {"id": "SPXVN21848", "name": "Nguyễn Ngọc Quý",      "email": "ngocquy.nguyen02@spxexpress.com", "phone": "0972683928", "area": "HCM", "yob": "1994"},
    {"id": "SPXVN22647", "name": "Hồ Tấn Thi",           "email": "tanthi.ho@spxexpress.com",        "phone": "0906771620", "area": "HCM", "yob": "1994"},
    {"id": "SPXVN2743",  "name": "Trần Minh Phụng",      "email": "phung.tranminh@spxexpress.com",   "phone": "0367198739", "area": "SW",  "yob": "1996"},
    {"id": "SPXVN22621", "name": "Nguyễn Thiên Long",    "email": "thienlong.nguyen@spxexpress.com", "phone": "0989486334", "area": "HCM", "yob": "1992"},
    {"id": "SPXVN21922", "name": "Trần Thị Thiên Trang", "email": "thientrang.tranthi@spxexpress.com","phone": "0388892148", "area": "HCM", "yob": "1992"},
    {"id": "SPXVN24339", "name": "Bùi Nhựt Linh",        "email": "nhutlinh.bui@spxexpress.com",     "phone": "0981986989", "area": "HCM", "yob": "1998"},
    {"id": "SPXVN14781", "name": "Trương Hữu Thọ",       "email": "tho.truonghuu@spxexpress.com",    "phone": "",           "area": "SW",  "yob": "1990"},
]

# Alias bổ sung để tìm kiếm (nickname / không dấu / viết tắt)
OE_ALIASES = {
    "kate":          "Liêu Ngọc Mỹ (Kate)",
    "lieu ngoc my":  "Liêu Ngọc Mỹ (Kate)",
    "ngoc my":       "Liêu Ngọc Mỹ (Kate)",
    "my":            "Liêu Ngọc Mỹ (Kate)",
    "kec":           "Liêu Ngọc Mỹ (Kate)",
    "kéc":           "Liêu Ngọc Mỹ (Kate)",
    "huynh":         "Đoàn Như Huynh",
    "doan nhu huynh":"Đoàn Như Huynh",
    "nhu huynh":     "Đoàn Như Huynh",
    "quy":           "Nguyễn Ngọc Quý",
    "nguyen ngoc quy":"Nguyễn Ngọc Quý",
    "ngoc quy":      "Nguyễn Ngọc Quý",
    "thi":           "Hồ Tấn Thi",
    "tan thi":       "Hồ Tấn Thi",
    "ho tan thi":    "Hồ Tấn Thi",
    "phung":         "Trần Minh Phụng",
    "minh phung":    "Trần Minh Phụng",
    "tran minh phung":"Trần Minh Phụng",
    "long":          "Nguyễn Thiên Long",
    "thien long":    "Nguyễn Thiên Long",
    "nguyen thien long":"Nguyễn Thiên Long",
    "trang":         "Trần Thị Thiên Trang",
    "thien trang":   "Trần Thị Thiên Trang",
    "tran thi thien trang":"Trần Thị Thiên Trang",
    "linh":          "Bùi Nhựt Linh",
    "nhut linh":     "Bùi Nhựt Linh",
    "bui nhut linh": "Bùi Nhựt Linh",
    "tho":           "Trương Hữu Thọ",
    "huu tho":       "Trương Hữu Thọ",
    "truong huu tho":"Trương Hữu Thọ",
}

# OE Library — Topic/Name | PIC | Docs
OE_LIBRARY = [
    {"topic": "AOM onboarding plan",                          "pic": "Kate",               "doc": "Operations Efficiency Team Information"},
    {"topic": "Backlogs & Compliance",                        "pic": "Nguyen Ngoc Quy",    "doc": "[South] Risk & Compliance - Sharing"},
    {"topic": "Công tác Phí",                                 "pic": "Thi Tấn",            "doc": "Chính sách Công tác // Travel Policy_09.2025"},
    {"topic": "FLM OE Onboarding plan",                       "pic": "Kate",               "doc": "Operations Efficiency Team Information"},
    {"topic": "KPI & Systems & Dashboard",                    "pic": "Doan Nhu Huynh",     "doc": "[South_Huynh OE]_OE Sharing SoW"},
    {"topic": "Network Expansion & Facilities & Assets",      "pic": "Nguyen Thien Long",  "doc": "[South] Network Expansion & Facilities & Assets (Onboarding AOM-SUP).pptx"},
    {"topic": "Performance & Truck plan",                     "pic": "Thi Tấn",            "doc": "[SOUTH] Tracker high risk Hub"},
    {"topic": "SOC OE Onboarding plan",                       "pic": "Kate",               "doc": "Operations Efficiency Team Information"},
    {"topic": "Workforce Management",                         "pic": "Tran Thi Thien Trang","doc": "Workforce Planning & Management"},
    {"topic": "Headcount Plan",                               "pic": "Tran Thi Thien Trang","doc": "Workforce Planning & Management - Headcount Plan"},
    {"topic": "OE Recap meeting",                             "pic": "Kate",               "doc": "OE Recap meeting 2026"},
    {"topic": "Project South_Master Tracker",                 "pic": "Kate",               "doc": "South | Master Project Tracker 2026"},
    {"topic": "Weekly Management Meeting Ops",                "pic": "Kate",               "doc": "South Management Weekly Meeting"},
    {"topic": "Rider backlogs support (Rider FLC/PT/Support)","pic": "Thi Tấn",           "doc": "[All Regions] Rider support scheme proposal"},
    {"topic": "Network & COT",                                "pic": "Tran Minh Phung",    "doc": "[Public] SPX Network | SPX COT Align"},
    {"topic": "SW SOC Headcounts",                            "pic": "Tran Minh Phung",    "doc": "[HC Request] SW SOC"},
    {"topic": "SW SOC KPI Performance",                       "pic": "Tran Minh Phung",    "doc": "Performance"},
    {"topic": "SW SOC ASM config",                            "pic": "Tran Minh Phung",    "doc": "5. SW SOC - Layout/Logic Config ASM"},
    {"topic": "SW SOC ASM performance",                       "pic": "Tran Minh Phung",    "doc": "Daily cap - SW SOC"},
]

# OE Task Calendar — detail | eta | pic (có thể nhiều người, ngăn cách \n)
OE_TASKS = [
    {"detail": "(BAU) Issue sai tuyến - check vs project team correct các tuyến thay đổi địa giới hành chính",
     "eta": "ASAP",    "pic": "Nguyen Thien Long\nDoan Nhu Huynh"},
    {"detail": "(BAU) Review các tuyến COT 2 Ops planning",
     "eta": "08-May",  "pic": "Doan Nhu Huynh"},
    {"detail": "(BAU) get approval write-off South Sep 2025 -> Mar 2026",
     "eta": "15-May",  "pic": "Nguyen Ngoc Quy"},
    {"detail": "(BAU) Training về quy trình xử lý sự vụ cho sup/lead định kỳ",
     "eta": "",        "pic": "Nguyen Ngoc Quy"},
    {"detail": "(BAU) Expansion plan South hub network - ETA H1/2026",
     "eta": "",        "pic": "Nguyen Thien Long"},
    {"detail": "(All) Appraisal mid year - team submit",
     "eta": "18-May",  "pic": "All"},
    {"detail": "Quản lý đánh giá",
     "eta": "01-Jun",  "pic": "Kate [SPX]"},
    {"detail": "Đối thoại team",
     "eta": "22-Jun",  "pic": "Kate [SPX]"},
    {"detail": "(CI) Review & restructure cost cho south budget",
     "eta": "",        "pic": "Kate [SPX]\nThi Tấn"},
    {"detail": "Form logic cost structure",
     "eta": "12-May",  "pic": "Thi Tấn\nBui Nhut Linh"},
    {"detail": "Review & align framework",
     "eta": "12-May",  "pic": "Kate [SPX]\nThi Tấn\nBui Nhut Linh"},
    {"detail": "Align vs Ops & get approval from ROM",
     "eta": "30-May",  "pic": "Thi Tấn"},
    {"detail": "handover BAU",
     "eta": "",        "pic": "Thi Tấn\nBui Nhut Linh"},
    {"detail": "(CI) Define SPX Ops_ HC SUP/AOM 2026",
     "eta": "05-May",  "pic": "Tran Thi Thien Trang"},
    {"detail": "(CI) Revamp template weekly meeting zone",
     "eta": "01-Jun",  "pic": "Bui Nhut Linh\nThi Tấn"},
    {"detail": "18.05: 1st draft proposal",
     "eta": "19-May",  "pic": "Bui Nhut Linh\nThi Tấn"},
    {"detail": "reschedule all meeting & training all zone",
     "eta": "22-May",  "pic": "Thi Tấn"},
    {"detail": "01.06: sign-off & release",
     "eta": "01-Jun",  "pic": "Bui Nhut Linh"},
    {"detail": "(CI) Review current hub network - audit data",
     "eta": "",        "pic": "Nguyen Thien Long"},
    {"detail": "(CI) WFP - Review logic input HC & OT từ đầu OE",
     "eta": "",        "pic": "Tran Thi Thien Trang"},
    {"detail": "(CI) handover logic report & data Huynh -> Dan Thi",
     "eta": "",        "pic": "Doan Nhu Huynh"},
    {"detail": "(CI) SW SOC improvement",
     "eta": "",        "pic": "Tran Minh Phung"},
    {"detail": "(CI) checklist audit hub compliance",
     "eta": "31-May",  "pic": "Nguyen Ngoc Quy"},
    {"detail": "(CI) Report FC purchasing",
     "eta": "01-Jun",  "pic": "Nguyen Thien Long"},
    {"detail": "(CI) Review flow đối soát hàng FLM hub & SOC & TS",
     "eta": "",        "pic": "Nguyen Viet Huyen Tran\nNguyen Ngoc Quy\nTruong Huu Tho"},
    {"detail": "(Kate) New OE structure",
     "eta": "",        "pic": "Kate [SPX]"},
    {"detail": "(project) Centralize backlogs & logs SOC -> move về SW SOC",
     "eta": "01-Jul",  "pic": "Kate [SPX]\nTran Minh Phung\nNguyen Viet Huyen Tran"},
    {"detail": "Book kick-off clear scope vs SWSOC & BDSOC",
     "eta": "22-May",  "pic": "Tran Minh Phung"},
    {"detail": "Draft scope & define RACI cho team Lost & Backlogs",
     "eta": "30-May",  "pic": "Kate [SPX]"},
    {"detail": "Transition plan & handover BAU",
     "eta": "30-Jun",  "pic": "Tran Minh Phung"},
    {"detail": "SOP & Alignment for Ops",
     "eta": "15-Jun",  "pic": "Nguyen Viet Huyen Tran"},
    {"detail": "(project) chuẩn hóa layout hub toàn south",
     "eta": "01-Jun",  "pic": "Nguyen Thien Long"},
    {"detail": "(project) Update google site flow quy trình chung của toàn south",
     "eta": "",        "pic": "pending PIC"},
    {"detail": "(project) material training newbie (OE/ AOM)",
     "eta": "",        "pic": "-"},
    {"detail": "(project) SWAT",
     "eta": "",        "pic": "Nguyen Ngoc Quy"},
    {"detail": "Problematic hub framework project",
     "eta": "",        "pic": "Nguyen Ngoc Quy"},
]

# ===================== QUERY FUNCTIONS =====================

def query_oe_profile(query_text):
    """Tìm thành viên OE theo tên (có dấu/không dấu/nickname/tên ngắn)"""
    q = normalize(query_text)
    print(f"PROFILE SEARCH: '{q}'")

    # 1. Tìm qua alias trước (chính xác nhất)
    target_name = None
    for alias_norm, full_name in OE_ALIASES.items():
        if q == normalize(alias_norm) or normalize(alias_norm) in q:
            target_name = full_name
            print(f"  ALIAS match: '{alias_norm}' -> '{full_name}'")
            break

    # 2. Nếu không có alias, tìm trực tiếp trong danh sách
    matches = []
    for member in OE_TEAM:
        name_norm = normalize(member["name"])
        name_parts = name_norm.split()
        short_name = name_parts[-1] if name_parts else ""

        if target_name:
            if member["name"] == target_name:
                matches.append(member)
        else:
            matched = (
                q == name_norm
                or q == short_name
                or q in name_norm
                or (len(q) >= 2 and any(p == q for p in name_parts))
                or (len(q) >= 3 and any(q in p for p in name_parts))
            )
            if matched:
                print(f"  DIRECT match: '{member['name']}'")
                matches.append(member)

    if not matches:
        print(f"  No profile match for '{q}'")
        return None

    lines = []
    for m in matches[:5]:
        line = f"👤 {m['name']}"
        line += f"\n   📧 {m['email']}"
        if m['phone']:
            line += f"\n   📱 {m['phone']}"
        line += f"\n   📍 Area: {m['area']}  |  🎂 YOB: {m['yob']}"
        line += f"\n   🪪 ID: {m['id']}"
        lines.append(line)

    return "📋 Thông tin thành viên OE:\n\n" + "\n\n".join(lines)


def query_task_by_pic(query_text):
    """Tìm task theo tên PIC"""
    q = normalize(query_text)
    matches = []
    for task in OE_TASKS:
        pic_norm = normalize(task["pic"])
        detail_norm = normalize(task["detail"])
        if q in pic_norm or q in detail_norm or pic_norm in q:
            matches.append(task)
    return matches


def query_tasks(query_text):
    """Trả về task theo PIC hoặc từ khóa công việc"""
    q = normalize(query_text)
    matches = query_task_by_pic(query_text)

    if not matches:
        return None

    # Nhóm theo PIC
    by_pic = {}
    for t in matches:
        for pic_line in t["pic"].split("\n"):
            pic_line = pic_line.strip()
            if pic_line:
                by_pic.setdefault(pic_line, []).append(
                    f"{t['detail']}" + (f" [{t['eta']}]" if t['eta'] else "")
                )

    lines = []
    for pic, tasks in list(by_pic.items())[:6]:
        task_list = "\n   • ".join(tasks[:8])
        lines.append(f"👷 {pic}\n   • {task_list}")

    return "📅 Task Calendar OE:\n\n" + "\n\n".join(lines)


def query_library(query_text):
    """Tìm tài liệu/link theo topic hoặc tên"""
    q = normalize(query_text)
    matches = []
    for item in OE_LIBRARY:
        topic_norm = normalize(item["topic"])
        pic_norm   = normalize(item["pic"])
        doc_norm   = normalize(item["doc"])
        # Khớp nếu query nằm trong topic, hoặc bất kỳ từ >= 3 ký tự nào của query nằm trong topic
        words_q = [w for w in q.split() if len(w) >= 3]
        matched = (
            q in topic_norm
            or topic_norm in q
            or q in pic_norm
            or q in doc_norm
            or any(w in topic_norm for w in words_q)
            or any(w in doc_norm   for w in words_q)
        )
        if matched:
            matches.append(item)

    if not matches:
        return None

    lines = []
    for m in matches[:6]:
        line = f"📄 {m['topic']}"
        line += f"\n   👤 PIC: {m['pic']}"
        line += f"\n   📎 {m['doc']}"
        lines.append(line)

    return "📚 OE Library:\n\n" + "\n\n".join(lines)


def query_onboarding_info():
    """Trả về thông tin onboarding nhanh từ library"""
    ob_topics = [i for i in OE_LIBRARY if "onboard" in normalize(i["topic"])]
    if not ob_topics:
        return "Vui lòng liên hệ Kate hoặc hỏi 'OE Library' để xem danh sách tài liệu."
    lines = []
    for m in ob_topics:
        lines.append(f"📄 {m['topic']}\n   👤 PIC: {m['pic']}\n   📎 {m['doc']}")
    return "🎓 Onboarding OE:\n\n" + "\n\n".join(lines)


def query_all_team():
    """Liệt kê toàn bộ team"""
    lines = []
    for m in OE_TEAM:
        lines.append(f"👤 {m['name']} | 📧 {m['email']} | 📍 {m['area']}")
    return "📋 Danh sách Team OE:\n\n" + "\n".join(lines)


# ===================== INTENT DETECTION =====================

FILLER_WORDS = {
    "la", "ai", "o", "dau", "the", "nao", "gi", "khong", "co",
    "tim", "hoi", "bot", "cho", "biet", "ve", "cua", "voi",
    "toi", "minh", "ban", "oi", "nhe", "nha", "duoc", "va"
}

def detect_intent(message_text):
    msg = normalize(message_text)
    print(f"INTENT CHECK: '{msg}'")

    if any(kw in msg for kw in ["onboar", "onboard", "3.3", "3.4", "nhap mon"]):
        return "onboarding"
    if re.search(r'\bob\b', msg):
        return "onboarding"

    if any(kw in msg for kw in ["danh sach", "tat ca", "toan bo team", "list team", "team oe", "oe team"]):
        return "list_team"

    if any(kw in msg for kw in ["tai lieu", "link", "huong dan", "quy trinh", "library", "thu vien", "doc", "sow", "tracker"]):
        return "library"

    if any(kw in msg for kw in ["task", "cong viec", "pic", "phu trach", "ai lam", "lam gi", "lich", "calendar", "project", "eta"]):
        return "task"

    if any(kw in msg for kw in ["la ai", "ai la", "gioi thieu", "thong tin ve", "email", "sdt", "phone",
                                  "so dien thoai", "thanh vien", "nhan vien"]):
        return "profile"

    # Heuristic câu ngắn → thử profile
    words = msg.strip().split()
    real_words = [w for w in words if w not in FILLER_WORDS and len(w) >= 2]
    print(f"  real_words: {real_words}")
    if 1 <= len(real_words) <= 3:
        return "profile"

    return None


def extract_search_term(message_text):
    msg = message_text.strip()
    stopwords = [
        "cho tôi biết", "cho mình biết", "tìm kiếm", "tìm", "kiếm", "hỏi",
        "ai là", "ai đang", "thông tin về", "thông tin của",
        "task của", "công việc của", "pic của", "phụ trách bởi",
        "link của", "tài liệu về", "tài liệu của",
        "là ai", "là gì", "ở đâu", "như thế nào",
        "cho xin", "cho hỏi", "mình hỏi",
        "oe team", "team oe", "onboarding", "onboard",
        "@khủng long", "@khung long", "khủng long", "bot",
    ]
    result = msg
    for sw in stopwords:
        result = re.sub(re.escape(sw), "", result, flags=re.IGNORECASE)
    result = result.strip(" ?.,!-")
    return result if len(result) >= 2 else msg


def query_data(message_text):
    intent = detect_intent(message_text)
    search = extract_search_term(message_text)
    print(f"INTENT={intent} | SEARCH='{search}'")

    if intent == "onboarding":
        return query_onboarding_info()
    if intent == "list_team":
        return query_all_team()
    if intent == "library":
        return query_library(search) or query_library(message_text)
    if intent == "task":
        return query_tasks(search) or query_tasks(message_text)
    if intent == "profile":
        return query_oe_profile(search) or query_oe_profile(message_text)

    # Không rõ → thử tuần tự
    return (
        query_oe_profile(search)
        or query_tasks(search)
        or query_library(search)
    )


# ===================== COMPANY INFO & AI =====================

COMPANY_INFO = """
Bạn là bot hỗ trợ nội bộ tên "Khủng Long 5 Canh" của OE Team - SPX Express.
Hãy trả lời ngắn gọn, thân thiện, chuyên nghiệp bằng tiếng Việt.
Nếu không biết, hãy nói: "Tôi chưa có thông tin này, vui lòng liên hệ Kate hoặc Thọ."

=== THÔNG TIN CÔNG TY ===
- Tên công ty: SPX Express - OE Team South
- Email IT: it-support@spxexpress.com | HR: hr@spxexpress.com

=== GIỜ LÀM VIỆC ===
- Thứ 2 - Thứ 6: 8:00 - 17:30 | Thứ 7: 8:00 - 12:00 | Chủ nhật: Nghỉ

=== QUY TRÌNH XIN NGHỈ PHÉP ===
- Báo trước ít nhất 3 ngày | Gửi đơn qua form HR | Chờ quản lý phê duyệt

=== NHÂN VẬT OE TEAM ===
- Kate (Liêu Ngọc Mỹ): Lead Team OE - ngocmy.lieu@spxexpress.com - 0971546606
- Thọ (Trương Hữu Thọ): Chủ Nhân Của Tôi - tho.truonghuu@spxexpress.com
- Quý (Nguyễn Ngọc Quý): ngocquy.nguyen02@spxexpress.com
- Huynh (Đoàn Như Huynh): huynh.doannhu@spxexpress.com
- Thi (Hồ Tấn Thi): tanthi.ho@spxexpress.com
- Phụng (Trần Minh Phụng): phung.tranminh@spxexpress.com
- Long (Nguyễn Thiên Long): thienlong.nguyen@spxexpress.com
- Trang (Trần Thị Thiên Trang): thientrang.tranthi@spxexpress.com
- Linh (Bùi Nhựt Linh): nhutlinh.bui@spxexpress.com

=== VUI VẺ ===
- Nhậu / uống bia: Đô bất tử hahaha!
"""

CUSTOM_REPLIES = [
    {
        "keywords": ["chu nhan", "chủ nhân", "owner"],
        "reply": "Chủ Nhân Của Tôi là Anh Thọ (Trương Hữu Thọ)! 🦖\n📧 tho.truonghuu@spxexpress.com"
    },
    {
        "keywords": ["nhậu", "uống bia", "uống rượu", "nhau"],
        "reply": "Đô bất tử hahaha! 🍺🔥"
    },
]


def get_access_token():
    try:
        r = requests.post("https://openapi.seatalk.io/auth/app_access_token",
                          json={"app_id": APP_ID, "app_secret": APP_SECRET}, timeout=10)
        return r.json().get("app_access_token", "")
    except Exception as e:
        print(f"TOKEN ERROR: {e}"); return ""

def send_message_direct(employee_code, text):
    token = get_access_token()
    if not token: return
    try:
        r = requests.post("https://openapi.seatalk.io/messaging/v2/single_chat",
            json={"employee_code": str(employee_code), "message": {"tag": "text", "text": {"content": text}}},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=10)
        print(f"SEND DIRECT: {r.status_code}")
    except Exception as e:
        print(f"SEND DIRECT ERROR: {e}")

def send_message_group(group_id, text):
    token = get_access_token()
    if not token: return
    try:
        r = requests.post("https://openapi.seatalk.io/messaging/v2/group_chat",
            json={"group_id": str(group_id), "message": {"tag": "text", "text": {"content": text}}},
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=10)
        print(f"SEND GROUP: {r.status_code}")
    except Exception as e:
        print(f"SEND GROUP ERROR: {e}")

def check_custom_reply(message_text):
    msg_norm = normalize(message_text)
    for item in CUSTOM_REPLIES:
        for kw in item["keywords"]:
            if normalize(kw) in msg_norm:
                print(f"CUSTOM match: '{kw}'")
                return item["reply"]
    return None

def ask_groq(message_text):
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": "llama3-8b-8192",
                  "messages": [{"role": "system", "content": COMPANY_INFO}, {"role": "user", "content": message_text}],
                  "max_tokens": 800, "temperature": 0.7}, timeout=30)
        result = r.json()
        if "error" in result: return None
        choices = result.get("choices", [])
        return choices[0]["message"]["content"] if choices else None
    except Exception as e:
        print(f"GROQ ERR: {e}"); return None

def ask_gemini(message_text):
    for model in ["gemini-2.0-flash-lite", "gemini-2.0-flash-exp", "gemini-1.0-pro"]:
        try:
            r = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}",
                headers={"Content-Type": "application/json"},
                json={"contents": [{"role": "user", "parts": [{"text": f"{COMPANY_INFO}\n\nNgười dùng hỏi: {message_text}"}]}],
                      "generationConfig": {"maxOutputTokens": 800, "temperature": 0.7}}, timeout=30)
            result = r.json()
            if "error" in result: continue
            cands = result.get("candidates", [])
            if cands: return cands[0]["content"]["parts"][0]["text"]
        except: continue
    return None

def fallback_reply(message_text):
    msg = message_text.lower().strip()
    if any(w in msg for w in ["xin chào", "hello", "hi", "chào", "hey"]):
        return "Xin chào! 👋 Tôi là Khủng Long 5 Canh - OE Team. Gõ 'menu' để xem tôi giúp được gì nhé!"
    elif any(w in msg for w in ["menu", "help", "giúp"]):
        return (
            "📋 Tôi có thể giúp:\n"
            "- 👤 Tìm thành viên OE: gõ tên (VD: 'Quý', 'Kate', 'Thi là ai')\n"
            "- 📋 Danh sách team: gõ 'danh sách team'\n"
            "- 📅 Task & PIC: gõ 'task của Quý', 'Long làm gì'\n"
            "- 📚 Tài liệu: gõ 'tài liệu onboarding', 'link KPI'\n"
            "- 🎓 Onboarding: gõ 'OB', 'onboarding'\n"
            "- ⏰ Giờ làm việc | 📋 Xin nghỉ phép\n"
            "Cứ hỏi tự nhiên nhé! 😊"
        )
    elif any(w in msg for w in ["giờ làm việc", "mấy giờ"]):
        return "⏰ Thứ 2-6: 8:00-17:30 | Thứ 7: 8:00-12:00 | CN: Nghỉ"
    elif any(w in msg for w in ["nghỉ phép", "xin nghỉ"]):
        return "📋 Xin nghỉ: báo trước 3 ngày → gửi đơn form HR → chờ quản lý duyệt"
    else:
        return "Tôi không hiểu rõ câu hỏi 🤔 Gõ 'menu' để xem hướng dẫn, hoặc liên hệ Kate: ngocmy.lieu@spxexpress.com"


def get_reply(message_text):
    print(f"\n===== MSG: '{message_text}' =====")

    # 1. Custom reply
    custom = check_custom_reply(message_text)
    if custom:
        return custom

    # 2. Hardcoded data
    data_result = query_data(message_text)
    if data_result:
        return data_result

    # 3. AI
    reply = ask_groq(message_text) or ask_gemini(message_text)
    if reply:
        return reply

    return fallback_reply(message_text)


def extract_group_message(event):
    msg = event.get("message", {})
    text = (msg.get("text", {}).get("plain_text", "")
            or msg.get("text", {}).get("content", "")
            or msg.get("plain_text", ""))
    return re.sub(r'@[^\s]+\s*', '', text).strip()


# ===================== DEBUG ENDPOINT =====================
@app.route("/debug", methods=["GET"])
def debug():
    q = request.args.get("q", "Quý")
    result = get_reply(q)
    return json.dumps({"query": q, "reply": result}, ensure_ascii=False, indent=2), 200, {"Content-Type": "application/json"}

# ===================== ROUTES =====================
@app.route("/", methods=["GET"])
def home():
    return "Khung Long 5 Canh - OE Team Bot!", 200

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
            message_text  = event.get("message", {}).get("text", {}).get("content", "")
            print(f"DIRECT: {employee_code} | '{message_text}'")
            if employee_code and message_text:
                send_message_direct(employee_code, get_reply(message_text))

        elif event_type == "new_mentioned_message_received_from_group_chat":
            group_id     = event.get("group_id", "")
            message_text = extract_group_message(event)
            print(f"GROUP: {group_id} | '{message_text}'")
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
