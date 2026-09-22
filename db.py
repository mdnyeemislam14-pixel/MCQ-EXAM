# -*- coding: utf-8 -*-
"""
db.py — SQLite ডাটাবেজ লেয়ার
MCQ পরীক্ষা প্ল্যাটফর্মের সব ডাটা (বিষয়, অধ্যায়, প্রশ্ন, পরীক্ষার সেটিংস, ফলাফল) এখানে সংরক্ষিত হয়।
"""

import sqlite3
import json
import datetime
from contextlib import contextmanager

DB_PATH = "exam_data.db"

FIXED_SUBJECTS = ["জীববিজ্ঞান", "পদার্থবিজ্ঞান", "রসায়ন"]


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chapter_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                option_ka TEXT NOT NULL,
                option_kha TEXT NOT NULL,
                option_ga TEXT NOT NULL,
                option_gha TEXT NOT NULL,
                correct_option TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS exam_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chapter_id INTEGER UNIQUE NOT NULL,
                duration_minutes INTEGER DEFAULT 20,
                marks_per_question REAL DEFAULT 1,
                negative_marks REAL DEFAULT 0,
                is_active INTEGER DEFAULT 0,
                updated_at TEXT,
                FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_name TEXT NOT NULL,
                student_class TEXT NOT NULL,
                chapter_id INTEGER NOT NULL,
                subject_name TEXT NOT NULL,
                chapter_name TEXT NOT NULL,
                answers_json TEXT NOT NULL,
                total_questions INTEGER NOT NULL,
                correct_count INTEGER NOT NULL,
                wrong_count INTEGER NOT NULL,
                unanswered_count INTEGER NOT NULL,
                score REAL NOT NULL,
                total_marks REAL NOT NULL,
                time_taken_seconds INTEGER,
                submitted_at TEXT NOT NULL
            )
        """)
        conn.commit()

        # ফিক্সড তিনটি বিষয় সিড করা (না থাকলে)
        for name in FIXED_SUBJECTS:
            c.execute("INSERT OR IGNORE INTO subjects (name) VALUES (?)", (name,))
        conn.commit()


# ---------------- বিষয় (Subjects) ----------------

def get_subjects():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM subjects ORDER BY id").fetchall()
        return [dict(r) for r in rows]


def get_subject_by_name(name):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM subjects WHERE name=?", (name,)).fetchone()
        return dict(row) if row else None


# ---------------- অধ্যায় (Chapters) ----------------

def get_chapters(subject_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM chapters WHERE subject_id=? ORDER BY sort_order, id",
            (subject_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_chapter(chapter_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM chapters WHERE id=?", (chapter_id,)).fetchone()
        return dict(row) if row else None


def add_chapter(subject_id, name):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO chapters (subject_id, name, sort_order) VALUES (?, ?, "
            "(SELECT COALESCE(MAX(sort_order), 0) + 1 FROM chapters WHERE subject_id=?))",
            (subject_id, name.strip(), subject_id)
        )
        chapter_id = cur.lastrowid
        conn.execute(
            "INSERT OR IGNORE INTO exam_config (chapter_id, updated_at) VALUES (?, ?)",
            (chapter_id, datetime.datetime.now().isoformat())
        )
        return chapter_id


def update_chapter(chapter_id, name):
    with get_conn() as conn:
        conn.execute("UPDATE chapters SET name=? WHERE id=?", (name.strip(), chapter_id))


def delete_chapter(chapter_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM chapters WHERE id=?", (chapter_id,))


# ---------------- প্রশ্ন (Questions) ----------------

def get_questions(chapter_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM questions WHERE chapter_id=? ORDER BY id", (chapter_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_question(question_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM questions WHERE id=?", (question_id,)).fetchone()
        return dict(row) if row else None


def add_question(chapter_id, question_text, ka, kha, ga, gha, correct_option):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO questions
            (chapter_id, question_text, option_ka, option_kha, option_ga, option_gha, correct_option, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (chapter_id, question_text.strip(), ka.strip(), kha.strip(), ga.strip(), gha.strip(),
              correct_option.strip(), datetime.datetime.now().isoformat()))


def add_questions_bulk(chapter_id, parsed_questions):
    """parsed_questions: question_parser.parse_questions() থেকে আসা তালিকা"""
    with get_conn() as conn:
        now = datetime.datetime.now().isoformat()
        conn.executemany("""
            INSERT INTO questions
            (chapter_id, question_text, option_ka, option_kha, option_ga, option_gha, correct_option, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (chapter_id, q["question"], q["ka"], q["kha"], q["ga"], q["gha"], q["answer"], now)
            for q in parsed_questions
        ])


def update_question(question_id, question_text, ka, kha, ga, gha, correct_option):
    with get_conn() as conn:
        conn.execute("""
            UPDATE questions SET question_text=?, option_ka=?, option_kha=?, option_ga=?, option_gha=?, correct_option=?
            WHERE id=?
        """, (question_text.strip(), ka.strip(), kha.strip(), ga.strip(), gha.strip(),
              correct_option.strip(), question_id))


def delete_question(question_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM questions WHERE id=?", (question_id,))


# ---------------- পরীক্ষার সেটিংস (Exam Config) ----------------

def get_exam_config(chapter_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM exam_config WHERE chapter_id=?", (chapter_id,)).fetchone()
        if row:
            return dict(row)
        # না থাকলে ডিফল্ট তৈরি করা
        conn.execute(
            "INSERT INTO exam_config (chapter_id, updated_at) VALUES (?, ?)",
            (chapter_id, datetime.datetime.now().isoformat())
        )
        row = conn.execute("SELECT * FROM exam_config WHERE chapter_id=?", (chapter_id,)).fetchone()
        return dict(row)


def update_exam_config(chapter_id, duration_minutes, marks_per_question, negative_marks=0):
    with get_conn() as conn:
        conn.execute("""
            UPDATE exam_config SET duration_minutes=?, marks_per_question=?, negative_marks=?, updated_at=?
            WHERE chapter_id=?
        """, (duration_minutes, marks_per_question, negative_marks,
              datetime.datetime.now().isoformat(), chapter_id))


def set_exam_active(chapter_id, active):
    """একটি অধ্যায়ের পরীক্ষা চালু করলে একই বিষয়ের অন্য সব অধ্যায়ের পরীক্ষা বন্ধ হয়ে যাবে
    (একসাথে একটির বেশি পরীক্ষা 'চলছে' দেখানো হবে না, বিভ্রান্তি এড়াতে)।"""
    with get_conn() as conn:
        if active:
            chapter = conn.execute("SELECT subject_id FROM chapters WHERE id=?", (chapter_id,)).fetchone()
            if chapter:
                subject_id = chapter["subject_id"]
                sibling_ids = [r["id"] for r in conn.execute(
                    "SELECT id FROM chapters WHERE subject_id=?", (subject_id,)
                ).fetchall()]
                if sibling_ids:
                    q_marks = ",".join("?" * len(sibling_ids))
                    conn.execute(
                        f"UPDATE exam_config SET is_active=0 WHERE chapter_id IN ({q_marks})",
                        sibling_ids
                    )
        conn.execute(
            "UPDATE exam_config SET is_active=?, updated_at=? WHERE chapter_id=?",
            (1 if active else 0, datetime.datetime.now().isoformat(), chapter_id)
        )


def get_active_chapter_for_subject(subject_id):
    with get_conn() as conn:
        row = conn.execute("""
            SELECT c.* FROM chapters c
            JOIN exam_config e ON e.chapter_id = c.id
            WHERE c.subject_id=? AND e.is_active=1
            LIMIT 1
        """, (subject_id,)).fetchone()
        return dict(row) if row else None


# ---------------- ফলাফল (Submissions) ----------------

def save_submission(student_name, student_class, chapter_id, subject_name, chapter_name,
                     answers, total_questions, correct_count, wrong_count, unanswered_count,
                     score, total_marks, time_taken_seconds):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO submissions
            (student_name, student_class, chapter_id, subject_name, chapter_name, answers_json,
             total_questions, correct_count, wrong_count, unanswered_count, score, total_marks,
             time_taken_seconds, submitted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (student_name.strip(), student_class.strip(), chapter_id, subject_name, chapter_name,
              json.dumps(answers, ensure_ascii=False), total_questions, correct_count, wrong_count,
              unanswered_count, score, total_marks, time_taken_seconds,
              datetime.datetime.now().isoformat()))
        return conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]


def get_submissions_for_chapter(chapter_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM submissions WHERE chapter_id=? ORDER BY score DESC, time_taken_seconds ASC",
            (chapter_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_submissions():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM submissions ORDER BY submitted_at DESC").fetchall()
        return [dict(r) for r in rows]
