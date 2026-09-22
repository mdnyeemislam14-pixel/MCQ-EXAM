# -*- coding: utf-8 -*-
"""
question_parser.py — একসাথে অনেকগুলো প্রশ্ন পেস্ট করলে তা পার্স করার লজিক।

প্রত্যাশিত ফরম্যাট (প্রতিটি প্রশ্ন একটি ব্লক, একাধিক ব্লক একের পর এক):

প্রশ্ন: বাংলাদেশের রাজধানীর নাম কী?
ক) চট্টগ্রাম
খ) ঢাকা
গ) সিলেট
ঘ) রাজশাহী
উত্তর: খ

- "প্রশ্ন:" লেখা না দিলেও চলবে (ঐচ্ছিক)
- উত্তর "উত্তর:" বা "উত্তরঃ" বা শুধু অক্ষর হতে পারে (ক/খ/গ/ঘ)
- উত্তর সঠিক অপশনের টেক্সট দিয়েও দেওয়া যাবে (ক অক্ষরের বদলে)
"""

import re

OPTION_LABELS = ["ক", "খ", "গ", "ঘ"]

# একটি প্রশ্ন ব্লক শনাক্ত করার জন্য প্যাটার্ন
_BLOCK_PATTERN = re.compile(
    r"""
    (?:প্রশ্ন\s*[:।\.]?\s*)?          # ঐচ্ছিক "প্রশ্ন:" শব্দ
    (?P<question>.+?)                  # প্রশ্নের লেখা
    \s*\n\s*ক\s*[)।.]\s*(?P<ka>.+?)
    \s*\n\s*খ\s*[)।.]\s*(?P<kha>.+?)
    \s*\n\s*গ\s*[)।.]\s*(?P<ga>.+?)
    \s*\n\s*ঘ\s*[)।.]\s*(?P<gha>.+?)
    \s*\n\s*উত্তর\s*[:ঃ।\.]?\s*(?P<ans>.+?)
    \s*(?=\n\s*(?:প্রশ্ন\s*[:।\.]?\s*)?.+?\n\s*ক\s*[)।.]|\Z)
    """,
    re.VERBOSE | re.DOTALL,
)


def _normalize_answer(ans_text, ka, kha, ga, gha):
    """উত্তর ফিল্ডকে ক/খ/গ/ঘ অক্ষরে রূপান্তর করে।"""
    ans_text = ans_text.strip().strip(".।)")
    # সরাসরি অক্ষর দেওয়া থাকলে
    for label in OPTION_LABELS:
        if ans_text == label or ans_text.startswith(label + ")") or ans_text.startswith(label + "."):
            return label
    # উত্তরে অপশনের টেক্সট মিলিয়ে দেখা
    options = {"ক": ka, "খ": kha, "গ": ga, "ঘ": gha}
    for label, text in options.items():
        if ans_text.strip() == text.strip():
            return label
    return None


def parse_questions(raw_text):
    """
    raw_text থেকে প্রশ্নগুলো পার্স করে একটি তালিকা রিটার্ন করে:
    [{"question":..., "ka":..., "kha":..., "ga":..., "gha":..., "answer": "ক"/"খ"/"গ"/"ঘ"}, ...]

    এবং পার্স করতে না পারা অংশগুলোর একটি তালিকা (errors) রিটার্ন করে।
    """
    text = raw_text.strip()
    if not text:
        return [], []

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # একাধিক ফাঁকা লাইনকে একটায় নামিয়ে আনা, কিন্তু লাইন গঠন ঠিক রাখা
    text = re.sub(r"\n{2,}", "\n", text)

    results = []
    errors = []

    matches = list(_BLOCK_PATTERN.finditer(text))

    if not matches:
        errors.append("কোনো প্রশ্ন সঠিক ফরম্যাটে পাওয়া যায়নি। অনুগ্রহ করে ফরম্যাট যাচাই করুন।")
        return results, errors

    consumed_end = 0
    for m in matches:
        question = m.group("question").strip()
        ka = m.group("ka").strip()
        kha = m.group("kha").strip()
        ga = m.group("ga").strip()
        gha = m.group("gha").strip()
        ans_raw = m.group("ans").strip()

        answer = _normalize_answer(ans_raw, ka, kha, ga, gha)

        if not question or not ka or not kha or not ga or not gha:
            errors.append(f"অসম্পূর্ণ প্রশ্ন উপেক্ষা করা হলো: {question[:50]}...")
            continue

        if answer is None:
            errors.append(f"'{question[:40]}...' প্রশ্নের সঠিক উত্তর (ক/খ/গ/ঘ) বোঝা যায়নি, উপেক্ষা করা হলো।")
            continue

        results.append({
            "question": question,
            "ka": ka,
            "kha": kha,
            "ga": ga,
            "gha": gha,
            "answer": answer,
        })
        consumed_end = m.end()

    # ম্যাচের বাইরে অবশিষ্ট টেক্সট থাকলে (আংশিক প্রশ্ন) সতর্ক করা
    leftover = text[consumed_end:].strip()
    if leftover and len(leftover) > 5:
        errors.append("শেষে কিছু টেক্সট প্যাটার্নে মেলেনি, তাই বাদ পড়েছে — অনুগ্রহ করে চেক করুন।")

    return results, errors
