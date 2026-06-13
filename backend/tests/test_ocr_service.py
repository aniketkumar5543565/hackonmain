"""Unit tests for OCR service."""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.ocr import parse_timetable_image, parse_time
from datetime import time


class TestParseTime:
    """Test parse_time utility function."""

    def test_parse_valid_time(self):
        """Test parsing valid HH:MM format."""
        result = parse_time("09:30")
        assert result == time(9, 30)

    def test_parse_time_no_minutes(self):
        """Test parsing time with only hours."""
        result = parse_time("14:")
        assert result == time(14, 0)

    def test_parse_invalid_time_returns_default(self):
        """Test that invalid time returns default 9:00."""
        result = parse_time("invalid")
        assert result == time(9, 0)

    def test_parse_time_object_returns_same(self):
        """Test that passing a time object returns it unchanged."""
        t = time(10, 30)
        result = parse_time(t)
        assert result == t


class TestParseTimetableImage:
    """Test parse_timetable_image function."""

    @pytest.mark.asyncio
    async def test_mock_response_when_no_api_key(self):
        """Test that mock response is returned when API key is not set."""
        with patch("app.services.ocr.settings") as mock_settings:
            mock_settings.GROQ_API_KEY = None
            
            result = await parse_timetable_image(b"fake_image_data")
            
            assert result["success"] is True
            assert "Mock timetable" in result["extracted_text"]
            assert len(result["entries"]) > 0
            assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_successful_ocr_with_plain_json(self):
        """Test successful OCR extraction with plain JSON response."""
        mock_response_data = {
            "choices": [{
                "message": {
                    "content": '{"extracted_text": "Sample timetable", "entries": [{"day_of_week": "Monday", "start_time": "09:00", "end_time": "10:00", "subject": "Math", "room": "A101", "faculty_name": "Dr. Smith"}]}'
                }
            }]
        }
        
        with patch("app.services.ocr.settings") as mock_settings:
            mock_settings.GROQ_API_KEY = "test_key"
            
            with patch("app.services.ocr.httpx.AsyncClient") as mock_client:
                mock_response = MagicMock()
                mock_response.json.return_value = mock_response_data
                mock_response.raise_for_status = MagicMock()
                
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
                
                result = await parse_timetable_image(b"fake_image_data")
                
                assert result["success"] is True
                assert result["extracted_text"] == "Sample timetable"
                assert len(result["entries"]) == 1
                assert result["entries"][0]["subject"] == "Math"
                assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_successful_ocr_with_markdown_json(self):
        """Test successful OCR extraction with markdown-wrapped JSON response."""
        mock_response_data = {
            "choices": [{
                "message": {
                    "content": '```json\n{"extracted_text": "Sample timetable", "entries": [{"day_of_week": "Tuesday", "start_time": "10:00", "end_time": "11:00", "subject": "Science", "room": "B202", "faculty_name": "Prof. Johnson"}]}\n```'
                }
            }]
        }
        
        with patch("app.services.ocr.settings") as mock_settings:
            mock_settings.GROQ_API_KEY = "test_key"
            
            with patch("app.services.ocr.httpx.AsyncClient") as mock_client:
                mock_response = MagicMock()
                mock_response.json.return_value = mock_response_data
                mock_response.raise_for_status = MagicMock()
                
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
                
                result = await parse_timetable_image(b"fake_image_data")
                
                assert result["success"] is True
                assert result["extracted_text"] == "Sample timetable"
                assert len(result["entries"]) == 1
                assert result["entries"][0]["subject"] == "Science"
                assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_empty_extracted_text_handled(self):
        """Test that empty extracted_text is handled correctly."""
        mock_response_data = {
            "choices": [{
                "message": {
                    "content": '{"extracted_text": "", "entries": []}'
                }
            }]
        }
        
        with patch("app.services.ocr.settings") as mock_settings:
            mock_settings.GROQ_API_KEY = "test_key"
            
            with patch("app.services.ocr.httpx.AsyncClient") as mock_client:
                mock_response = MagicMock()
                mock_response.json.return_value = mock_response_data
                mock_response.raise_for_status = MagicMock()
                
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
                
                result = await parse_timetable_image(b"fake_image_data")
                
                assert result["success"] is True
                assert result["extracted_text"] == ""
                assert result["entries"] == []
                assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self):
        """Test that timeout errors are properly handled and logged."""
        with patch("app.services.ocr.settings") as mock_settings:
            mock_settings.GROQ_API_KEY = "test_key"
            
            with patch("app.services.ocr.httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    side_effect=TimeoutError("Request timed out")
                )
                
                with patch("app.services.ocr.logger") as mock_logger:
                    result = await parse_timetable_image(b"fake_image_data")
                    
                    assert result["success"] is False
                    assert result["extracted_text"] == ""
                    assert result["entries"] == []
                    assert "timeout" in result["errors"][0].lower()
                    assert "30 seconds" in result["errors"][0]
                    # Verify logging occurred with exception type and stack trace
                    mock_logger.error.assert_called_once()
                    error_msg = mock_logger.error.call_args[0][0]
                    assert "TimeoutError" in error_msg

    @pytest.mark.asyncio
    async def test_general_exception_handling(self):
        """Test that general exceptions are properly handled and logged."""
        with patch("app.services.ocr.settings") as mock_settings:
            mock_settings.GROQ_API_KEY = "test_key"
            
            with patch("app.services.ocr.httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                    side_effect=Exception("API error occurred")
                )
                
                with patch("app.services.ocr.logger") as mock_logger:
                    result = await parse_timetable_image(b"fake_image_data")
                    
                    assert result["success"] is False
                    assert result["extracted_text"] == ""
                    assert result["entries"] == []
                    assert "OCR parsing failed" in result["errors"][0]
                    # Verify logging occurred with exception type and stack trace
                    mock_logger.error.assert_called_once()
                    error_msg = mock_logger.error.call_args[0][0]
                    assert "Exception" in error_msg

    @pytest.mark.asyncio
    async def test_correct_model_name_used(self):
        """Test that the correct Groq model name is used in the API call."""
        mock_response_data = {
            "choices": [{
                "message": {
                    "content": '{"extracted_text": "test", "entries": []}'
                }
            }]
        }
        
        with patch("app.services.ocr.settings") as mock_settings:
            mock_settings.GROQ_API_KEY = "test_key"
            
            with patch("app.services.ocr.httpx.AsyncClient") as mock_client:
                mock_response = MagicMock()
                mock_response.json.return_value = mock_response_data
                mock_response.raise_for_status = MagicMock()
                
                mock_post = AsyncMock(return_value=mock_response)
                mock_client.return_value.__aenter__.return_value.post = mock_post
                
                await parse_timetable_image(b"fake_image_data")
                
                # Verify the correct model name was used
                call_args = mock_post.call_args
                payload = call_args[1]["json"]
                assert payload["model"] == "llama-3.2-90b-vision-preview"
