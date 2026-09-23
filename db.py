# -*- coding: utf-8 -*-
"""
db.py — Supabase (PostgreSQL) ডাটাবেজ লেয়ার

MCQ পরীক্ষা প্ল্যাটফর্মের সব ডাটা (বিষয়, অধ্যায়, প্রশ্ন, পরীক্ষার সেটিংস, ফলাফল)
এখন Supabase-এ সংরক্ষিত হয়, যাতে Streamlit Cloud রিস্টার্ট/রিডিপ্লয় হলেও ডেটা না হারায়।

app.py এবং question_parser.py-তে কোনো পরিবর্তনের দরকার নেই — এই ফাইলের সব ফাংশনের
নাম ও ইনপুট-আউটপুট আগের sqlite3 ভার্সনের মতোই রাখা হয়েছে।
"""

import json
import datetime
import streamlit as st
from supabase import create_client, Client

FIXED_SUBJECTS = ["জীববিজ্ঞান", "পদার্থবিজ্ঞান", "রসায়ন"]
BD_TZ = datetime.timezone(datetime.timedelta(hours=6))


def bd_now_iso():
    """সার্ভার যে টাইমজোনেই থাকুক না কেন, সবসময় বাংলাদেশ সময় (UTC+6) রিটার্ন করে"""
    return datetime.datetime.now(BD_TZ).isoformat()


@st.cache_resource
def _get_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


supabase = _get_client()


def init_db():
    """টেবিল Supabase SQL Editor দিয়ে আগেই তৈরি করা হয়েছে।
    এখানে শুধু ফিক্সড তিনটি বিষয় সিড করা হচ্ছে (না থাকলে)।"""
    existing = supabase.table("subjects").select("name").execute().data
    existing_names = {row["name"] for row in existing}
    for name in FIXED_SUBJECTS:
        if name not in existing_names:
            supabase.table("subjects").insert({"name": name}).execute()


# ---------------- বিষয় (Subjects) ----------------

@st.cache_data(ttl=5)
def get_subjects():
    res = supabase.table("subjects").select("*").order("id").execute()
    return res.data


def get_subject_by_name(name):
    res = supabase.table("subjects").select("*").eq("name", name).execute()
    return res.data[0] if res.data else None


# ---------------- অধ্যায় (Chapters) ----------------

@st.cache_data(ttl=5)
def get_chapters(subject_id):
    res = (
        supabase.table("chapters")
        .select("*")
        .eq("subject_id", subject_id)
        .order("sort_order")
        .order("id")
        .execute()
    )
    return res.data


def get_chapter(chapter_id):
    res = supabase.table("chapters").select("*").eq("id", chapter_id).execute()
    return res.data[0] if res.data else None


def add_chapter(subject_id, name):
    existing = (
        supabase.table("chapters")
        .select("sort_order")
        .eq("subject_id", subject_id)
        .order("sort_order", desc=True)
        .limit(1)
        .execute()
        .data
    )
    next_order = (existing[0]["sort_order"] + 1) if existing else 1

    res = (
        supabase.table("chapters")
        .insert({"subject_id": subject_id, "name": name.strip(), "sort_order": next_order})
        .execute()
    )
    chapter_id = res.data[0]["id"]

    supabase.table("exam_config").insert(
        {"chapter_id": chapter_id, "updated_at": bd_now_iso()}
    ).execute()

    get_chapters.clear()
    return chapter_id


def update_chapter(chapter_id, name):
    supabase.table("chapters").update({"name": name.strip()}).eq("id", chapter_id).execute()
    get_chapters.clear()


def delete_chapter(chapter_id):
    supabase.table("chapters").delete().eq("id", chapter_id).execute()
    get_chapters.clear()
    get_active_chapter_for_subject.clear()


# ---------------- প্রশ্ন (Questions) ----------------

@st.cache_data(ttl=5)
def get_questions(chapter_id):
    res = (
        supabase.table("questions")
        .select("*")
        .eq("chapter_id", chapter_id)
        .order("id")
        .execute()
    )
    return res.data


def get_question(question_id):
    res = supabase.table("questions").select("*").eq("id", question_id).execute()
    return res.data[0] if res.data else None


def add_question(chapter_id, question_text, ka, kha, ga, gha, correct_option):
    supabase.table("questions").insert(
        {
            "chapter_id": chapter_id,
            "question_text": question_text.strip(),
            "option_ka": ka.strip(),
            "option_kha": kha.strip(),
            "option_ga": ga.strip(),
            "option_gha": gha.strip(),
            "correct_option": correct_option.strip(),
            "created_at": bd_now_iso(),
        }
    ).execute()
    get_questions.clear()


def add_questions_bulk(chapter_id, parsed_questions):
    """parsed_questions: question_parser.parse_questions() থেকে আসা তালিকা"""
    now = bd_now_iso()
    rows = [
        {
            "chapter_id": chapter_id,
            "question_text": q["question"],
            "option_ka": q["ka"],
            "option_kha": q["kha"],
            "option_ga": q["ga"],
            "option_gha": q["gha"],
            "correct_option": q["answer"],
            "created_at": now,
        }
        for q in parsed_questions
    ]
    if rows:
        supabase.table("questions").insert(rows).execute()
        get_questions.clear()


def update_question(question_id, question_text, ka, kha, ga, gha, correct_option):
    supabase.table("questions").update(
        {
            "question_text": question_text.strip(),
            "option_ka": ka.strip(),
            "option_kha": kha.strip(),
            "option_ga": ga.strip(),
            "option_gha": gha.strip(),
            "correct_option": correct_option.strip(),
        }
    ).eq("id", question_id).execute()
    get_questions.clear()


def delete_question(question_id):
    supabase.table("questions").delete().eq("id", question_id).execute()
    get_questions.clear()


# ---------------- পরীক্ষার সেটিংস (Exam Config) ----------------

@st.cache_data(ttl=5)
def get_exam_config(chapter_id):
    res = supabase.table("exam_config").select("*").eq("chapter_id", chapter_id).execute()
    if res.data:
        return res.data[0]

    supabase.table("exam_config").insert(
        {"chapter_id": chapter_id, "updated_at": bd_now_iso()}
    ).execute()
    res = supabase.table("exam_config").select("*").eq("chapter_id", chapter_id).execute()
    return res.data[0]


def update_exam_config(chapter_id, duration_minutes, marks_per_question, negative_marks=0):
    supabase.table("exam_config").update(
        {
            "duration_minutes": duration_minutes,
            "marks_per_question": marks_per_question,
            "negative_marks": negative_marks,
            "updated_at": bd_now_iso(),
        }
    ).eq("chapter_id", chapter_id).execute()
    get_exam_config.clear()


def set_exam_active(chapter_id, active):
    """একটি অধ্যায়ের পরীক্ষা চালু করলে একই বিষয়ের অন্য সব অধ্যায়ের পরীক্ষা বন্ধ হয়ে যাবে
    (একসাথে একটির বেশি পরীক্ষা 'চলছে' দেখানো হবে না, বিভ্রান্তি এড়াতে)।"""
    if active:
        chapter = get_chapter(chapter_id)
        if chapter:
            siblings = get_chapters(chapter["subject_id"])
            sibling_ids = [c["id"] for c in siblings]
            if sibling_ids:
                supabase.table("exam_config").update({"is_active": False}).in_(
                    "chapter_id", sibling_ids
                ).execute()

    supabase.table("exam_config").update(
        {"is_active": bool(active), "updated_at": bd_now_iso()}
    ).eq("chapter_id", chapter_id).execute()
    get_exam_config.clear()
    get_active_chapter_for_subject.clear()


@st.cache_data(ttl=5)
def get_active_chapter_for_subject(subject_id):
    chapters = get_chapters(subject_id)
    if not chapters:
        return None
    chapter_ids = [c["id"] for c in chapters]

    res = (
        supabase.table("exam_config")
        .select("chapter_id")
        .in_("chapter_id", chapter_ids)
        .eq("is_active", True)
        .execute()
    )
    if not res.data:
        return None

    active_id = res.data[0]["chapter_id"]
    for c in chapters:
        if c["id"] == active_id:
            return c
    return None


# ---------------- ফলাফল (Submissions) ----------------

def save_submission(
    student_name, student_class, chapter_id, subject_name, chapter_name,
    answers, total_questions, correct_count, wrong_count, unanswered_count,
    score, total_marks, time_taken_seconds,
):
    res = (
        supabase.table("submissions")
        .insert(
            {
                "student_name": student_name.strip(),
                "student_class": student_class.strip(),
                "chapter_id": chapter_id,
                "subject_name": subject_name,
                "chapter_name": chapter_name,
                "answers_json": json.dumps(answers, ensure_ascii=False),
                "total_questions": total_questions,
                "correct_count": correct_count,
                "wrong_count": wrong_count,
                "unanswered_count": unanswered_count,
                "score": score,
                "total_marks": total_marks,
                "time_taken_seconds": time_taken_seconds,
                "submitted_at": bd_now_iso(),
            }
        )
        .execute()
    )
    return res.data[0]["id"]


def get_submissions_for_chapter(chapter_id):
    res = (
        supabase.table("submissions")
        .select("*")
        .eq("chapter_id", chapter_id)
        .order("score", desc=True)
        .order("time_taken_seconds")
        .execute()
    )
    return res.data


def get_all_submissions():
    res = (
        supabase.table("submissions")
        .select("*")
        .order("submitted_at", desc=True)
        .execute()
    )
    return res.data
