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
        result = parse_time("14:0")
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
            
            with patch("app.services.ocr._call_groq_api", new_callable=AsyncMock) as mock_call:
                mock_call.return_value = {
                    "success": True,
                    "extracted_text": "Sample timetable",
                    "entries": [{"day_of_week": "Monday", "start_time": "09:00", "end_time": "10:00", "subject": "Math", "room": "A101", "faculty_name": "Dr. Smith"}],
                    "errors": []
                }
                
                result = await parse_timetable_image(b"fake_image_data")
                
                assert result["success"] is True
                assert result["extracted_text"] == "Sample timetable"
                assert len(result["entries"]) == 1
                assert result["entries"][0]["subject"] == "Math"
                assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_successful_ocr_with_markdown_json(self):
        """Test successful OCR extraction with markdown-wrapped JSON response."""
        with patch("app.services.ocr.settings") as mock_settings:
            mock_settings.GROQ_API_KEY = "test_key"
            
            with patch("app.services.ocr._call_groq_api", new_callable=AsyncMock) as mock_call:
                mock_call.return_value = {
                    "success": True,
                    "extracted_text": "Sample timetable",
                    "entries": [{"day_of_week": "Tuesday", "start_time": "10:00", "end_time": "11:00", "subject": "Science", "room": "B202", "faculty_name": "Prof. Johnson"}],
                    "errors": []
                }
                
                result = await parse_timetable_image(b"fake_image_data")
                
                assert result["success"] is True
                assert result["extracted_text"] == "Sample timetable"
                assert len(result["entries"]) == 1
                assert result["entries"][0]["subject"] == "Science"
                assert result["errors"] == []

    @pytest.mark.asyncio
    async def test_empty_extracted_text_handled(self):
        """Test that empty extracted_text is handled correctly."""
        with patch("app.services.ocr.settings") as mock_settings:
            mock_settings.GROQ_API_KEY = "test_key"
            
            with patch("app.services.ocr._call_groq_api", new_callable=AsyncMock) as mock_call:
                mock_call.return_value = {
                    "success": True,
                    "extracted_text": "",
                    "entries": [],
                    "errors": []
                }
                
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
            
            with patch("app.services.ocr._call_groq_api", new_callable=AsyncMock) as mock_call:
                mock_call.side_effect = TimeoutError("Request timed out")
                
                with patch("app.services.ocr.logger") as mock_logger:
                    import asyncio
                    with patch.object(asyncio, "sleep", new_callable=AsyncMock) as mock_sleep:
                        result = await parse_timetable_image(b"fake_image_data")
                        
                        assert result["success"] is False
                        assert result["extracted_text"] == ""
                        assert result["entries"] == []
                        assert "timeout" in result["errors"][0].lower()
                        assert "3 attempts" in result["errors"][0]
                        # Verify retry logic was called (2 retries)
                        assert mock_sleep.call_count == 2
                        # Verify exponential backoff: 2^0=1s, 2^1=2s
                        mock_sleep.assert_any_call(1)
                        mock_sleep.assert_any_call(2)

    @pytest.mark.asyncio
    async def test_general_exception_handling(self):
        """Test that general exceptions are properly handled and logged."""
        with patch("app.services.ocr.settings") as mock_settings:
            mock_settings.GROQ_API_KEY = "test_key"
            
            with patch("app.services.ocr._call_groq_api", new_callable=AsyncMock) as mock_call:
                mock_call.side_effect = Exception("API error occurred")
                
                with patch("app.services.ocr.logger") as mock_logger:
                    import asyncio
                    with patch.object(asyncio, "sleep", new_callable=AsyncMock) as mock_sleep:
                        result = await parse_timetable_image(b"fake_image_data")
                        
                        assert result["success"] is False
                        assert result["extracted_text"] == ""
                        assert result["entries"] == []
                        assert "OCR parsing failed" in result["errors"][0]
                        assert "3 attempts" in result["errors"][0]
                        # Verify retry logic was called (2 retries)
                        assert mock_sleep.call_count == 2
                        # Verify exponential backoff: 2^0=1s, 2^1=2s
                        mock_sleep.assert_any_call(1)
                        mock_sleep.assert_any_call(2)

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
            
            # Need to import httpx inside the test since it's imported inside _call_groq_api
            import httpx
            with patch.object(httpx, "AsyncClient") as mock_client:
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

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_initial_failure(self):
        """Test that retry logic succeeds after initial failure."""
        with patch("app.services.ocr.settings") as mock_settings:
            mock_settings.GROQ_API_KEY = "test_key"
            
            with patch("app.services.ocr._call_groq_api", new_callable=AsyncMock) as mock_call:
                # First call fails, second call succeeds
                mock_call.side_effect = [
                    Exception("First attempt failed"),
                    {
                        "success": True,
                        "extracted_text": "Retry success",
                        "entries": [],
                        "errors": []
                    }
                ]
                
                import asyncio
                with patch.object(asyncio, "sleep", new_callable=AsyncMock) as mock_sleep:
                    result = await parse_timetable_image(b"fake_image_data")
                    
                    assert result["success"] is True
                    assert result["extracted_text"] == "Retry success"
                    assert result["errors"] == []
                    # Verify one retry happened with 1 second backoff
                    assert mock_sleep.call_count == 1
                    mock_sleep.assert_called_with(1)

    @pytest.mark.asyncio
    async def test_optimized_prompt_includes_edge_cases(self):
        """Test that the optimized prompt includes edge case handling instructions."""
        mock_response_data = {
            "choices": [{
                "message": {
                    "content": '{"extracted_text": "test", "entries": []}'
                }
            }]
        }
        
        with patch("app.services.ocr.settings") as mock_settings:
            mock_settings.GROQ_API_KEY = "test_key"
            
            import httpx
            with patch.object(httpx, "AsyncClient") as mock_client:
                mock_response = MagicMock()
                mock_response.json.return_value = mock_response_data
                mock_response.raise_for_status = MagicMock()
                
                mock_post = AsyncMock(return_value=mock_response)
                mock_client.return_value.__aenter__.return_value.post = mock_post
                
                await parse_timetable_image(b"fake_image_data")
                
                # Verify the prompt includes edge case handling
                call_args = mock_post.call_args
                payload = call_args[1]["json"]
                prompt = payload["messages"][0]["content"][1]["text"]
                
                # Check for edge case instructions
                assert "merged cells" in prompt.lower()
                assert "rotated text" in prompt.lower()
                assert "handwritten" in prompt.lower()
                
                # Check for examples
                assert "Example 1" in prompt
                assert "Example 2" in prompt
                assert "Example 3" in prompt
                
                # Check for explicit JSON structure
                assert "REQUIRED JSON STRUCTURE" in prompt
                assert "extracted_text" in prompt
                assert "day_of_week" in prompt

    @pytest.mark.asyncio
    async def test_temperature_lowered_for_deterministic_parsing(self):
        """Test that temperature is lowered to 0.3 for more deterministic results."""
        mock_response_data = {
            "choices": [{
                "message": {
                    "content": '{"extracted_text": "test", "entries": []}'
                }
            }]
        }
        
        with patch("app.services.ocr.settings") as mock_settings:
            mock_settings.GROQ_API_KEY = "test_key"
            
            import httpx
            with patch.object(httpx, "AsyncClient") as mock_client:
                mock_response = MagicMock()
                mock_response.json.return_value = mock_response_data
                mock_response.raise_for_status = MagicMock()
                
                mock_post = AsyncMock(return_value=mock_response)
                mock_client.return_value.__aenter__.return_value.post = mock_post
                
                await parse_timetable_image(b"fake_image_data")
                
                # Verify temperature is 0.3
                call_args = mock_post.call_args
                payload = call_args[1]["json"]
                assert payload["temperature"] == 0.3
