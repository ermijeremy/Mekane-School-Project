from datetime import date
from typing import Optional, Literal
from pydantic import BaseModel, Field

class TeacherProfile(BaseModel):
    id: int
    first_name: str
    last_name: str
    phone: str
    photo_url: Optional[str]
    hire_date: Optional[date]

class TeachingRow(BaseModel):
    cst_id: int
    class_id: int
    class_name: Optional[str]
    grade_level: int
    section: str
    room: Optional[str]
    subject_id: int
    subject: str

class HomeroomRow(BaseModel):
    class_id: int
    class_name: Optional[str]
    grade_level: int
    section: str
    room: Optional[str]

class MyClasses(BaseModel):
    teaching: list[TeachingRow]
    homeroom: list[HomeroomRow]

class StudentRow(BaseModel):
    id: int
    student_id_number: Optional[str]
    first_name: str
    last_name: str
    gender: str
    academic_status: str

class AttendanceEntry(BaseModel):
    student_id: int
    status: Literal["present", "absent", "late", "excused"]

class AttendanceMarkRequest(BaseModel):
    date: date
    entries: list[AttendanceEntry] = Field(min_length=1)

class AttendanceReportRow(BaseModel):
    student_id: int
    first_name: str
    last_name: str
    date: date
    status: str

class AssessmentCreate(BaseModel):
    cst_id: int
    title: str = Field(min_length=1, max_length=255)
    type: Literal["quiz", "midterm", "final", "project", "other"]
    max_score: float = Field(default=100, gt=0)
    date: Optional[date] = None

class AssessmentRow(BaseModel):
    id: int
    title:str
    type: str
    max_score: float
    date: Optional[date]
    is_published: bool
    class_name: Optional[str]
    subject: str
    scores_recorded: int

class ScoreEntry(BaseModel):
    student_id: int
    score: float = Field(ge=0)
    note: Optional[str] = None

class ScoreRequest(BaseModel):
    scores: list[ScoreEntry] = Field(min_length=1)