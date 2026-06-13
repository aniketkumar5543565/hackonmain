"""Unit tests for academic router - timetable confirm endpoint."""
import uuid
import pytest
from datetime import datetime, time
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.routers.academic import confirm_timetable
from app.models.academic import Timetable
from app.schemas.campus import TimetableConfirmRequest, TimetableUploadResponse


class TestConfirmTimetable:
    """Test confirm_timetable endpoint."""

    @pytest.fixture
    def mock_admin(self):
        """Create a mock admin user with department."""
        admin = MagicMock()
        admin.department_id = uuid.uuid4()
        admin.role = "ACADEMIC_ADMIN"
        return admin

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        db = AsyncMock(spec=AsyncSession)
        db.begin_nested = AsyncMock()
        db.begin_nested.return_value.__aenter__ = AsyncMock()
        db.begin_nested.return_value.__aexit__ = AsyncMock()
        db.execute = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.rollback = AsyncMock()
        return db

    @pytest.fixture
    def valid_entries(self):
        """Create valid timetable entries."""
        return [
            {
                "day_of_week": "Monday",
                "start_time": "09:00",
                "end_time": "10:30",
                "subject": "Data Structures",
                "room": "A101",
                "faculty_name": "Dr. Smith",
                "semester": 1,
            },
            {
                "day_of_week": "Tuesday",
                "start_time": "11:00",
                "end_time": "12:30",
                "subject": "Web Development",
                "room": "B202",
                "faculty_name": "Prof. Johnson",
                "semester": 1,
            },
        ]

    @pytest.mark.asyncio
    async def test_confirm_without_department_id_raises_error(self, mock_db):
        """Test that confirming without department_id raises 400 error."""
        admin = MagicMock()
        admin.department_id = None  # No department assigned
        
        body = TimetableConfirmRequest(entries=[{"day_of_week": "Monday", "start_time": "09:00", "end_time": "10:00", "subject": "Test"}])
        
        with pytest.raises(HTTPException) as exc_info:
            await confirm_timetable(body, admin, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "assigned to a department" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_confirm_with_empty_entries_raises_error(self, mock_admin, mock_db):
        """Test that confirming with empty entries raises 400 error."""
        body = TimetableConfirmRequest(entries=[])
        
        with pytest.raises(HTTPException) as exc_info:
            await confirm_timetable(body, mock_admin, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "At least one timetable entry is required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_confirm_successful_atomic_replacement(self, mock_admin, mock_db, valid_entries):
        """Test successful atomic replacement of timetable entries."""
        body = TimetableConfirmRequest(entries=valid_entries)
        
        # Mock the database operations
        created_entries = []
        def mock_add(entry):
            # Simulate database ID assignment
            entry.id = len(created_entries) + 1
            entry.created_at = datetime.now()
            created_entries.append(entry)
        
        mock_db.add.side_effect = mock_add
        
        result = await confirm_timetable(body, mock_admin, mock_db)
        
        # Verify transaction was started
        mock_db.begin_nested.assert_called_once()
        
        # Verify timeout was set
        assert mock_db.execute.call_count >= 1
        first_call_args = mock_db.execute.call_args_list[0][0][0]
        assert "statement_timeout" in first_call_args.lower()
        assert "60s" in first_call_args
        
        # Verify DELETE was executed
        delete_call_found = False
        for call in mock_db.execute.call_args_list:
            arg = str(call[0][0])
            if "delete" in arg.lower():
                delete_call_found = True
                break
        assert delete_call_found, "DELETE statement should be executed"
        
        # Verify entries were added
        assert mock_db.add.call_count == len(valid_entries)
        
        # Verify flush and commit were called
        mock_db.flush.assert_called_once()
        mock_db.commit.assert_called_once()
        
        # Verify response
        assert isinstance(result, TimetableUploadResponse)
        assert result.success is True
        assert result.entries_created == len(valid_entries)
        assert len(result.entries) == len(valid_entries)
        assert "Successfully saved" in result.message

    @pytest.mark.asyncio
    async def test_confirm_skips_invalid_time_order(self, mock_admin, mock_db):
        """Test that entries with invalid time order (start >= end) are skipped."""
        invalid_entries = [
            {
                "day_of_week": "Monday",
                "start_time": "10:30",
                "end_time": "09:00",  # Invalid: end before start
                "subject": "Invalid Entry",
                "semester": 1,
            },
            {
                "day_of_week": "Tuesday",
                "start_time": "09:00",
                "end_time": "10:30",  # Valid entry
                "subject": "Valid Entry",
                "semester": 1,
            },
        ]
        
        body = TimetableConfirmRequest(entries=invalid_entries)
        
        created_entries = []
        def mock_add(entry):
            entry.id = len(created_entries) + 1
            entry.created_at = datetime.now()
            created_entries.append(entry)
        
        mock_db.add.side_effect = mock_add
        
        result = await confirm_timetable(body, mock_admin, mock_db)
        
        # Only one valid entry should be added
        assert mock_db.add.call_count == 1
        assert result.entries_created == 1
        assert result.entries[0].subject == "Valid Entry"

    @pytest.mark.asyncio
    async def test_confirm_handles_database_error_with_rollback(self, mock_admin, mock_db, valid_entries):
        """Test that database errors trigger rollback."""
        body = TimetableConfirmRequest(entries=valid_entries)
        
        # Simulate database error during commit
        mock_db.commit.side_effect = Exception("Database connection lost")
        
        with pytest.raises(HTTPException) as exc_info:
            await confirm_timetable(body, mock_admin, mock_db)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Database transaction failed" in exc_info.value.detail
        assert "No changes were saved" in exc_info.value.detail
        
        # Verify rollback was called
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_confirm_parses_time_strings_correctly(self, mock_admin, mock_db):
        """Test that time strings are correctly parsed to time objects."""
        entries = [
            {
                "day_of_week": "Wednesday",
                "start_time": "14:45",
                "end_time": "16:15",
                "subject": "Advanced Programming",
                "semester": 2,
            }
        ]
        
        body = TimetableConfirmRequest(entries=entries)
        
        added_entry = None
        def mock_add(entry):
            nonlocal added_entry
            added_entry = entry
            entry.id = 1
            entry.created_at = datetime.now()
        
        mock_db.add.side_effect = mock_add
        
        await confirm_timetable(body, mock_admin, mock_db)
        
        # Verify the added entry has correct time objects
        assert added_entry is not None
        assert added_entry.start_time == time(14, 45)
        assert added_entry.end_time == time(16, 15)

    @pytest.mark.asyncio
    async def test_confirm_assigns_department_id_to_entries(self, mock_admin, mock_db, valid_entries):
        """Test that all entries are assigned the admin's department_id."""
        body = TimetableConfirmRequest(entries=valid_entries)
        
        added_entries = []
        def mock_add(entry):
            entry.id = len(added_entries) + 1
            entry.created_at = datetime.now()
            added_entries.append(entry)
        
        mock_db.add.side_effect = mock_add
        
        await confirm_timetable(body, mock_admin, mock_db)
        
        # Verify all entries have the admin's department_id
        for entry in added_entries:
            assert entry.department_id == mock_admin.department_id

    @pytest.mark.asyncio
    async def test_confirm_uses_default_semester_when_not_provided(self, mock_admin, mock_db):
        """Test that semester defaults to 1 when not provided."""
        entries = [
            {
                "day_of_week": "Friday",
                "start_time": "10:00",
                "end_time": "11:30",
                "subject": "Database Systems",
                # semester not provided
            }
        ]
        
        body = TimetableConfirmRequest(entries=entries)
        
        added_entry = None
        def mock_add(entry):
            nonlocal added_entry
            added_entry = entry
            entry.id = 1
            entry.created_at = datetime.now()
        
        mock_db.add.side_effect = mock_add
        
        await confirm_timetable(body, mock_admin, mock_db)
        
        # Verify default semester is 1
        assert added_entry.semester == 1

    @pytest.mark.asyncio
    async def test_confirm_preserves_optional_fields(self, mock_admin, mock_db):
        """Test that optional fields (room, faculty_name) are preserved."""
        entries = [
            {
                "day_of_week": "Thursday",
                "start_time": "13:00",
                "end_time": "14:30",
                "subject": "Software Engineering",
                "room": "Lab-305",
                "faculty_name": "Dr. Kumar",
                "semester": 3,
            }
        ]
        
        body = TimetableConfirmRequest(entries=entries)
        
        added_entry = None
        def mock_add(entry):
            nonlocal added_entry
            added_entry = entry
            entry.id = 1
            entry.created_at = datetime.now()
        
        mock_db.add.side_effect = mock_add
        
        await confirm_timetable(body, mock_admin, mock_db)
        
        # Verify optional fields are preserved
        assert added_entry.room == "Lab-305"
        assert added_entry.faculty_name == "Dr. Kumar"

    @pytest.mark.asyncio
    async def test_confirm_handles_missing_optional_fields(self, mock_admin, mock_db):
        """Test that missing optional fields are handled gracefully."""
        entries = [
            {
                "day_of_week": "Monday",
                "start_time": "08:00",
                "end_time": "09:30",
                "subject": "Mathematics",
                "semester": 1,
                # room and faculty_name not provided
            }
        ]
        
        body = TimetableConfirmRequest(entries=entries)
        
        added_entry = None
        def mock_add(entry):
            nonlocal added_entry
            added_entry = entry
            entry.id = 1
            entry.created_at = datetime.now()
        
        mock_db.add.side_effect = mock_add
        
        await confirm_timetable(body, mock_admin, mock_db)
        
        # Verify optional fields are None
        assert added_entry.room is None
        assert added_entry.faculty_name is None
