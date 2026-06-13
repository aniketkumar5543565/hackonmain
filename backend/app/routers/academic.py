"""
Academic router — timetable, exam schedules, holidays.
Read: all authenticated users.
Write: SUPER_ADMIN, ACADEMIC_ADMIN.
"""
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import AcademicWrite, CurrentUser
from app.models.academic import Department, ExamSchedule, Holiday, Timetable
from app.schemas.campus import (
    DepartmentOut,
    ExamScheduleCreate,
    ExamScheduleOut,
    HolidayCreate,
    HolidayOut,
    TimetableCreate,
    TimetableOut,
    TimetableUploadResponse,
)
from app.services.ocr import parse_timetable_image, parse_time

router = APIRouter(prefix="/academic", tags=["academic"])
DB = Annotated[AsyncSession, Depends(get_db)]


# ── Departments (public read) ─────────────────────────────────────────────── #

@router.get("/departments", response_model=list[DepartmentOut])
async def list_departments(_user: CurrentUser, db: DB) -> list[DepartmentOut]:
    result = await db.execute(select(Department).order_by(Department.code))
    return [DepartmentOut.model_validate(d) for d in result.scalars().all()]


# ── Timetable ─────────────────────────────────────────────────────────────── #

@router.get("/timetable", response_model=list[TimetableOut])
async def get_timetable(
    current_user: CurrentUser,
    db: DB,
    department_id: uuid.UUID | None = None,
    semester: int | None = None,
) -> list[TimetableOut]:
    query = select(Timetable)
    dept_id = department_id or current_user.department_id
    if dept_id:
        query = query.where(Timetable.department_id == dept_id)
    if semester:
        query = query.where(Timetable.semester == semester)
    query = query.order_by(Timetable.day_of_week, Timetable.start_time)
    result = await db.execute(query)
    return [TimetableOut.model_validate(t) for t in result.scalars().all()]


@router.post("/timetable", response_model=TimetableOut, status_code=status.HTTP_201_CREATED)
async def create_timetable_entry(
    body: TimetableCreate,
    _admin: AcademicWrite,
    db: DB,
) -> TimetableOut:
    entry = Timetable(**body.model_dump())
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return TimetableOut.model_validate(entry)


@router.delete("/timetable/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_timetable_entry(
    entry_id: int,
    _admin: AcademicWrite,
    db: DB,
) -> None:
    result = await db.execute(select(Timetable).where(Timetable.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Timetable entry not found")
    await db.delete(entry)
    await db.commit()


@router.post("/timetable/upload", response_model=TimetableUploadResponse)
async def upload_timetable_image(
    admin: AcademicWrite,
    db: DB,
    file: UploadFile = File(...),
) -> TimetableUploadResponse:
    """
    Upload a timetable image (JPEG/PNG) for OCR parsing.
    Uses Groq Vision API to extract schedule information.
    Returns parsed entries for frontend review WITHOUT database write.
    
    **Only Academic Admins can upload timetables.**
    """
    # Validate file type
    if file.content_type not in ["image/jpeg", "image/png"]:
        return TimetableUploadResponse(
            success=False,
            message="Invalid file type. Only JPEG and PNG images are supported.",
            errors=["Unsupported file format"],
        )

    # Validate file size (10 MB limit)
    file_content = await file.read()
    if len(file_content) > 10 * 1024 * 1024:
        return TimetableUploadResponse(
            success=False,
            message="File size exceeds 10 MB limit.",
            errors=["File too large"],
        )

    # Check if file is empty
    if len(file_content) == 0:
        return TimetableUploadResponse(
            success=False,
            message="Uploaded file is empty",
            errors=["File is empty"],
        )

    # Ensure admin has department assigned
    if not admin.department_id:
        return TimetableUploadResponse(
            success=False,
            message="Admin user must be assigned to a department before uploading timetables.",
            errors=["No department assigned"],
        )

    try:
        # Parse timetable from image using OCR
        ocr_result = await parse_timetable_image(file_content)

        if not ocr_result["success"]:
            return TimetableUploadResponse(
                success=False,
                message="Failed to parse timetable image.",
                extracted_text=ocr_result.get("extracted_text", ""),
                errors=ocr_result.get("errors", ["OCR parsing failed"]),
            )

        entries = ocr_result.get("entries", [])
        if not entries:
            return TimetableUploadResponse(
                success=True,
                message="Image processed but no timetable entries were extracted. Please try a clearer image.",
                extracted_text=ocr_result.get("extracted_text", ""),
                errors=["No entries extracted from image"],
            )

        # Validate and convert parsed entries to TimetableOut format
        # WITHOUT database write - just return for frontend review
        parsed_entries = []
        for entry_data in entries:
            try:
                # Validate required fields
                if not all(k in entry_data for k in ["day_of_week", "start_time", "end_time", "subject"]):
                    continue

                # Parse time values
                start_time = parse_time(entry_data["start_time"])
                end_time = parse_time(entry_data["end_time"])

                # Create entry object for response (without database ID or created_at)
                # Using a mock TimetableOut structure
                parsed_entry = TimetableOut(
                    id=0,  # Temporary ID since not saved yet
                    department_id=admin.department_id,
                    semester=entry_data.get("semester", 1),
                    day_of_week=entry_data["day_of_week"],
                    start_time=start_time,
                    end_time=end_time,
                    subject=entry_data["subject"],
                    room=entry_data.get("room"),
                    faculty_name=entry_data.get("faculty_name"),
                    created_at=datetime.now(),  # Temporary timestamp
                )
                parsed_entries.append(parsed_entry)
            except (ValueError, KeyError) as e:
                continue

        return TimetableUploadResponse(
            success=True,
            message=f"Successfully parsed {len(parsed_entries)} timetable entries. Review and confirm to save.",
            extracted_text=ocr_result.get("extracted_text", ""),
            entries_created=0,  # No entries created yet - awaiting confirmation
            entries=parsed_entries,
            errors=ocr_result.get("errors", []),
        )

    except Exception as e:
        return TimetableUploadResponse(
            success=False,
            message=f"Error processing timetable upload: {str(e)}",
            errors=[str(e)],
        )


@router.post("/timetable/confirm", response_model=TimetableUploadResponse)
async def confirm_timetable(
    body: TimetableConfirmRequest,
    admin: AcademicWrite,
    db: DB,
) -> TimetableUploadResponse:
    """
    Confirm and save reviewed timetable entries with atomic replacement.
    Deletes all existing timetable entries for the admin's department and inserts new ones.
    
    **Only Academic Admins can confirm timetables.**
    """
    # Validate user has department_id assigned
    if not admin.department_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin user must be assigned to a department before saving timetables.",
        )

    # Validate entries array is not empty (schema validator handles this)
    if not body.entries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one timetable entry is required",
        )

    try:
        # Begin atomic transaction with timeout
        async with db.begin_nested():
            # Set transaction timeout to 60 seconds
            await db.execute("SET LOCAL statement_timeout = '60s'")

            # Step 1: Delete existing timetable entries for this department
            delete_stmt = delete(Timetable).where(
                Timetable.department_id == admin.department_id
            )
            await db.execute(delete_stmt)

            # Step 2: Insert new timetable entries
            new_entries = []
            for entry_data in body.entries:
                try:
                    # Parse time strings
                    start_time = parse_time(entry_data["start_time"])
                    end_time = parse_time(entry_data["end_time"])

                    # Validate time order
                    if start_time >= end_time:
                        continue  # Skip invalid entries

                    # Create new timetable entry
                    timetable_entry = Timetable(
                        department_id=admin.department_id,
                        semester=entry_data.get("semester", 1),
                        day_of_week=entry_data["day_of_week"],
                        start_time=start_time,
                        end_time=end_time,
                        subject=entry_data["subject"],
                        room=entry_data.get("room"),
                        faculty_name=entry_data.get("faculty_name"),
                    )
                    db.add(timetable_entry)
                    new_entries.append(timetable_entry)

                except (ValueError, KeyError) as e:
                    # Skip invalid entries
                    continue

            # Flush to get IDs but don't commit yet
            await db.flush()

        # Commit the transaction (outer transaction)
        await db.commit()

        # Refresh entries to get all fields including created_at
        for entry in new_entries:
            await db.refresh(entry)

        # Convert to response format
        response_entries = [TimetableOut.model_validate(entry) for entry in new_entries]

        return TimetableUploadResponse(
            success=True,
            message=f"Successfully saved {len(new_entries)} timetable entries.",
            entries_created=len(new_entries),
            entries=response_entries,
            errors=[],
        )

    except Exception as e:
        # Rollback happens automatically
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database transaction failed. No changes were saved: {str(e)}",
        )


# ── Exam Schedule ─────────────────────────────────────────────────────────── #

@router.get("/exams", response_model=list[ExamScheduleOut])
async def get_exam_schedule(
    current_user: CurrentUser,
    db: DB,
    department_id: uuid.UUID | None = None,
    semester: int | None = None,
) -> list[ExamScheduleOut]:
    query = select(ExamSchedule)
    dept_id = department_id or current_user.department_id
    if dept_id:
        query = query.where(ExamSchedule.department_id == dept_id)
    if semester:
        query = query.where(ExamSchedule.semester == semester)
    query = query.order_by(ExamSchedule.exam_date, ExamSchedule.start_time)
    result = await db.execute(query)
    return [ExamScheduleOut.model_validate(e) for e in result.scalars().all()]


@router.post("/exams", response_model=ExamScheduleOut, status_code=status.HTTP_201_CREATED)
async def create_exam(
    body: ExamScheduleCreate,
    _admin: AcademicWrite,
    db: DB,
) -> ExamScheduleOut:
    exam = ExamSchedule(**body.model_dump())
    db.add(exam)
    await db.commit()
    await db.refresh(exam)
    return ExamScheduleOut.model_validate(exam)


# ── Holidays ──────────────────────────────────────────────────────────────── #

@router.get("/holidays", response_model=list[HolidayOut])
async def get_holidays(_user: CurrentUser, db: DB) -> list[HolidayOut]:
    result = await db.execute(select(Holiday).order_by(Holiday.holiday_date))
    return [HolidayOut.model_validate(h) for h in result.scalars().all()]


@router.post("/holidays", response_model=HolidayOut, status_code=status.HTTP_201_CREATED)
async def create_holiday(
    body: HolidayCreate,
    _admin: AcademicWrite,
    db: DB,
) -> HolidayOut:
    holiday = Holiday(**body.model_dump())
    db.add(holiday)
    await db.commit()
    await db.refresh(holiday)
    return HolidayOut.model_validate(holiday)
