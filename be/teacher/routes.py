from datetime import date
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Query, Depends
from psycopg import AsyncConnection
from auth import require_teacher
from db.connection import get_conn
from teacher import schemas

router = APIRouter()

async def _get_teacher_row(conn: AsyncConnection, user_id:int) -> dict:
    async with conn.cursor() as cur:
        await cur.execute(
            """ SELECT id FROM teachers WHERE user_id = %s AND is_active = True
            """, (user_id,),
        )

        teacher = await cur.fetchone()
    
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No teacher profile for this account")
    
    return teacher

async def _assert_teaches_class(conn: AsyncConnection, teacher_id: int, class_id: int):
    async with conn.cursor() as cur:
        await cur.execute(
            """  SELECT 1 FROM classes c LEFT JOIN class_subject_teachers cst 
            ON cst.class_id = c.id AND cst.teacher_id = %s WHERE c.id = %s AND 
            (c.homeroom_teacher_id = %s OR cst.id IS NOT NULL) LIMIT 1
            """, (teacher_id, class_id, teacher_id),
        )

        row = await cur.fetchone()
    
    if row is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not assigned to this class")


@router.get("/me", response_model=schemas.TeacherProfile)
async def get_my_profile(
    user: dict = Depends(require_teacher),
    conn: AsyncConnection = Depends(get_conn)
):
    async with conn.cursor() as cur:
        await cur.execute(
            """ SELECT id, first_name, last_name, phone, photo_url, hire_date
            FROM teachers WHERE user_id = %s
            """, (user["id"],),
        )

        row = await cur.fetchone()

    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No teacher profile for this account")

    return row

@router.get("/classes", response_model=schemas.MyClasses)
async def get_my_classes(
    user: dict = Depends(require_teacher),
    conn: AsyncConnection = Depends(get_conn)
):
    teacher = await _get_teacher_row(conn, user["id"])
    
    async with conn.cursor() as cur:
        await cur.execute(
            """ SELECT cst.id AS cst_id, c.id AS class_id, c.name AS class_name,
                   c.grade_level, c.section, c.room,
                   subj.id AS subject_id, subj.name AS subject
            FROM class_subject_teachers cst
            JOIN classes c    ON c.id = cst.class_id
            JOIN subjects subj ON subj.id = cst.subject_id
            WHERE cst.teacher_id = %s
            ORDER BY c.grade_level, c.section, subj.name
            """, (teacher["id"],),
        )

        teaching = await cur.fetchall()

        await cur.execute(
            """SELECT id AS class_id, name AS class_name, grade_level, section, room
            FROM classes
            WHERE homeroom_teacher_id = %s
            ORDER BY grade_level, section
            """, (teacher["id"],),
        )

        homeroom = await cur.fetchall()

    return {"teaching": teaching, "homeroom": homeroom}

@router.get("/classes/{class_id}/students", response_model=list[schemas.StudentRow])
async def get_class_students(
    class_id: int,
    user: dict = Depends(require_teacher),
    conn: AsyncConnection = Depends(get_conn)
):
    teacher = await _get_teacher_row(conn, user["id"])
    await _assert_teaches_class(conn, teacher["id"], class_id)

    async with conn.cursor() as cur:
        await cur.execute(
            """ SELECT id, student_id_number, first_name, last_name, gender, academic_status
            FROM students WHERE current_class_id = %s 
            ORDER BY first_name, last_name
            """, (class_id,),
        )

        return await cur.fetchall()

@router.post("/classes/{class_id}/attendance", status_code=status.HTTP_204_NO_CONTENT)
async def mark_attendance(
    class_id: int,
    body: schemas.AttendanceMarkRequest,
    user: dict = Depends(require_teacher),
    conn: AsyncConnection = Depends(get_conn)
):
    teacher = await _get_teacher_row(conn, user["id"])

    async with conn.cursor() as cur:
        await cur.execute(
            """ SELECT homeroom_teacher_id FROM classes WHERE  id = %s
            """, (class_id,),
        )

        clas = await cur.fetchone()

        if clas is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class Not found")
        
        if clas["homeroom_teacher_id"] != teacher["id"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the homeroom teacher can record attendance")
        
        await cur.execute(
            "SELECT id FROM students WHERE current_class_id = %s", (class_id, ),
        )

        valid_ids = {row["id"] for row in await cur.fetchall()}

        bad = [e.student_id for e in body.entries if e.student_id not in valid_ids]

        if bad:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Students not in this class: {bad}")
        
        await cur.executemany(
            """
            INSERT INTO attendance_records (student_id, class_id, date, status, recorded_by)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (student_id, date)
            DO UPDATE SET status = EXCLUDED.status,
                          recorded_by = EXCLUDED.recorded_by,
                          updated_at = NOW()
            """,
            [(e.student_id, class_id, body.date, e.status, teacher["id"])
             for e in body.entries],
        )

@router.get("/classes/{class_id}/attendance", response_model=list[schemas.AttendanceReportRow])
async def get_class_attendance(
    class_id: int,
    user: dict = Depends(require_teacher),
    conn: AsyncConnection = Depends(get_conn),
    date_from: Optional[date] = Query(None, alias="from"),
    date_to: Optional[date] = Query(None, alias="to")
):
    teacher = await _get_teacher_row(conn, user["id"])
    await _assert_teaches_class(conn, teacher["id"], class_id)

    sql = """
        SELECT ar.student_id, s.first_name, s.last_name, ar.date, ar.status
        FROM attendance_records ar
        JOIN students s ON s.id = ar.student_id
        WHERE ar.class_id = %s
    """
    params: list = [class_id]
    if date_from:
        sql += " AND ar.date >= %s"
        params.append(date_from)
    if date_to:
        sql += " AND ar.date <= %s"
        params.append(date_to)
    sql += " ORDER BY ar.date DESC, s.last_name, s.first_name"

    async with conn.cursor() as cur:
        await cur.execute(sql, params)
        return await cur.fetchall()


@router.post("/assessments", status_code=status.HTTP_201_CREATED)
async def create_assessment(
    body: schemas.AssessmentCreate,
    user: dict = Depends(require_teacher),
    conn: AsyncConnection = Depends(get_conn)
):
    teacher = await _get_teacher_row(conn, user["id"])
    
    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT cst.id, c.academic_year_id
            FROM class_subject_teachers cst
            JOIN classes c ON c.id = cst.class_id
            WHERE cst.id = %s AND cst.teacher_id = %s
            """, (body.cst_id, teacher["id"]),
        )

        cst = await cur.fetchone()
        if cst is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't teach this class-subject")

        await cur.execute(
            """
            INSERT INTO assessments
                (class_subject_teacher_id, academic_year_id, title, type, max_score, date)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (body.cst_id, cst["academic_year_id"], body.title,
             body.type, body.max_score, body.date),
        )

        row = await cur.fetchone()

    return {"id": row["id"]}


@router.get("/assessments", response_model=list[schemas.AssessmentRow])
async def get_my_assessments(
    user: dict = Depends(require_teacher),
    conn: AsyncConnection = Depends(get_conn)
):
    teacher = await _get_teacher_row(conn, user["id"])
    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT a.id, a.title, a.type, a.max_score, a.date, a.is_published,
                   c.name AS class_name, subj.name AS subject,
                   COUNT(sc.id) AS scores_recorded
            FROM assessments a
            JOIN class_subject_teachers cst ON cst.id = a.class_subject_teacher_id
            JOIN classes c    ON c.id = cst.class_id
            JOIN subjects subj ON subj.id = cst.subject_id
            LEFT JOIN assessment_scores sc ON sc.assessment_id = a.id
            WHERE cst.teacher_id = %s
            GROUP BY a.id, c.name, subj.name
            ORDER BY a.date DESC NULLS LAST, a.id DESC
            """, (teacher["id"],),
        )

        return await cur.fetchall()


@router.post("/assessments/{assessment_id}/scores", status_code=status.HTTP_204_NO_CONTENT)
async def record_scores(
    assessment_id: int,
    body: schemas.ScoreRequest,
    user: dict = Depends(require_teacher),
    conn: AsyncConnection = Depends(get_conn)
):
    teacher = await _get_teacher_row(conn, user["id"])

    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT a.max_score, cst.class_id
            FROM assessments a
            JOIN class_subject_teachers cst ON cst.id = a.class_subject_teacher_id
            WHERE a.id = %s AND cst.teacher_id = %s
            """, (assessment_id, teacher["id"]),
        )
        assessment = await cur.fetchone()
        if assessment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Assessment not found")

        too_high = [e.student_id for e in body.scores
                    if e.score > float(assessment["max_score"])]
        if too_high:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Score exceeds max_score for students: {too_high}")

        await cur.execute(
            "SELECT id FROM students WHERE current_class_id = %s",
            (assessment["class_id"],),
        )
        valid_ids = {row["id"] for row in await cur.fetchall()}
        bad = [e.student_id for e in body.scores if e.student_id not in valid_ids]
        if bad:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Students not in this class: {bad}")

        await cur.executemany(
            """
            INSERT INTO assessment_scores (assessment_id, student_id, score, note, recorded_by)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (assessment_id, student_id)
            DO UPDATE SET score = EXCLUDED.score,
                          note = EXCLUDED.note,
                          recorded_by = EXCLUDED.recorded_by,
                          recorded_at = NOW()
            """,
            [(assessment_id, e.student_id, e.score, e.note, teacher["id"])
             for e in body.scores],
        )


@router.patch("/assessments/{assessment_id}/publish")
async def publish_assessment(
    assessment_id: int,
    user: dict = Depends(require_teacher),
    conn: AsyncConnection = Depends(get_conn),
):
    teacher = await _get_teacher_row(conn, user["id"])

    async with conn.cursor() as cur:
        await cur.execute(
            """
            UPDATE assessments a
            SET is_published = TRUE
            FROM class_subject_teachers cst
            WHERE a.id = %s
              AND cst.id = a.class_subject_teacher_id
              AND cst.teacher_id = %s
            RETURNING a.title
            """, (assessment_id, teacher["id"]),
        )
        updated = await cur.fetchone()
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Assessment not found")

        # Notify every student who has a score on this assessment.
        await cur.execute(
            """
            INSERT INTO notifications
                (user_id, sender_id, type, title, body, reference_type, reference_id)
            SELECT s.user_id, %s, 'grade_published',
                   %s, 'Your grade has been published.', 'assessment', %s
            FROM assessment_scores sc
            JOIN students s ON s.id = sc.student_id
            WHERE sc.assessment_id = %s AND s.user_id IS NOT NULL
            """,
            (user["id"], f"Grade published: {updated['title']}", assessment_id,
             assessment_id),
        )
        notified = cur.rowcount

    return {"published": True, "students_notified": notified}


