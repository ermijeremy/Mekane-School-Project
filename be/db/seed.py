"""
seed.py — Execute schema.sql then populate the database with realistic sample data.

Usage:
    python seed.py

Environment variables (or edit config.py):
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
"""

import os
import sys
import random
from datetime import date, timedelta, datetime, timezone

import psycopg2
from psycopg2.extras import execute_values

# Import shared config
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import CONFIG, HASHED_PASSWORD, SCHEMA_FILE

# HELPERS

def rand_phone() -> str:
    return f"+2519{''.join([str(random.randint(0, 9)) for _ in range(8)])}"

def rand_date(start: date, end: date) -> date:
    return start + timedelta(days=random.randint(0, (end - start).days))

def now() -> datetime:
    return datetime.now(timezone.utc)


# MAIN

def main():
    conn = psycopg2.connect(**CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # 1. Create tables
        print("→ Running schema.sql …")
        with open(SCHEMA_FILE, "r") as f:
            cur.execute(f.read())

        # 2. School info
        print("→ Seeding school_info …")
        cur.execute("""
            INSERT INTO school_info
                (id, name, address, phone, email, website,
                 principal_name, principal_message, established_year)
            VALUES
                (1, 'Sunrise Academy', '123 Education Lane, Addis Ababa',
                 '+251911000001', 'info@sunriseacademy.et', 'https://sunriseacademy.et',
                 'Dr. Almaz Bekele',
                 'Welcome to Sunrise Academy — where every student is empowered to excel.',
                 1998)
            ON CONFLICT (id) DO NOTHING;
        """)

        # 3. Academic years
        print("→ Seeding academic_years …")
        cur.execute("""
            INSERT INTO academic_years (name, start_date, end_date, is_current)
            VALUES
                ('2023-2024 Semester 1', '2023-09-01', '2024-01-31', FALSE),
                ('2023-2024 Semester 2', '2024-02-01', '2024-06-30', FALSE),
                ('2024-2025 Semester 1', '2024-09-01', '2025-01-31', TRUE)
            RETURNING id;
        """)
        ay_ids = [row[0] for row in cur.fetchall()]
        current_ay_id = ay_ids[2]   # 2024-2025 Sem 1

        # 4. Users — admins
        print("→ Seeding admin users …")
        admin_data = [
            ("admin1@school.et", "admin"),
            ("admin2@school.et", "admin"),
        ]
        # username = email local part (e.g. admin1)
        cur.executemany("""
            INSERT INTO users (role, username, email, password_hash)
            VALUES (%s, %s, %s, %s)
        """, [(r, e.split("@")[0], e, HASHED_PASSWORD) for e, r in admin_data])

        cur.execute("SELECT id FROM users WHERE role = 'admin' ORDER BY id")
        admin_user_ids = [row[0] for row in cur.fetchall()]

        admin_profiles = [
            (admin_user_ids[0], "Tigist",   "Hailu",   rand_phone()),
            (admin_user_ids[1], "Bereket",  "Tadesse",  rand_phone()),
        ]
        execute_values(cur, """
            INSERT INTO admins (user_id, first_name, last_name, phone) VALUES %s
        """, admin_profiles)

        cur.execute("SELECT id FROM admins ORDER BY id")
        admin_ids = [row[0] for row in cur.fetchall()]

        # 5. Users — teachers
        print("→ Seeding teachers …")
        teacher_data = [
            ("Abebe",      "Girma"),
            ("Selamawit",  "Tesfaye"),
            ("Dawit",      "Alemu"),
            ("Hiwot",      "Mulugeta"),
            ("Yonas",      "Bekele"),
            ("Meron",      "Tadesse"),
            ("Kebede",     "Worku"),
            ("Azeb",       "Haile"),
        ]
        teacher_emails = [
            f"teacher{i+1}@school.et" for i in range(len(teacher_data))
        ]
        # username = email local part (e.g. teacher1)
        cur.executemany("""
            INSERT INTO users (role, username, email, password_hash) VALUES (%s, %s, %s, %s)
        """, [("teacher", e.split("@")[0], e, HASHED_PASSWORD) for e in teacher_emails])

        cur.execute("SELECT id FROM users WHERE role = 'teacher' ORDER BY id")
        teacher_user_ids = [row[0] for row in cur.fetchall()]

        execute_values(cur, """
            INSERT INTO teachers (user_id, first_name, last_name, phone, hire_date)
            VALUES %s
        """, [
            (teacher_user_ids[i],
             teacher_data[i][0],
             teacher_data[i][1],
             rand_phone(),
             rand_date(date(2015, 1, 1), date(2023, 8, 31)))
            for i in range(len(teacher_data))
        ])

        cur.execute("SELECT id FROM teachers ORDER BY id")
        teacher_ids = [row[0] for row in cur.fetchall()]

        # 6. Classes
        print("→ Seeding classes …")
        class_specs = [
            (current_ay_id, 9,  "A", "Grade 9A",  "Room 101", teacher_ids[0]),
            (current_ay_id, 9,  "B", "Grade 9B",  "Room 102", teacher_ids[1]),
            (current_ay_id, 10, "A", "Grade 10A", "Room 201", teacher_ids[2]),
            (current_ay_id, 10, "B", "Grade 10B", "Room 202", teacher_ids[3]),
            (current_ay_id, 11, "A", "Grade 11A", "Room 301", teacher_ids[4]),
            (current_ay_id, 11, "B", "Grade 11B", "Room 302", teacher_ids[5]),
            (current_ay_id, 12, "A", "Grade 12A", "Room 401", teacher_ids[6]),
            (current_ay_id, 12, "B", "Grade 12B", "Room 402", teacher_ids[7]),
        ]
        execute_values(cur, """
            INSERT INTO classes
                (academic_year_id, grade_level, section, name, room, homeroom_teacher_id)
            VALUES %s
        """, class_specs)
        cur.execute("SELECT id FROM classes ORDER BY id")
        class_ids = [row[0] for row in cur.fetchall()]

        # 7. Subjects
        print("→ Seeding subjects …")
        subjects = [
            ("Mathematics",        "MATH"),
            ("English Language",   "ENG"),
            ("Physics",            "PHY"),
            ("Chemistry",          "CHEM"),
            ("Biology",            "BIO"),
            ("History",            "HIST"),
            ("Geography",          "GEO"),
            ("Physical Education", "PE"),
        ]
        execute_values(cur, """
            INSERT INTO subjects (name, code) VALUES %s
        """, subjects)
        cur.execute("SELECT id FROM subjects ORDER BY id")
        subject_ids = [row[0] for row in cur.fetchall()]

        # 8. class_subject_teachers
        print("→ Seeding class_subject_teachers …")
        cst_rows = []
        for cls_id in class_ids:
            for j, subj_id in enumerate(subject_ids[:4]):
                cst_rows.append((cls_id, subj_id, teacher_ids[j % len(teacher_ids)]))

        execute_values(cur, """
            INSERT INTO class_subject_teachers (class_id, subject_id, teacher_id)
            VALUES %s
        """, cst_rows)
        cur.execute("SELECT id FROM class_subject_teachers ORDER BY id")
        cst_ids = [row[0] for row in cur.fetchall()]

        # 9. Users — students
        print("→ Seeding students …")
        student_first = ["Naol","Liya","Biruk","Eden","Robel","Sara","Yohannes","Hana",
                          "Mikias","Tigist","Abel","Marta","Fiker","Kiya","Solomon","Rahel",
                          "Amir","Blen","Daniel","Tsion"]
        student_last  = ["Tesfaye","Alemu","Bekele","Girma","Hailu","Tadesse","Worku","Kebede"]

        student_first_names = [random.choice(student_first) for _ in range(40)]
        student_last_names  = [random.choice(student_last)  for _ in range(40)]
        student_emails      = [f"student{i+1}@school.et" for i in range(40)]
        # Student username == student_id_number, generated at approval time.
        student_id_numbers  = [f"STU{2024000 + i + 1}" for i in range(40)]

        cur.executemany("""
            INSERT INTO users (role, username, email, password_hash) VALUES (%s, %s, %s, %s)
        """, [("student", student_id_numbers[i], student_emails[i], HASHED_PASSWORD)
              for i in range(40)])

        cur.execute("SELECT id FROM users WHERE role = 'student' ORDER BY id")
        student_user_ids = [row[0] for row in cur.fetchall()]

        # 5 students per class (8 classes × 5 = 40)
        student_rows = []
        for i in range(40):
            cls_id = class_ids[i // 5]
            student_rows.append((
                student_user_ids[i],
                student_id_numbers[i],
                student_first_names[i],
                student_last_names[i],
                rand_date(date(2006, 1, 1), date(2010, 12, 31)),
                random.choice(["male", "female"]),
                rand_phone(),
                cls_id,
                "active",
            ))

        execute_values(cur, """
            INSERT INTO students
                (user_id, student_id_number, first_name, last_name, date_of_birth,
                 gender, phone, current_class_id, academic_status)
            VALUES %s
        """, student_rows)
        cur.execute("SELECT id FROM students ORDER BY id")
        student_ids = [row[0] for row in cur.fetchall()]

        # 10. Enrollments
        print("→ Seeding enrollments …")
        enroll_rows = [
            (student_ids[i], class_ids[i // 5], current_ay_id, "active")
            for i in range(40)
        ]
        execute_values(cur, """
            INSERT INTO enrollments (student_id, class_id, academic_year_id, status)
            VALUES %s
        """, enroll_rows)

        # 11. Registration applications
        print("→ Seeding registration_applications …")
        statuses = ["pending_review", "approved", "rejected", "waiting_for_payment", "registered"]
        app_rows = []
        for i in range(10):
            st = statuses[i % len(statuses)]
            app_rows.append((
                f"Applicant{i+1}",
                "Tesfaye",
                rand_date(date(2008, 1, 1), date(2011, 12, 31)),
                random.choice(["male", "female"]),
                "Addis Ababa",
                rand_phone(),
                f"applicant{i+1}@gmail.com",
                random.choice([9, 10, 11]),
                current_ay_id,
                f"Guardian {i+1}",
                "parent",
                rand_phone(),
                st,
                "Rejection due to incomplete documents" if st == "rejected" else None,
                250.00 if st in ("waiting_for_payment", "registered") else None,
            ))

        execute_values(cur, """
            INSERT INTO registration_applications
                (first_name, last_name, date_of_birth, gender, address, phone, email,
                 grade_level, academic_year_id, guardian_name, guardian_relation,
                 guardian_phone, status, rejection_reason, payment_amount)
            VALUES %s
        """, app_rows)
        cur.execute("SELECT id FROM registration_applications ORDER BY id")
        app_ids = [row[0] for row in cur.fetchall()]

        # Attach a document to each application
        doc_rows = [(aid, "birth_certificate",
                     f"https://files.school.et/docs/birth_{aid}.pdf",
                     f"birth_certificate_{aid}.pdf")
                    for aid in app_ids]
        execute_values(cur, """
            INSERT INTO registration_documents
                (application_id, document_type, file_url, file_name)
            VALUES %s
        """, doc_rows)

        # 12. Attendance records
        print("→ Seeding attendance_records …")
        att_rows = []
        school_days = [date(2024, 9, 1) + timedelta(days=d)
                       for d in range(30)
                       if (date(2024, 9, 1) + timedelta(days=d)).weekday() < 5]

        for i, stu_id in enumerate(student_ids):
            cls_id       = class_ids[i // 5]
            homeroom_tid = teacher_ids[i // 5]
            for day in school_days[:10]:   # first 10 school days
                att_rows.append((
                    stu_id, cls_id, day,
                    random.choices(
                        ["present", "absent", "late", "excused"],
                        weights=[85, 7, 5, 3]
                    )[0],
                    homeroom_tid,
                ))

        execute_values(cur, """
            INSERT INTO attendance_records
                (student_id, class_id, date, status, recorded_by)
            VALUES %s
            ON CONFLICT (student_id, date) DO NOTHING
        """, att_rows)

        # 13. Assessments
        print("→ Seeding assessments …")
        assessment_rows = []
        for cst_id in cst_ids[:8]:    # first 8 CST rows (one per class for MATH)
            for atype, title, adate in [
                ("quiz",    "Chapter 1 Quiz",     date(2024, 10, 5)),
                ("midterm", "Midterm Examination", date(2024, 11, 15)),
                ("project", "Group Project",       date(2024, 12, 1)),
            ]:
                assessment_rows.append(
                    (cst_id, current_ay_id, title, atype, 100, adate, True)
                )

        execute_values(cur, """
            INSERT INTO assessments
                (class_subject_teacher_id, academic_year_id, title, type,
                 max_score, date, is_published)
            VALUES %s
        """, assessment_rows)
        cur.execute("SELECT id FROM assessments ORDER BY id")
        assessment_ids = [row[0] for row in cur.fetchall()]

        # 14. Assessment scores
        print("→ Seeding assessment_scores …")
        score_rows = []
        for a_idx, assess_id in enumerate(assessment_ids):
            cls_index    = a_idx // 3
            stu_slice    = student_ids[cls_index * 5: cls_index * 5 + 5]
            recorder_tid = teacher_ids[cls_index % len(teacher_ids)]
            for stu_id in stu_slice:
                score_rows.append((
                    assess_id, stu_id,
                    round(random.uniform(45, 100), 2),
                    recorder_tid,
                ))

        execute_values(cur, """
            INSERT INTO assessment_scores
                (assessment_id, student_id, score, recorded_by)
            VALUES %s
            ON CONFLICT (assessment_id, student_id) DO NOTHING
        """, score_rows)

        # 15. Announcements
        print("→ Seeding announcements …")
        ann_rows = [
            ("Welcome Back!", "A warm welcome to all students for the new semester.",
             "school_wide", None, admin_user_ids[0], True, True, True),
            ("Exam Schedule Released", "Midterm exams run Nov 15–20. Check your timetable.",
             "exam_schedule", None, admin_user_ids[0], True, False, True),
            ("Grade 9A Parent Meeting", "Parents of Grade 9A are invited on Oct 10 at 3 PM.",
             "class", class_ids[0], admin_user_ids[1], True, False, False),
            ("Emergency Drill", "Fire drill scheduled for Oct 3 at 10 AM.",
             "emergency", None, admin_user_ids[0], True, True, True),
        ]
        execute_values(cur, """
            INSERT INTO announcements
                (title, body, type, target_class_id, published_by,
                 is_published, is_pinned, is_public)
            VALUES %s
        """, ann_rows)
        cur.execute("SELECT id FROM announcements ORDER BY id")
        ann_ids = [row[0] for row in cur.fetchall()]

        # 16. Notifications
        print("→ Seeding notifications …")
        notif_rows = []

        for stu_uid in student_user_ids[:10]:
            notif_rows.append((
                stu_uid, None, "announcement",
                "Welcome Back!", "A warm welcome to all students for the new semester.",
                "announcement", ann_ids[0],
            ))

        grade9a_student_uids = [student_user_ids[i] for i in range(5)]
        for uid in grade9a_student_uids:
            notif_rows.append((
                uid, None, "announcement",
                "Exam Schedule Released", "Midterm exams run Nov 15–20.",
                "announcement", ann_ids[1],
            ))

        for uid in student_user_ids[:3]:
            notif_rows.append((
                uid, admin_user_ids[0], "warning",
                "Attendance Warning",
                "Your attendance has dropped below 80%. Please improve your attendance.",
                "attendance_record", None,
            ))

        for uid in student_user_ids[:5]:
            notif_rows.append((
                uid, None, "grade_published",
                "Quiz Grade Published", "Your Chapter 1 Quiz grade has been published.",
                "assessment", assessment_ids[0],
            ))

        for admin_uid in admin_user_ids:
            notif_rows.append((
                admin_uid, None, "registration",
                "New Registration Submitted",
                "A new student registration application has been submitted.",
                "registration_application", app_ids[0],
            ))

        execute_values(cur, """
            INSERT INTO notifications
                (user_id, sender_id, type, title, body, reference_type, reference_id)
            VALUES %s
        """, notif_rows)

        # 17. Contact inquiries
        print("→ Seeding contact_inquiries …")
        execute_values(cur, """
            INSERT INTO contact_inquiries (full_name, email, phone, subject, message)
            VALUES %s
        """, [
            ("Aster Bekele",  "aster@gmail.com",   rand_phone(),
             "Admission Inquiry", "I would like to know the requirements for Grade 10 admission."),
            ("Tesfaye Girma", "tesfaye@gmail.com", rand_phone(),
             "Fee Structure",    "Could you please share the school fee structure for 2024-2025?"),
            ("Mulu Alemu",    "mulu@gmail.com",    rand_phone(),
             "General",         "What extracurricular activities does the school offer?"),
        ])

        # 18. Staff profiles
        print("→ Seeding staff_profiles …")
        execute_values(cur, """
            INSERT INTO staff_profiles (first_name, last_name, role_title, bio, order_index)
            VALUES %s
        """, [
            ("Almaz",     "Bekele",  "Principal",
             "Dr. Almaz has led Sunrise Academy for 12 years with a focus on academic excellence.", 1),
            ("Kebede",    "Worku",   "Vice Principal",
             "Oversees daily school operations and student discipline.", 2),
            ("Tigist",    "Hailu",   "Head of Academics",
             "Coordinates curriculum development and teacher training.", 3),
            ("Abebe",     "Girma",   "Mathematics Teacher",
             "15 years of experience teaching mathematics at secondary level.", 4),
            ("Selamawit", "Tesfaye", "English Teacher",
             "Passionate about literature and language arts.", 5),
        ])

        conn.commit()
        print("\n✅  Database seeded successfully.")
        print(f"    academic_years : {len(ay_ids)}")
        print(f"    teachers       : {len(teacher_ids)}")
        print(f"    classes        : {len(class_ids)}")
        print(f"    subjects       : {len(subject_ids)}")
        print(f"    students       : {len(student_ids)}")
        print(f"    assessments    : {len(assessment_ids)}")
        print(f"    notifications  : {len(notif_rows)}")

    except Exception as exc:
        conn.rollback()
        print(f"\n❌  Error — rolled back.\n{exc}")
        raise

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
