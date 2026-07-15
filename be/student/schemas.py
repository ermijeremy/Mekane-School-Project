from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel


class StudentProfile(BaseModel):
    id: int
    student_id_number: Optional[str]
    first_name: str
    last_name: str
    date_of_birth: Optional[date]
    gender: str
    phone: Optional[str]
    academic_status: str
    class_name: Optional[str]
    grade_level: Optional[int]
    section: Optional[str]

class AttendanceRow(BaseModel):
    date: date
    status: str

class AttendanceSummary(BaseModel):
    total: int
    present: int
    absent: int
    late: int
    excused: int
    records: list[AttendanceRow]

class GradeRow(BaseModel):
    assessment_id: int
    title: str
    type: str
    subject: str
    score: float
    max_score: float
    date: Optional[date]

class AnnouncementRow(BaseModel):
    id: int
    title: str
    body: str
    type: str
    is_pinned: bool
    published_at: Optional[date]

class NotificationRow(BaseModel):
    id: int
    type: str
    title: str
    body: Optional[str]
    is_read: bool
    created_at: datetime
