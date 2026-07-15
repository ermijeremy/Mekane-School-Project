from datetime import date
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Query, Depends
from psycopg import AsyncConnection
from auth import require_student
from db.connection import get_conn
from student import schemas

router = APIRouter()

async def _get_student_row(conn: AsyncConnection, user_id: int) -> dict:
    async with conn.cursor() as cur:
        await cur.execute(
            """SELECT id, current_class_id FROM students WHERE user_id=%s
            """, (user_id,),
        )
    
        user = await cur.fetchone()
    
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No student profile for this account")

    return user

@router.get("/me", response_model=schemas.StudentProfile)
async def get_my_profile(
    user: dict = Depends(require_student),
    conn: AsyncConnection = Depends(get_conn)
):
    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT s.id, s.student_id_number, s.first_name, s.last_name,
                   s.date_of_birth, s.gender, s.phone, s.academic_status,
                   c.name AS class_name, c.grade_level, c.section
            FROM students s
            LEFT JOIN classes c ON c.id = s.current_class_id
            WHERE s.user_id = %s
            """, (user["id"],),
        )

        row = await cur.fetchone()
    
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No student profile for this account")

    return row


@router.get("/attendance", response_model=schemas.AttendanceSummary)
async def get_my_attendance(
    user: dict = Depends(require_student),
    conn: AsyncConnection = Depends(get_conn),
    date_from: Optional[date] = Query(None, alias="from"),
    date_to: Optional[date] = Query(None, alias="to")
):
    student = await _get_student_row(conn, user["id"])

    sql = "SELECT date, status FROM attendance_records WHERE student_id=%s"
    params: list = [student["id"]]
    if date_from:
        sql += " AND date >= %s"
        params.append(date_from)
    if date_to:
        sql += " AND date <= %s"
        params.append(date_to)
    sql += " ORDER BY date DESC"

    async with conn.cursor() as cur:
        await cur.execute(sql, params)
        rows = await cur.fetchall()
    
    counts = {"present": 0, "absent": 0, "late": 0, "excused": 0}

    for r in rows:
        counts[r["status"]] += 1
    
    return {"total": len(rows), **counts, "records": rows}

@router.get("/grades", response_model=list[schemas.GradeRow]) 
async def get_my_grades(
    user: dict = Depends(require_student),
    conn: AsyncConnection = Depends(get_conn)
):
    student = await _get_student_row(conn, user["id"])

    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT a.id   AS assessment_id,
                   a.title,
                   a.type,
                   subj.name AS subject,
                   sc.score,
                   a.max_score,
                   a.date
            FROM assessment_scores sc
            JOIN assessments a               ON a.id = sc.assessment_id
            JOIN class_subject_teachers cst  ON cst.id = a.class_subject_teacher_id
            JOIN subjects subj               ON subj.id = cst.subject_id
            WHERE sc.student_id = %s
              AND a.is_published = TRUE     -- never leak unpublished grades
            ORDER BY a.date DESC NULLS LAST
            """, (student["id"],),
        )

        return await cur.fetchall()

@router.get("/notifications", response_model=list[schemas.NotificationRow])
async def get_my_notification(user: dict = Depends(require_student), conn: AsyncConnection = Depends(get_conn)):
    async with conn.cursor() as cur:
        await cur.execute(
            """
            SELECT id, type, title, body, is_read, created_at
            FROM notifications WHERE user_id = %s
            ORDER BY created_at DESC
            """, (user["id"],),
        )
    
        return await cur.fetchall()

@router.patch("/notifications/{notif_id}/read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notification_read(notif_id: int, user: dict = Depends(require_student), conn: AsyncConnection = Depends(get_conn)):
    async with conn.cursor() as cur:
        await cur.execute(
            """ UPDATE notifications SET is_read = TRUE WHERE id = %s AND user_id = %s
            """, (notif_id, user["id"]),
        )

        if cur.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        
    await conn.commit()
