"""
AI router — intelligent campus assistant.

Aggregates live data from all modules (academic, hostel, placement, clubs)
and calls Google Gemini API to generate a personalized daily summary.

Falls back to a structured mock response if GEMINI_API_KEY is not set,
so the demo works out of the box without needing a key.
"""
import os
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import CurrentUser
from app.models.content import Assignment, Event
from app.models.placement import PlacementDrive
from app.models.academic import ExamSchedule, Timetable
from app.models.hostel import MessMenu, MessNotice
from app.schemas.campus import AIQueryRequest, AIQueryResponse

router = APIRouter(prefix="/ai", tags=["ai"])
DB = Annotated[AsyncSession, Depends(get_db)]


async def _gather_context(current_user, db: AsyncSession) -> tuple[list[str], list[str]]:
    """Fetch upcoming data from all modules for the current user."""
    today = date.today()
    next_week = today + timedelta(days=7)
    context_lines: list[str] = []
    context_labels: list[str] = []

    # Assignments due soon
    if current_user.department_id:
        ass_result = await db.execute(
            select(Assignment)
            .where(
                Assignment.department_id == current_user.department_id,
                Assignment.due_date >= today,
                Assignment.due_date <= next_week,
            )
            .order_by(Assignment.due_date)
            .limit(5)
        )
        for a in ass_result.scalars().all():
            days = (a.due_date - today).days
            label = "today" if days == 0 else f"in {days} day(s)"
            context_lines.append(f"Assignment: {a.title} ({a.subject}) due {label}")
            context_labels.append("academic")

    # Upcoming exams
    if current_user.department_id:
        exam_result = await db.execute(
            select(ExamSchedule)
            .where(
                ExamSchedule.department_id == current_user.department_id,
                ExamSchedule.exam_date >= today,
                ExamSchedule.exam_date <= next_week,
            )
            .order_by(ExamSchedule.exam_date)
            .limit(5)
        )
        for e in exam_result.scalars().all():
            days = (e.exam_date - today).days
            label = "tomorrow" if days == 1 else (f"in {days} days" if days > 1 else "today")
            context_lines.append(f"Exam: {e.subject} — {label} at {e.start_time} in {e.room or 'TBD'}")
            context_labels.append("academic")

    # Placement drives with upcoming deadlines
    drive_result = await db.execute(
        select(PlacementDrive)
        .where(
            PlacementDrive.is_active == True,
            PlacementDrive.registration_deadline >= today,
            PlacementDrive.registration_deadline <= next_week,
        )
        .order_by(PlacementDrive.registration_deadline)
        .limit(5)
    )
    for d in drive_result.scalars().all():
        days = (d.registration_deadline - today).days
        label = "today" if days == 0 else f"in {days} day(s)"
        context_lines.append(
            f"Placement: {d.company_name} ({d.job_role}, {d.package_lpa} LPA) — registration closes {label}"
        )
        context_labels.append("placement")

    # Upcoming events
    event_result = await db.execute(
        select(Event)
        .where(Event.event_date >= today, Event.event_date <= next_week)
        .order_by(Event.event_date)
        .limit(5)
    )
    for e in event_result.scalars().all():
        days = (e.event_date - today).days
        label = "today" if days == 0 else f"in {days} day(s)"
        context_lines.append(f"Event: {e.title} ({e.domain}) — {label}")
        context_labels.append("events")

    # Today's mess (special dinners)
    mess_result = await db.execute(
        select(MessMenu)
        .where(MessMenu.is_special == True, MessMenu.week_start <= today)
        .order_by(MessMenu.week_start.desc())
        .limit(3)
    )
    for m in mess_result.scalars().all():
        context_lines.append(f"Special Mess: {m.meal_type} — {m.items}")
        context_labels.append("hostel")

    # Today's timetable
    day_name = today.strftime("%A")
    if current_user.department_id:
        tt_result = await db.execute(
            select(Timetable)
            .where(
                Timetable.department_id == current_user.department_id,
                Timetable.day_of_week == day_name,
            )
            .order_by(Timetable.start_time)
        )
        classes = tt_result.scalars().all()
        if classes:
            class_names = ", ".join(f"{c.subject} @ {c.start_time}" for c in classes)
            context_lines.append(f"Today's classes ({day_name}): {class_names}")
            context_labels.append("academic")

    return context_lines, context_labels


def _build_prompt(user_name: str, context_lines: list[str], user_message: str) -> str:
    context_text = "\n".join(f"- {line}" for line in context_lines) if context_lines else "- No upcoming items found."
    return f"""You are CampusOS AI, a helpful and friendly campus assistant for {user_name}.

Here is their current campus data:
{context_text}

The student asks: "{user_message}"

Based on the above data, give a concise, friendly, prioritized response. 
Format as a numbered priority list if showing multiple items. 
Be specific — mention actual subjects, companies, and deadlines.
Keep response under 200 words."""


async def _call_gemini(prompt: str) -> str:
    """Call Google Gemini API or fall back to structured mock."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return _mock_ai_response(prompt)

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception as exc:
        # Graceful fallback
        return _mock_ai_response(prompt)


def _mock_ai_response(prompt: str) -> str:
    """Intelligent mock that parses the context from the prompt."""
    lines = [line.strip("- ") for line in prompt.split("\n") if line.startswith("- ") and ":" in line]
    if not lines:
        return "📚 Looks like your schedule is clear! A great time to review past material or work on side projects."

    priorities = []
    for i, line in enumerate(lines[:5], 1):
        priorities.append(f"{i}. {line}")

    return "🎯 **Today's Priorities for you:**\n\n" + "\n".join(priorities) + "\n\nStay focused and make it count! 💪"


@router.post("/query", response_model=AIQueryResponse)
async def ai_query(
    body: AIQueryRequest,
    current_user: CurrentUser,
    db: DB,
) -> AIQueryResponse:
    context_lines, context_labels = await _gather_context(current_user, db)
    prompt = _build_prompt(current_user.full_name, context_lines, body.message)
    reply = await _call_gemini(prompt)
    unique_labels = list(dict.fromkeys(context_labels))  # preserve order, deduplicate
    return AIQueryResponse(reply=reply, context_used=unique_labels)
