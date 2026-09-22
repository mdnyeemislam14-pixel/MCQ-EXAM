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
            active_ch = db.get_active_chapter_for_subject(s["id"])
            if active_ch:
                running_any = True
                cfg = db.get_exam_config(active_ch["id"])
                st.markdown(
                    f"- **{s['name']}** → *{active_ch['name']}* "
                    f"(সময়: {cfg['duration_minutes']} মিনিট, প্রতি প্রশ্নে মার্ক: {cfg['marks_per_question']}) "
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
                "ফরম্যাট: প্রশ্ন → ক) খ) গ) ঘ) → উত্তর: ক/খ/গ/ঘ  |  প্রতিটি প্রশ্নের পর একটি নতুন লাইন দিন।"
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
                        colA, colB = st.columns(2)
                        with colA:
                            save = st.form_submit_button("💾 সংরক্ষণ করুন")
                        with colB:
                            delete = st.form_submit_button("🗑️ মুছে ফেলুন")

                        if save:
                            db.update_question(q["id"], qt, ka, kha, ga, gha, ans)
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
                save_cfg = st.form_submit_button("💾 সেটিংস সংরক্ষণ করুন")
                if save_cfg:
                    db.update_exam_config(chapter_id3, int(duration), marks, neg)
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
                        "জমার সময়": s["submitted_at"][:16].replace("T", " "),
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
    st.markdown('<div class="big-title">📝 অনলাইন MCQ পরীক্ষায় স্বাগতম</div>', unsafe_allow_html=True)
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


def subject_selection():
    st.markdown(
        f'<div class="big-title">স্বাগতম, {st.session_state.student_name} '
        f'({st.session_state.student_class})</div>',
        unsafe_allow_html=True
    )
    st.write("নিচে থেকে বিষয় ও অধ্যায় নির্বাচন করে পরীক্ষা শুরু করো।")

    subjects = db.get_subjects()
    cols = st.columns(len(subjects))

    for col, subj in zip(cols, subjects):
        with col:
            active_ch = db.get_active_chapter_for_subject(subj["id"])
            st.markdown(f"#### {subj['name']}")
            if active_ch:
                st.markdown("<span class='exam-running'>● পরীক্ষা চলছে</span>", unsafe_allow_html=True)
            else:
                st.markdown("<span class='exam-not-running'>কোনো পরীক্ষা চলছে না</span>", unsafe_allow_html=True)

            chapters = db.get_chapters(subj["id"])
            if not chapters:
                st.caption("এখনো কোনো অধ্যায় নেই।")
                continue

            chapter_names = [c["name"] for c in chapters]
            chosen = st.selectbox("অধ্যায় নির্বাচন করো", chapter_names, key=f"select_ch_{subj['id']}")
            chosen_chapter = next(c for c in chapters if c["name"] == chosen)
            cfg = db.get_exam_config(chosen_chapter["id"])
            q_count = len(db.get_questions(chosen_chapter["id"]))

            is_running = active_ch is not None and active_ch["id"] == chosen_chapter["id"]

            if is_running:
                st.caption(f"সময়: {cfg['duration_minutes']} মিনিট | মোট প্রশ্ন: {q_count} | "
                           f"পূর্ণমান: {q_count * cfg['marks_per_question']}")
                if st.button("🚀 পরীক্ষা শুরু করো", key=f"start_{subj['id']}"):
                    st.session_state.exam_chapter_id = chosen_chapter["id"]
                    st.session_state.exam_questions = db.get_questions(chosen_chapter["id"])
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
    cfg = db.get_exam_config(chapter_id)
    chapter = db.get_chapter(chapter_id)
    subject = db.get_subjects()
    subject_name = next((s["name"] for s in subject if s["id"] == chapter["subject_id"]), "")

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
    cfg = db.get_exam_config(st.session_state.exam_chapter_id)
    duration_seconds = cfg["duration_minutes"] * 60
    elapsed = time.time() - st.session_state.exam_start_time
    remaining = int(duration_seconds - elapsed)

    if remaining <= 0:
        grade_and_submit()
        st.rerun()
        return

    st_autorefresh(interval=1000, key="exam_timer_refresh")

    mins, secs = divmod(remaining, 60)
    timer_class = "timer-box timer-warning" if remaining <= 60 else "timer-box"
    c1, c2 = st.columns([3, 1])
    with c1:
        chapter = db.get_chapter(st.session_state.exam_chapter_id)
        st.markdown(f"#### 📝 {chapter['name']} — পরীক্ষা চলছে")
    with c2:
        st.markdown(f"<div class='{timer_class}'>⏱️ {mins:02d}:{secs:02d}</div>", unsafe_allow_html=True)

    st.markdown("---")

    questions = st.session_state.exam_questions
    for idx, q in enumerate(questions, start=1):
        st.markdown(f"**{idx}. {q['question_text']}**")
        options = {"ক": q["option_ka"], "খ": q["option_kha"], "গ": q["option_ga"], "ঘ": q["option_gha"]}
        labels = [f"{k}) {v}" for k, v in options.items()]
        prev = st.session_state.exam_answers.get(str(q["id"]))
        prev_idx = ["ক", "খ", "গ", "ঘ"].index(prev) if prev else None
        choice = st.radio(
            f"q_{q['id']}", labels, index=prev_idx, key=f"radio_{q['id']}", label_visibility="collapsed"
        )
        if choice:
            st.session_state.exam_answers[str(q["id"])] = choice.split(")")[0].strip()
        st.markdown("")

    st.markdown("---")
    if st.button("✅ পরীক্ষা জমা দাও (Submit)", type="primary"):
        grade_and_submit()
        st.rerun()


def exam_result():
    r = st.session_state.exam_submitted_result
    st.markdown(f'<div class="big-title">📊 ফলাফল — {r["chapter_name"]}</div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("প্রাপ্ত নম্বর", f"{r['score']} / {r['total_marks']}")
    c2.metric("সঠিক উত্তর", r["correct_count"])
    c3.metric("ভুল উত্তর", r["wrong_count"])
    c4.metric("অনুত্তরিত", r["unanswered_count"])

    mins, secs = divmod(r["time_taken"], 60)
    st.caption(f"সময় লেগেছে: {mins} মিনিট {secs} সেকেন্ড")

    st.markdown("---")
    st.markdown("#### উত্তরপত্র পর্যালোচনা")
    for idx, d in enumerate(r["detail"], start=1):
        if d["is_correct"] is True:
            css = "correct-answer"
            tag = "✅ সঠিক"
        elif d["is_correct"] is False:
            css = "wrong-answer"
            tag = "❌ ভুল"
        else:
            css = "wrong-answer"
            tag = "⚪ অনুত্তরিত"

        st.markdown(f"**{idx}. {d['question']}** — {tag}")
        for label, text in d["options"].items():
            marker = ""
            if label == d["correct"]:
                marker = " ✔️ (সঠিক উত্তর)"
            if label == d["given"] and label != d["correct"]:
                marker = " ❌ (তোমার উত্তর)"
            elif label == d["given"] and label == d["correct"]:
                marker = " ✔️ (তোমার উত্তর — সঠিক)"
            st.markdown(f"&nbsp;&nbsp;{label}) {text}{marker}", unsafe_allow_html=True)
        st.markdown("")

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
