"""
Pydantic schemas for all RBAC domain models.
"""
import uuid
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Auth / User ──────────────────────────────────────────────────────────── #

class SyncProfileRequest(BaseModel):
    """
    Sent by the frontend after Supabase sign-up.
    All new users start as STUDENT; role elevation is done by admins.
    """
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    department_id: uuid.UUID | None = None
    year_of_study: int | None = Field(default=None, ge=1, le=8)


class UserProfileOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_demo: bool
    department_id: uuid.UUID | None = None
    year_of_study: int | None = None
    hostel_room_id: uuid.UUID | None = None
    roles: list[str] = []

    model_config = {"from_attributes": True}


# ── Role assignment ───────────────────────────────────────────────────────── #

class AssignRoleRequest(BaseModel):
    role_name: str
    scope_id: uuid.UUID | None = None


class RoleOut(BaseModel):
    id: int
    name: str
    description: str

    model_config = {"from_attributes": True}


class UserRoleOut(BaseModel):
    id: int
    user_id: uuid.UUID
    role_id: int
    role_name: str
    scope_id: uuid.UUID | None = None
    granted_at: datetime

    model_config = {"from_attributes": True}


# ── Department ───────────────────────────────────────────────────────────── #

class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=20)


class DepartmentOut(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Timetable ─────────────────────────────────────────────────────────────── #

class TimetableCreate(BaseModel):
    department_id: uuid.UUID
    semester: int = Field(ge=1, le=8)
    day_of_week: Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    start_time: time
    end_time: time
    subject: str = Field(min_length=1, max_length=100)
    room: str | None = Field(default=None, max_length=50)
    faculty_name: str | None = Field(default=None, max_length=100)

    @field_validator('end_time')
    @classmethod
    def validate_time_order(cls, v, info):
        """Validate that end_time is after start_time"""
        if 'start_time' in info.data and v <= info.data['start_time']:
            raise ValueError('end_time must be after start_time')
        return v


class TimetableOut(BaseModel):
    id: int
    department_id: uuid.UUID
    semester: int
    day_of_week: str
    start_time: time
    end_time: time
    subject: str
    room: str | None = None
    faculty_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TimetableUploadResponse(BaseModel):
    """Response from timetable OCR upload endpoint"""
    success: bool
    message: str
    extracted_text: str = ""
    entries_created: int = 0
    entries: list[TimetableOut] = []
    errors: list[str] = []


class TimetableConfirmRequest(BaseModel):
    """Request body for confirming and saving timetable entries"""
    entries: list[dict] = Field(min_length=1)

    @field_validator('entries')
    @classmethod
    def validate_entries(cls, v):
        """Validate each entry has required fields"""
        if not v:
            raise ValueError("At least one timetable entry is required")
        
        valid_days = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}
        
        for idx, entry in enumerate(v):
            # Validate required fields
            if 'day_of_week' not in entry:
                raise ValueError(f"Entry {idx}: day_of_week is required")
            if 'start_time' not in entry:
                raise ValueError(f"Entry {idx}: start_time is required")
            if 'end_time' not in entry:
                raise ValueError(f"Entry {idx}: end_time is required")
            if 'subject' not in entry:
                raise ValueError(f"Entry {idx}: subject is required")
            
            # Validate day_of_week
            if entry['day_of_week'] not in valid_days:
                raise ValueError(f"Entry {idx}: day_of_week must be one of {valid_days}")
            
            # Validate subject length
            if not entry['subject'] or len(entry['subject']) > 100:
                raise ValueError(f"Entry {idx}: subject must be between 1 and 100 characters")
            
            # Validate optional field lengths
            if 'room' in entry and entry['room'] and len(entry['room']) > 50:
                raise ValueError(f"Entry {idx}: room must not exceed 50 characters")
            
            if 'faculty_name' in entry and entry['faculty_name'] and len(entry['faculty_name']) > 100:
                raise ValueError(f"Entry {idx}: faculty_name must not exceed 100 characters")
            
            # Validate semester if provided
            if 'semester' in entry:
                semester = entry['semester']
                if not isinstance(semester, int) or semester < 1 or semester > 8:
                    raise ValueError(f"Entry {idx}: semester must be between 1 and 8")
        
        return v


# ── Exam Schedule ─────────────────────────────────────────────────────────── #

class ExamScheduleCreate(BaseModel):
    department_id: uuid.UUID
    semester: int = Field(ge=1, le=8)
    subject: str = Field(min_length=1, max_length=100)
    exam_date: date
    start_time: time
    room: str | None = None


class ExamScheduleOut(BaseModel):
    id: int
    department_id: uuid.UUID
    semester: int
    subject: str
    exam_date: date
    start_time: time
    room: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Holiday ───────────────────────────────────────────────────────────────── #

class HolidayCreate(BaseModel):
    holiday_date: date
    description: str = Field(min_length=1, max_length=255)


class HolidayOut(BaseModel):
    id: int
    holiday_date: date
    description: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Hostel ────────────────────────────────────────────────────────────────── #

class HostelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class HostelOut(BaseModel):
    id: uuid.UUID
    name: str
    warden_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class HostelRoomCreate(BaseModel):
    hostel_id: uuid.UUID
    room_number: str = Field(min_length=1, max_length=20)
    capacity: int = Field(default=2, ge=1, le=10)


class HostelRoomOut(BaseModel):
    id: uuid.UUID
    hostel_id: uuid.UUID
    room_number: str
    capacity: int

    model_config = {"from_attributes": True}


# ── Mess Menu ─────────────────────────────────────────────────────────────── #

class MessMenuCreate(BaseModel):
    hostel_id: uuid.UUID
    week_start: date
    day_of_week: str
    meal_type: Literal["breakfast", "lunch", "snacks", "dinner"]
    items: str = Field(min_length=1)
    is_special: bool = False


class MessMenuOut(BaseModel):
    id: int
    hostel_id: uuid.UUID
    week_start: date
    day_of_week: str
    meal_type: str
    items: str
    is_special: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class MessNoticeCreate(BaseModel):
    hostel_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)


class MessNoticeOut(BaseModel):
    id: int
    hostel_id: uuid.UUID
    title: str
    body: str
    created_by: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Placement ─────────────────────────────────────────────────────────────── #

class PlacementDriveCreate(BaseModel):
    company_name: str = Field(min_length=1, max_length=150)
    job_role: str = Field(min_length=1, max_length=150)
    package_lpa: float | None = Field(default=None, ge=0)
    drive_date: date | None = None
    registration_deadline: date | None = None
    description: str = ""


class PlacementDriveOut(BaseModel):
    id: uuid.UUID
    company_name: str
    job_role: str
    package_lpa: float | None = None
    drive_date: date | None = None
    registration_deadline: date | None = None
    description: str
    is_active: bool
    created_by: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PlacementNoticeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)
    drive_id: uuid.UUID | None = None


class PlacementNoticeOut(BaseModel):
    id: int
    title: str
    body: str
    drive_id: uuid.UUID | None = None
    created_by: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Clubs ─────────────────────────────────────────────────────────────────── #

class ClubCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    club_type: Literal["technical", "cultural", "sports", "other"] = "technical"
    description: str = ""


class ClubOut(BaseModel):
    id: uuid.UUID
    name: str
    club_type: str
    description: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Notices ───────────────────────────────────────────────────────────────── #

class NoticeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)
    domain: Literal["academic", "hostel", "placement", "clubs", "general"]
    target_department_id: uuid.UUID | None = None
    is_pinned: bool = False


class NoticeOut(BaseModel):
    id: uuid.UUID
    title: str
    body: str
    domain: str
    target_department_id: uuid.UUID | None = None
    created_by: uuid.UUID | None = None
    is_pinned: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Events ────────────────────────────────────────────────────────────────── #

class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    domain: Literal["academic", "hostel", "placement", "clubs", "general"]
    event_date: date
    venue: str | None = None
    requires_registration: bool = False
    registration_deadline: date | None = None


class EventOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    domain: str
    event_date: date
    venue: str | None = None
    requires_registration: bool
    registration_deadline: date | None = None
    created_by: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Assignments ───────────────────────────────────────────────────────────── #

class AssignmentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = ""
    subject: str = Field(min_length=1, max_length=100)
    due_date: date
    file_url: str | None = None
    department_id: uuid.UUID
    semester: int | None = Field(default=None, ge=1, le=8)


class AssignmentOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str
    subject: str
    due_date: date
    file_url: str | None = None
    department_id: uuid.UUID
    semester: int | None = None
    faculty_id: uuid.UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── AI ────────────────────────────────────────────────────────────────────── #

class AIQueryRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)


class AIQueryResponse(BaseModel):
    reply: str
    context_used: list[str] = []
