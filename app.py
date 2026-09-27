# -*- coding: utf-8 -*-
"""
app.py — অনলাইন MCQ পরীক্ষা প্ল্যাটফর্ম
বিষয়: জীববিজ্ঞান, পদার্থবিজ্ঞান, রসায়ন
"""

import time
import random
import datetime
import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh

import db
from question_parser import parse_questions

ADMIN_PASSWORD = "098765"
ADMIN_NAME = "মো: নাঈম ইসলাম"
ADMIN_DESIGNATION = "সহকারী শিক্ষক"

BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")
BN_MONTHS = {
    1: "জানুয়ারি", 2: "ফেব্রুয়ারি", 3: "মার্চ", 4: "এপ্রিল", 5: "মে", 6: "জুন",
    7: "জুলাই", 8: "আগস্ট", 9: "সেপ্টেম্বর", 10: "অক্টোবর", 11: "নভেম্বর", 12: "ডিসেম্বর",
}


def format_bn_datetime(iso_str):
    """ISO টাইমস্ট্যাম্পকে '২৩ সেপ্টেম্বর ২০২৬, দুপুর ০২:৩৫' আকারে ফরম্যাট করে (১২-ঘণ্টা)"""
    if not iso_str:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(iso_str)
    except ValueError:
        return iso_str
    hour12 = dt.strftime("%I:%M")
    ampm = "দুপুর" if 12 <= dt.hour < 18 else ("বিকাল" if dt.hour >= 18 and dt.hour < 20 else
           ("রাত" if dt.hour >= 20 or dt.hour < 4 else ("ভোর" if dt.hour < 6 else "সকাল")))
    day = str(dt.day).translate(BN_DIGITS)
    year = str(dt.year).translate(BN_DIGITS)
    time_bn = hour12.translate(BN_DIGITS)
    return f"{day} {BN_MONTHS[dt.month]} {year}, {ampm} {time_bn}"

st.set_page_config(page_title="অনলাইন এম.সি.কিউ প্ল্যাটফর্ম", page_icon="📝", layout="wide")

db.init_db()

# ---------------------------------------------------------------------------
# বিষয়ভিত্তিক রঙ ও আইকন (প্রতিটি বিষয়ের নিজস্ব পরিচয়)
# ---------------------------------------------------------------------------
SUBJECT_STYLE = {
    "জীববিজ্ঞান": {"color": "#2F8F5B", "soft": "#EAF6EF", "icon": "🌿"},
    "পদার্থবিজ্ঞান": {"color": "#35578C", "soft": "#EAF0F8", "icon": "⚛️"},
    "রসায়ন": {"color": "#C1752E", "soft": "#FBF0E5", "icon": "🧪"},
}
DEFAULT_SUBJECT_STYLE = {"color": "#5B6B63", "soft": "#F1F1EC", "icon": "📘"}


def subject_style(name):
    return SUBJECT_STYLE.get(name, DEFAULT_SUBJECT_STYLE)


# ---------------------------------------------------------------------------
# স্টাইল — কাগজ-খাতা ও চকবোর্ডের অনুপ্রেরণায় ডিজাইন
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Tiro+Bangla&family=Hind+Siliguri:wght@400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Hind Siliguri', sans-serif; }

:root {
    --ink: #1D3F33;
    --cream: #FBF8F1;
    --card-bg: #FFFFFF;
    --text-main: #23302B;
    --text-muted: #6B7A72;
    --border: #E4E0D4;
}

.stApp { background: var(--cream); }
.block-container { padding-top: 1.6rem; max-width: 900px; }

/* ---------- বর্ডারড কার্ডে হালকা shadow (বিষয় কার্ড, প্রশ্ন কার্ড) ---------- */
div[data-testid="stVerticalBlockBorderWrapper"] {
    box-shadow: 0 2px 8px rgba(35,48,43,0.06);
    border-radius: 12px;
    transition: box-shadow 0.2s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    box-shadow: 0 4px 14px rgba(35,48,43,0.10);
}

/* ---------- হেডার ব্যানার ---------- */
.app-header {
    background: linear-gradient(135deg, #1D3F33 0%, #163329 100%);
    background-image:
        linear-gradient(135deg, #1D3F33 0%, #163329 100%),
        repeating-linear-gradient(0deg, rgba(255,255,255,0.035) 0px, rgba(255,255,255,0.035) 1px, transparent 1px, transparent 28px),
        repeating-linear-gradient(90deg, rgba(255,255,255,0.035) 0px, rgba(255,255,255,0.035) 1px, transparent 1px, transparent 28px);
    box-shadow: 0 4px 14px rgba(29,63,51,0.18);
    border-radius: 16px;
    padding: 22px 28px;
    margin-bottom: 28px;
    display: flex;
    align-items: center;
    gap: 18px;
}
.app-header-badge {
    font-size: 30px;
    background: rgba(255,255,255,0.12);
    width: 54px; height: 54px;
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    flex-shrink: 0;
}
.app-header-title {
    font-family: 'Tiro Bangla', serif;
    font-size: 27px;
    color: #F7F4EA;
    line-height: 1.3;
}
.app-header-sub {
    color: #C7D6CC;
    font-size: 14px;
    margin-top: 3px;
}

/* ---------- সাধারণ শিরোনাম ---------- */
.big-title {
    font-family: 'Tiro Bangla', serif;
    font-size: 25px;
    font-weight: 400;
    color: var(--text-main);
    margin-bottom: 4px;
}

/* ---------- বিষয় কার্ড ---------- */
.subject-card-head {
    display: flex; align-items: center; gap: 10px; margin-bottom: 2px;
}
.subject-icon-badge {
    font-size: 22px;
    width: 40px; height: 40px;
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
}
.subject-name {
    font-family: 'Tiro Bangla', serif;
    font-size: 19px;
    color: var(--text-main);
}
.status-pill {
    display: inline-flex; align-items: center; gap: 6px;
    font-size: 12.5px; font-weight: 600;
    padding: 3px 10px; border-radius: 20px;
    margin: 8px 0 10px 0;
}
.status-running { background: #E4F5EA; color: #1F7A45; }
.status-idle { background: #F1F1EC; color: #8A9089; }
.pulse-dot {
    width: 7px; height: 7px; border-radius: 50%; background: #1F7A45;
    animation: pulse 1.4s infinite;
}
@keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(31,122,69,0.5); }
    70% { box-shadow: 0 0 0 6px rgba(31,122,69,0); }
    100% { box-shadow: 0 0 0 0 rgba(31,122,69,0); }
}
.subject-meta { color: var(--text-muted); font-size: 13px; margin: 6px 0 10px 0; }

/* ---------- টাইমার ---------- */
.timer-box {
    background: var(--ink); color: #F7F4EA; padding: 10px 22px; border-radius: 10px;
    font-family: 'Tiro Bangla', serif;
    font-size: 22px; text-align: center; display: inline-block;
    letter-spacing: 1px;
}
.timer-warning { background: #A23B2E !important; }

/* ---------- প্রশ্ন কার্ড ---------- */
.q-number-badge {
    display: inline-flex; align-items: center; justify-content: center;
    width: 28px; height: 28px; border-radius: 50%;
    background: var(--ink); color: #F7F4EA;
    font-size: 13px; font-weight: 600; margin-right: 8px;
}
.q-text { font-size: 16px; color: var(--text-main); }

/* ---------- উত্তর লক হওয়ার পর দেখানো (কাস্টম রেডিও লুক) ---------- */
.locked-options { margin-top: 6px; }
.locked-option {
    display: flex; align-items: center; gap: 10px;
    padding: 7px 4px; font-size: 15px; color: var(--text-muted);
}
.locked-option.locked-selected { color: var(--text-main); font-weight: 600; }
.locked-dot {
    width: 16px; height: 16px; border-radius: 50%;
    background: #C0392B; border: 2px solid #C0392B; flex-shrink: 0;
}
.locked-dot-empty {
    width: 16px; height: 16px; border-radius: 50%;
    border: 2px solid #D8D3C4; flex-shrink: 0;
}

/* ---------- ফলাফল স্কোরকার্ড ---------- */
.score-card {
    border-radius: 16px; padding: 26px; text-align: center;
    color: #fff; margin-bottom: 22px;
}
.score-card .score-value { font-family: 'Tiro Bangla', serif; font-size: 42px; }
.score-card .score-label { font-size: 14px; opacity: 0.9; margin-top: 2px; }
.score-good { background: linear-gradient(135deg, #2F8F5B, #226B44); }
.score-mid { background: linear-gradient(135deg, #C1752E, #9C5B20); }
.score-low { background: linear-gradient(135deg, #A23B2E, #7E2B20); }

.review-card {
    border-radius: 12px; padding: 14px 16px; margin-bottom: 12px;
    border: 1px solid var(--border);
}
.review-correct { background: #F3FAF5; border-color: #CBE8D5; }
.review-wrong { background: #FDF3F1; border-color: #F0CFC7; }
.option-row { padding: 3px 0 3px 6px; font-size: 14.5px; }
.option-correct-tag { color: #1F7A45; font-weight: 600; }
.option-wrong-tag { color: #A23B2E; font-weight: 600; }
</style>
""", unsafe_allow_html=True)


def render_header():
    st.markdown("""
    <div class="app-header">
        <div class="app-header-badge">📝</div>
        <div>
            <div class="app-header-title">অনলাইন এম.সি.কিউ প্ল্যাটফর্ম</div>
            <div class="app-header-sub">জীববিজ্ঞান, পদার্থবিজ্ঞান ও রসায়ন — অধ্যায়ভিত্তিক প্রস্তুতি পরীক্ষা</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# সেশন স্টেট ইনিশিয়ালাইজ
# ---------------------------------------------------------------------------
defaults = {
    "role": None,  # "student" / "admin"
    "admin_authenticated": False,
    "student_name": "",
    "student_class": "",
    "student_registered": False,
    "exam_chapter_id": None,
    "exam_questions": None,
    "exam_cfg": None,
    "exam_chapter_info": None,
    "exam_subject_name": None,
    "exam_start_time": None,
    "exam_answers": {},
    "exam_submitted_result": None,
    "confirm_submit_pending": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def go_home():
    for key in ["student_registered", "exam_chapter_id", "exam_questions",
                "exam_cfg", "exam_chapter_info", "exam_subject_name", "confirm_submit_pending",
                "exam_start_time", "exam_answers", "exam_submitted_result"]:
        st.session_state[key] = defaults[key]


# ---------------------------------------------------------------------------
# সাইডবার — ভূমিকা নির্বাচন
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 📝 MCQ পরীক্ষা প্ল্যাটফর্ম")
    mode = st.radio("প্রবেশ করুন", ["শিক্ষার্থী", "এডমিন"], index=0)
    st.session_state.role = "admin" if mode == "এডমিন" else "student"

    if st.session_state.role == "admin" and st.session_state.admin_authenticated:
        if st.button("🔒 লগআউট"):
            st.session_state.admin_authenticated = False
            st.rerun()


# ===========================================================================
# এডমিন প্যানেল
# ===========================================================================
def admin_login():
    render_header()
    st.markdown('<div class="big-title">🔐 এডমিন লগইন</div>', unsafe_allow_html=True)
    with st.form("admin_login_form"):
        pwd = st.text_input("পাসওয়ার্ড দিন", type="password")
        submitted = st.form_submit_button("প্রবেশ করুন")
        if submitted:
            if pwd == ADMIN_PASSWORD:
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("ভুল পাসওয়ার্ড। আবার চেষ্টা করুন।")


def admin_panel():
    render_header()
    st.markdown('<div class="big-title">⚙️ এডমিন প্যানেল</div>', unsafe_allow_html=True)

    tabs = st.tabs(["📊 ড্যাশবোর্ড", "📚 অধ্যায় ব্যবস্থাপনা", "➕ প্রশ্ন যোগ/এডিট",
                     "⏱️ পরীক্ষা সেটিংস", "🏆 ফলাফল ও মেধাতালিকা"])

    subjects = db.get_subjects()
    subject_names = [s["name"] for s in subjects]

    # ---------------- ড্যাশবোর্ড ----------------
    with tabs[0]:
        st.subheader("সার্বিক পরিসংখ্যান")
        all_subs = db.get_all_submissions()

        col1, col2, col3 = st.columns(3)
        col1.metric("মোট বিষয়", len(subjects))
        total_chapters = sum(len(db.get_chapters(s["id"])) for s in subjects)
        col2.metric("মোট অধ্যায়", total_chapters)
        col3.metric("মোট পরীক্ষা দিয়েছে", len(all_subs))

        st.markdown("#### চলমান পরীক্ষা")
        running_any = False
        for s in subjects:
            for ch in db.get_chapters(s["id"]):
                cfg = db.get_exam_config(ch["id"])
                if cfg["is_active"]:
                    running_any = True
                    qc = cfg.get("question_count") or "সবগুলো"
                    st.markdown(
                        f"- **{s['name']}** → *{ch['name']}* "
                        f"(সময়: {cfg['duration_minutes']} মিনিট, প্রশ্ন: {qc}, প্রতি প্রশ্নে মার্ক: {cfg['marks_per_question']}) "
                        f"<span class='exam-running'>● পরীক্ষা চলছে</span>",
                        unsafe_allow_html=True
                    )
        if not running_any:
            st.caption("এই মুহূর্তে কোনো পরীক্ষা চলছে না।")

        if all_subs:
            st.markdown("#### সাম্প্রতিক জমাসমূহ")
            df = pd.DataFrame(all_subs)[
                ["student_name", "student_class", "subject_name", "chapter_name", "score", "total_marks", "submitted_at"]
            ]
            df["submitted_at"] = df["submitted_at"].apply(format_bn_datetime)
            df.columns = ["নাম", "শ্রেণি", "বিষয়", "অধ্যায়", "প্রাপ্ত নম্বর", "পূর্ণমান", "জমার সময়"]
            st.dataframe(df.head(20), use_container_width=True, hide_index=True)

    # ---------------- অধ্যায় ব্যবস্থাপনা ----------------
    with tabs[1]:
        st.subheader("অধ্যায় ব্যবস্থাপনা")
        subj_choice = st.selectbox("বিষয় নির্বাচন করুন", subject_names, key="chap_subject")
        subj = db.get_subject_by_name(subj_choice)

        with st.form("add_chapter_form", clear_on_submit=True):
            new_chapter = st.text_input("নতুন অধ্যায়ের নাম")
            add_btn = st.form_submit_button("➕ অধ্যায় যোগ করুন")
            if add_btn:
                if new_chapter.strip():
                    db.add_chapter(subj["id"], new_chapter.strip())
                    st.success(f"'{new_chapter.strip()}' অধ্যায় যোগ হয়েছে।")
                    st.rerun()
                else:
                    st.warning("অধ্যায়ের নাম লিখুন।")

        st.markdown("---")
        chapters = db.get_chapters(subj["id"])
        if not chapters:
            st.info("এখনো কোনো অধ্যায় যোগ করা হয়নি।")

        for ch in chapters:
            q_count = len(db.get_questions(ch["id"]))
            c1, c2, c3, c4 = st.columns([4, 2, 1, 1])
            with c1:
                edited_name = st.text_input(
                    f"chapter_{ch['id']}", value=ch["name"], label_visibility="collapsed", key=f"ch_name_{ch['id']}"
                )
            with c2:
                st.caption(f"প্রশ্ন সংখ্যা: {q_count}")
            with c3:
                if st.button("💾 সংরক্ষণ", key=f"save_ch_{ch['id']}"):
                    db.update_chapter(ch["id"], edited_name)
                    st.success("সংরক্ষণ হয়েছে।")
                    st.rerun()
            with c4:
                if st.button("🗑️ মুছুন", key=f"del_ch_{ch['id']}"):
                    db.delete_chapter(ch["id"])
                    st.success("অধ্যায় মুছে ফেলা হয়েছে।")
                    st.rerun()

    # ---------------- প্রশ্ন যোগ/এডিট ----------------
    with tabs[2]:
        st.subheader("প্রশ্ন যোগ ও এডিট করুন")
        subj_choice2 = st.selectbox("বিষয় নির্বাচন করুন", subject_names, key="q_subject")
        subj2 = db.get_subject_by_name(subj_choice2)
        chapters2 = db.get_chapters(subj2["id"])

        if not chapters2:
            st.info("প্রথমে 'অধ্যায় ব্যবস্থাপনা' ট্যাব থেকে একটি অধ্যায় যোগ করুন।")
        else:
            chapter_names2 = {ch["name"]: ch["id"] for ch in chapters2}
            ch_choice = st.selectbox("অধ্যায় নির্বাচন করুন", list(chapter_names2.keys()), key="q_chapter")
            chapter_id2 = chapter_names2[ch_choice]

            st.markdown("##### 📋 একসাথে অনেকগুলো প্রশ্ন পেস্ট করুন")
            st.caption(
                "ফরম্যাট: প্রশ্ন → ক) খ) গ) ঘ) → উত্তর: ক/খ/গ/ঘ | প্রতিটি প্রশ্নের পর একটি নতুন লাইন দিন।"
            )
            with st.expander("উদাহরণ দেখুন"):
                st.code(
                    "প্রশ্ন: বাংলাদেশের রাজধানীর নাম কী?\n"
                    "ক) চট্টগ্রাম\nখ) ঢাকা\nগ) সিলেট\nঘ) রাজশাহী\nউত্তর: খ\n\n"
                    "মানবদেহের সবচেয়ে বড় অঙ্গ কোনটি?\n"
                    "ক) হৃদপিণ্ড\nখ) যকৃত\nগ) ত্বক\nঘ) মস্তিষ্ক\nউত্তর: গ",
                    language=None
                )

            bulk_text = st.text_area("এখানে পেস্ট করুন", height=250, key="bulk_paste_area")
            if st.button("🔍 যাচাই ও যোগ করুন", key="parse_add_btn"):
                if not bulk_text.strip():
                    st.warning("কিছু পেস্ট করুন।")
                else:
                    parsed, errs = parse_questions(bulk_text)
                    if parsed:
                        db.add_questions_bulk(chapter_id2, parsed)
                        st.success(f"✅ {len(parsed)}টি প্রশ্ন সফলভাবে যোগ করা হয়েছে।")
                    if errs:
                        for e in errs:
                            st.warning(e)
                    if parsed:
                        st.rerun()

            st.markdown("---")
            st.markdown(f"##### ✏️ '{ch_choice}' অধ্যায়ের প্রশ্নসমূহ")
            questions = db.get_questions(chapter_id2)
            st.caption(f"মোট প্রশ্ন: {len(questions)}")

            for q in questions:
                with st.expander(f"প্রশ্ন #{q['id']}: {q['question_text'][:60]}"):
                    with st.form(f"edit_q_{q['id']}"):
                        qt = st.text_area("প্রশ্ন", value=q["question_text"], key=f"qt_{q['id']}")
                        c1, c2 = st.columns(2)
                        with c1:
                            ka = st.text_input("ক)", value=q["option_ka"], key=f"ka_{q['id']}")
                            ga = st.text_input("গ)", value=q["option_ga"], key=f"ga_{q['id']}")
                        with c2:
                            kha = st.text_input("খ)", value=q["option_kha"], key=f"kha_{q['id']}")
                            gha = st.text_input("ঘ)", value=q["option_gha"], key=f"gha_{q['id']}")
                        ans = st.selectbox(
                            "সঠিক উত্তর", ["ক", "খ", "গ", "ঘ"],
                            index=["ক", "খ", "গ", "ঘ"].index(q["correct_option"]),
                            key=f"ans_{q['id']}"
                        )
                        img_url = st.text_input(
                            "ছবি/গ্রাফের লিংক (ঐচ্ছিক)", value=q.get("image_url") or "",
                            key=f"img_{q['id']}", placeholder="https://i.ibb.co/..."
                        )
                        colA, colB = st.columns(2)
                        with colA:
                            save = st.form_submit_button("💾 সংরক্ষণ করুন")
                        with colB:
                            delete = st.form_submit_button("🗑️ মুছে ফেলুন")

                        if save:
                            db.update_question(q["id"], qt, ka, kha, ga, gha, ans, img_url)
                            st.success("সংরক্ষণ হয়েছে।")
                            st.rerun()
                        if delete:
                            db.delete_question(q["id"])
                            st.success("প্রশ্ন মুছে ফেলা হয়েছে।")
                            st.rerun()

    # ---------------- পরীক্ষা সেটিংস ----------------
    with tabs[3]:
        st.subheader("পরীক্ষা সেটিংস ও চালু/বন্ধ নিয়ন্ত্রণ")
        subj_choice3 = st.selectbox("বিষয় নির্বাচন করুন", subject_names, key="exam_subject")
        subj3 = db.get_subject_by_name(subj_choice3)
        chapters3 = db.get_chapters(subj3["id"])

        if not chapters3:
            st.info("প্রথমে একটি অধ্যায় যোগ করুন।")
        else:
            chapter_names3 = {ch["name"]: ch["id"] for ch in chapters3}
            ch_choice3 = st.selectbox("অধ্যায় নির্বাচন করুন", list(chapter_names3.keys()), key="exam_chapter_select")
            chapter_id3 = chapter_names3[ch_choice3]

            cfg = db.get_exam_config(chapter_id3)
            q_count3 = len(db.get_questions(chapter_id3))
            st.caption(f"এই অধ্যায়ে মোট প্রশ্ন সংখ্যা: {q_count3}")

            with st.form("exam_config_form"):
                duration = st.number_input("পরীক্ষার সময় (মিনিট)", min_value=1, max_value=300,
                                            value=cfg["duration_minutes"])
                marks = st.number_input("প্রতি প্রশ্নের মার্ক", min_value=0.25, max_value=10.0,
                                         value=float(cfg["marks_per_question"]), step=0.25)
                neg = st.number_input("ভুল উত্তরে নেগেটিভ মার্ক (ঐচ্ছিক, ০ দিলে নেই)", min_value=0.0,
                                       max_value=10.0, value=float(cfg["negative_marks"]), step=0.25)
                if q_count3 > 0:
                    default_qc = cfg.get("question_count") or q_count3
                    default_qc = min(default_qc, q_count3)
                    q_to_use = st.number_input(
                        f"পরীক্ষায় কতটা প্রশ্ন ব্যবহার হবে (মোট আছে {q_count3}টি)",
                        min_value=1, max_value=q_count3, value=default_qc,
                    )
                    st.caption("প্রশ্নভাণ্ডার থেকে এলোমেলোভাবে এই সংখ্যক প্রশ্ন বেছে পরীক্ষা নেওয়া হবে।")
                else:
                    q_to_use = None
                save_cfg = st.form_submit_button("💾 সেটিংস সংরক্ষণ করুন")
                if save_cfg:
                    db.update_exam_config(chapter_id3, int(duration), marks, neg, q_to_use)
                    st.success("সেটিংস সংরক্ষণ হয়েছে।")
                    st.rerun()

            st.markdown("---")
            if cfg["is_active"]:
                st.markdown("**অবস্থা:** <span class='exam-running'>● পরীক্ষা চলছে</span>", unsafe_allow_html=True)
                if st.button("⏹️ পরীক্ষা বন্ধ করুন"):
                    db.set_exam_active(chapter_id3, False)
                    st.rerun()
            else:
                st.markdown("**অবস্থা:** পরীক্ষা বন্ধ আছে")
                if q_count3 == 0:
                    st.warning("পরীক্ষা চালু করার আগে অন্তত একটি প্রশ্ন যোগ করুন।")
                else:
                    if st.button("▶️ পরীক্ষা চালু করুন"):
                        db.set_exam_active(chapter_id3, True)
                        st.success("পরীক্ষা চালু হয়েছে! শিক্ষার্থীরা এখন প্রবেশ করতে পারবে।")
                        st.rerun()

    # ---------------- ফলাফল ও মেধাতালিকা ----------------
    with tabs[4]:
        st.subheader("ফলাফল ও মেধাতালিকা")
        subj_choice4 = st.selectbox("বিষয় নির্বাচন করুন", subject_names, key="result_subject")
        subj4 = db.get_subject_by_name(subj_choice4)
        chapters4 = db.get_chapters(subj4["id"])

        if not chapters4:
            st.info("এই বিষয়ে এখনো কোনো অধ্যায় নেই।")
        else:
            chapter_names4 = {ch["name"]: ch["id"] for ch in chapters4}
            ch_choice4 = st.selectbox("অধ্যায় নির্বাচন করুন", list(chapter_names4.keys()), key="result_chapter")
            chapter_id4 = chapter_names4[ch_choice4]

            subs = db.get_submissions_for_chapter(chapter_id4)
            if not subs:
                st.info("এই অধ্যায়ে এখনো কেউ পরীক্ষা দেয়নি।")
            else:
                st.markdown(f"##### 🏆 মেধাতালিকা — {ch_choice4}")
                rows = []
                for i, s in enumerate(subs, start=1):
                    pct = round((s["score"] / s["total_marks"]) * 100, 1) if s["total_marks"] else 0
                    mins, secs = divmod(s["time_taken_seconds"] or 0, 60)
                    rows.append({
                        "মেধাক্রম": i,
                        "নাম": s["student_name"],
                        "শ্রেণি": s["student_class"],
                        "প্রাপ্ত নম্বর": s["score"],
                        "পূর্ণমান": s["total_marks"],
                        "শতকরা": f"{pct}%",
                        "সঠিক": s["correct_count"],
                        "ভুল": s["wrong_count"],
                        "অনুত্তরিত": s["unanswered_count"],
                        "সময় লেগেছে": f"{mins}মি {secs}সে",
                        "জমার সময়": format_bn_datetime(s["submitted_at"]),
                    })
                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True, hide_index=True)

                csv = df.to_csv(index=False).encode("utf-8-sig")
                st.download_button("⬇️ CSV ডাউনলোড করুন", csv,
                                    file_name=f"merit_list_{ch_choice4}.csv", mime="text/csv")


# ===========================================================================
# শিক্ষার্থী পোর্টাল
# ===========================================================================
def student_registration():
    render_header()
    st.markdown('<div class="big-title">পরীক্ষায় স্বাগতম</div>', unsafe_allow_html=True)
    st.write("পরীক্ষা শুরু করার আগে নিচে আপনার তথ্য দিন।")

    with st.form("student_reg_form"):
        name = st.text_input("তোমার নাম")
        cls = st.text_input("তোমার শ্রেণি (যেমনঃ নবম, দশম)")
        submitted = st.form_submit_button("প্রবেশ করুন")
        if submitted:
            if name.strip() and cls.strip():
                st.session_state.student_name = name.strip()
                st.session_state.student_class = cls.strip()
                st.session_state.student_registered = True
                st.rerun()
            else:
                st.warning("নাম ও শ্রেণি দুটোই লিখুন।")

    st.markdown(
        f"<div style='text-align:center; margin-top:60px; color:#B8B2A2; font-size:12.5px;'>"
        f"{ADMIN_NAME}<br>{ADMIN_DESIGNATION}</div>",
        unsafe_allow_html=True
    )


def subject_selection():
    render_header()
    st.markdown(
        f'<div class="big-title">স্বাগতম, {st.session_state.student_name} '
        f'({st.session_state.student_class})</div>',
        unsafe_allow_html=True
    )
    st.write("নিচে থেকে বিষয় ও অধ্যায় নির্বাচন করে পরীক্ষা শুরু করো।")

    with st.spinner("লোড হচ্ছে..."):
        subjects = db.get_subjects()

    dynamic_css = "<style>"
    for subj in subjects:
        style = subject_style(subj["name"])
        dynamic_css += (
            f".st-key-subject_card_{subj['id']} {{ border-top: 4px solid {style['color']} !important; }}"
        )
    dynamic_css += "</style>"
    st.markdown(dynamic_css, unsafe_allow_html=True)

    cols = st.columns(len(subjects))
    for col, subj in zip(cols, subjects):
        style = subject_style(subj["name"])
        with col:
            with st.container(border=True, key=f"subject_card_{subj['id']}"):
                chapters = db.get_chapters(subj["id"])
                any_running = any(db.get_exam_config(c["id"])["is_active"] for c in chapters) if chapters else False

                st.markdown(
                    f"<div class='subject-card-head'>"
                    f"<div class='subject-icon-badge' style='background:{style['soft']};'>{style['icon']}</div>"
                    f"<div class='subject-name'>{subj['name']}</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )

                if any_running:
                    st.markdown(
                        "<div class='status-pill status-running'>"
                        "<span class='pulse-dot'></span> পরীক্ষা চলছে</div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        "<div class='status-pill status-idle'>কোনো পরীক্ষা চলছে না</div>",
                        unsafe_allow_html=True
                    )

                if not chapters:
                    st.caption("এখনো কোনো অধ্যায় নেই।")
                    continue

                chapter_names = [c["name"] for c in chapters]
                chosen = st.selectbox("অধ্যায় নির্বাচন করো", chapter_names, key=f"select_ch_{subj['id']}")
                chosen_chapter = next(c for c in chapters if c["name"] == chosen)

                cfg = db.get_exam_config(chosen_chapter["id"])
                q_count_total = len(db.get_questions(chosen_chapter["id"]))
                is_running = cfg["is_active"]
                q_to_use = min(cfg.get("question_count") or q_count_total, q_count_total)

                if is_running:
                    st.markdown(
                        f"<div class='subject-meta'>সময়: {cfg['duration_minutes']} মিনিট &nbsp;•&nbsp; "
                        f"প্রশ্ন সংখ্যা: {q_to_use} &nbsp;•&nbsp; "
                        f"পূর্ণমান: {q_to_use * cfg['marks_per_question']}</div>",
                        unsafe_allow_html=True
                    )
                    if st.button("🚀 পরীক্ষা শুরু করো", key=f"start_{subj['id']}", type="primary"):
                        all_questions = db.get_questions(chosen_chapter["id"])
                        if q_to_use < len(all_questions):
                            selected_questions = random.sample(all_questions, q_to_use)
                        else:
                            selected_questions = all_questions
                        st.session_state.exam_chapter_id = chosen_chapter["id"]
                        st.session_state.exam_questions = selected_questions
                        st.session_state.exam_cfg = cfg
                        st.session_state.exam_chapter_info = chosen_chapter
                        st.session_state.exam_subject_name = subj["name"]
                        st.session_state.exam_start_time = time.time()
                        st.session_state.exam_answers = {}
                        st.session_state.exam_submitted_result = None
                        st.rerun()
                else:
                    st.caption("এই অধ্যায়ে এখন পরীক্ষা চালু নেই।")


def grade_and_submit():
    chapter_id = st.session_state.exam_chapter_id
    questions = st.session_state.exam_questions
    answers = st.session_state.exam_answers

    cfg = st.session_state.exam_cfg
    chapter = st.session_state.exam_chapter_info
    subject_name = st.session_state.exam_subject_name

    correct_count = wrong_count = unanswered_count = 0
    detail = []
    for q in questions:
        given = answers.get(str(q["id"]))
        if given is None:
            unanswered_count += 1
            is_correct = None
        elif given == q["correct_option"]:
            correct_count += 1
            is_correct = True
        else:
            wrong_count += 1
            is_correct = False

        detail.append({
            "question": q["question_text"],
            "image_url": q.get("image_url"),
            "options": {"ক": q["option_ka"], "খ": q["option_kha"], "গ": q["option_ga"], "ঘ": q["option_gha"]},
            "given": given,
            "correct": q["correct_option"],
            "is_correct": is_correct,
        })

    score = correct_count * cfg["marks_per_question"] - wrong_count * cfg["negative_marks"]
    score = max(score, 0)
    total_marks = len(questions) * cfg["marks_per_question"]
    time_taken = int(time.time() - st.session_state.exam_start_time)

    sub_id = db.save_submission(
        st.session_state.student_name, st.session_state.student_class, chapter_id,
        subject_name, chapter["name"], answers, len(questions), correct_count, wrong_count,
        unanswered_count, score, total_marks, time_taken
    )

    st.session_state.exam_submitted_result = {
        "score": score, "total_marks": total_marks, "correct_count": correct_count,
        "wrong_count": wrong_count, "unanswered_count": unanswered_count,
        "time_taken": time_taken, "detail": detail, "chapter_name": chapter["name"],
        "subject_name": subject_name,
    }
    st.session_state.exam_questions = None
    st.session_state.exam_chapter_id = None


def exam_taking():
    cfg = st.session_state.exam_cfg
    duration_seconds = cfg["duration_minutes"] * 60
    elapsed = time.time() - st.session_state.exam_start_time
    remaining = int(duration_seconds - elapsed)

    if remaining <= 0:
        try:
            grade_and_submit()
        except Exception as e:
            st.error("⚠️ সময় শেষে অটো-সাবমিট করতে সমস্যা হয়েছে। নিচের এররটি স্ক্রিনশট নিয়ে জানান:")
            st.exception(e)
            st.stop()
        st.rerun()
        return

    st_autorefresh(interval=1000, key="exam_timer_refresh")

    questions = st.session_state.exam_questions
    answered_count = len(st.session_state.exam_answers)
    total_count = len(questions)
    progress_pct = int((answered_count / total_count) * 100) if total_count else 0

    mins, secs = divmod(remaining, 60)
    subj_color = subject_style(st.session_state.exam_subject_name)["color"]
    if remaining <= 60:
        timer_style = "background:#A23B2E;"
    else:
        timer_style = f"background:{subj_color};"

    c1, c2 = st.columns([3, 1])
    with c1:
        chapter = st.session_state.exam_chapter_info
        st.markdown(f"#### 📝 {chapter['name']} — পরীক্ষা চলছে")
    with c2:
        st.markdown(f"<div class='timer-box' style='{timer_style}'>⏱️ {mins:02d}:{secs:02d}</div>", unsafe_allow_html=True)

    st.markdown(
        f"<div class='subject-meta' style='margin-top:4px;'>উত্তর দেওয়া হয়েছে: "
        f"<b>{answered_count} / {total_count}</b></div>",
        unsafe_allow_html=True
    )
    st.progress(progress_pct / 100)
    st.markdown("---")

    for idx, q in enumerate(questions, start=1):
        with st.container(border=True):
            st.markdown(
                f"<span class='q-number-badge'>{idx}</span>"
                f"<span class='q-text'>{q['question_text']}</span>",
                unsafe_allow_html=True
            )
            if q.get("image_url"):
                st.image(q["image_url"], use_container_width=False, width=380)
            options = {"ক": q["option_ka"], "খ": q["option_kha"], "গ": q["option_ga"], "ঘ": q["option_gha"]}
            already_answered = str(q["id"]) in st.session_state.exam_answers

            if already_answered:
                prev = st.session_state.exam_answers[str(q["id"])]
                rows_html = "<div class='locked-options'>"
                for label, text in options.items():
                    if label == prev:
                        rows_html += (
                            f"<div class='locked-option locked-selected'>"
                            f"<span class='locked-dot'></span>{label}) {text}</div>"
                        )
                    else:
                        rows_html += (
                            f"<div class='locked-option'>"
                            f"<span class='locked-dot-empty'></span>{label}) {text}</div>"
                        )
                rows_html += "</div>"
                st.markdown(rows_html, unsafe_allow_html=True)
            else:
                labels = [f"{k}) {v}" for k, v in options.items()]
                choice = st.radio(
                    f"q_{q['id']}", labels, index=None, key=f"radio_{q['id']}", label_visibility="collapsed"
                )
                if choice:
                    st.session_state.exam_answers[str(q["id"])] = choice.split(")")[0].strip()

            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    st.markdown("---")
    if not st.session_state.confirm_submit_pending:
        if st.button("✅ পরীক্ষা জমা দাও (Submit)", type="primary"):
            st.session_state.confirm_submit_pending = True
            st.rerun()
    else:
        st.warning("আপনি কি সত্যিই পরীক্ষা জমা দিতে চান? জমা দেওয়ার পর আর উত্তর পরিবর্তন করা যাবে না।")
        cyes, cno = st.columns(2)
        with cyes:
            if st.button("✅ হ্যাঁ, জমা দাও", type="primary", key="confirm_submit_yes"):
                st.session_state.confirm_submit_pending = False
                with st.spinner("জমা হচ্ছে..."):
                    try:
                        grade_and_submit()
                    except Exception as e:
                        st.error("⚠️ সাবমিট করতে সমস্যা হয়েছে। নিচের এররটি স্ক্রিনশট নিয়ে জানান:")
                        st.exception(e)
                        st.stop()
                st.rerun()
        with cno:
            if st.button("❌ না, ফিরে যাও", key="confirm_submit_no"):
                st.session_state.confirm_submit_pending = False
                st.rerun()


def exam_result():
    r = st.session_state.exam_submitted_result
    if st.button("🏠 হোমে ফিরে যান", key="home_top_btn"):
        go_home()
        st.rerun()
    render_header()
    st.markdown(
        f'<div class="big-title">🎉 অভিনন্দন, {st.session_state.student_name}!</div>',
        unsafe_allow_html=True
    )
    style = subject_style(r["subject_name"])
    st.markdown(
        f'<div class="subject-meta" style="margin-top:-6px; margin-bottom:14px; display:flex; align-items:center; gap:8px;">'
        f'<span class="subject-icon-badge" style="background:{style["soft"]}; font-size:16px; width:28px; height:28px;">{style["icon"]}</span>'
        f'{r["subject_name"]} — {r["chapter_name"]} পরীক্ষার ফলাফল</div>',
        unsafe_allow_html=True
    )

    pct = round((r["score"] / r["total_marks"]) * 100, 1) if r["total_marks"] else 0
    score_class = "score-good" if pct >= 80 else ("score-mid" if pct >= 50 else "score-low")
    mins, secs = divmod(r["time_taken"], 60)

    st.markdown(
        f"""<div class="score-card {score_class}">
            <div class="score-value">{r['score']} / {r['total_marks']}</div>
            <div class="score-label">প্রাপ্ত নম্বর &nbsp;•&nbsp; {pct}% &nbsp;•&nbsp; সময় লেগেছে {mins} মিনিট {secs} সেকেন্ড</div>
        </div>""",
        unsafe_allow_html=True
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("সঠিক উত্তর", r["correct_count"])
    c2.metric("ভুল উত্তর", r["wrong_count"])
    c3.metric("অনুত্তরিত", r["unanswered_count"])

    st.markdown("---")
    st.markdown('<div class="big-title" style="font-size:20px;">উত্তরপত্র পর্যালোচনা</div>', unsafe_allow_html=True)

    for idx, d in enumerate(r["detail"], start=1):
        if d["is_correct"] is True:
            css = "review-card review-correct"
            tag = "✅ সঠিক"
        elif d["is_correct"] is False:
            css = "review-card review-wrong"
            tag = "❌ ভুল"
        else:
            css = "review-card review-wrong"
            tag = "⚪ অনুত্তরিত"

        rows = f"<div class='{css}'><b>{idx}. {d['question']}</b> — {tag}<br>"
        if d.get("image_url"):
            rows += f"<img src='{d['image_url']}' style='max-width:320px; border-radius:8px; margin:8px 0;' /><br>"
        for label, text in d["options"].items():
            marker = ""
            if label == d["correct"]:
                marker = " <span class='option-correct-tag'>✔️ সঠিক উত্তর</span>"
            if label == d["given"] and label != d["correct"]:
                marker = " <span class='option-wrong-tag'>❌ তোমার উত্তর</span>"
            elif label == d["given"] and label == d["correct"]:
                marker = " <span class='option-correct-tag'>✔️ তোমার উত্তর — সঠিক</span>"
            rows += f"<div class='option-row'>{label}) {text}{marker}</div>"
        rows += "</div>"
        st.markdown(rows, unsafe_allow_html=True)

    if st.button("🏠 হোমপেজে ফিরে যাও"):
        go_home()
        st.rerun()


# ===========================================================================
# রাউটিং
# ===========================================================================
if st.session_state.role == "admin":
    if not st.session_state.admin_authenticated:
        admin_login()
    else:
        admin_panel()
else:
    if not st.session_state.student_registered:
        student_registration()
    elif st.session_state.exam_submitted_result is not None:
        exam_result()
    elif st.session_state.exam_chapter_id is not None:
        exam_taking()
    else:
        subject_selection()
