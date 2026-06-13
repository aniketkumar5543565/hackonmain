"""OCR and timetable parsing service using Groq API.
Falls back to mock parsing if API key is not configured.
"""
import base64
import json
import logging
import re
import traceback
from datetime import time

from app.config import settings

logger = logging.getLogger(__name__)


async def parse_timetable_image(file_content: bytes) -> dict:
    """
    Parse a timetable image using Groq API with vision capability.
    Returns extracted text and parsed entries.
    """
    # Encode image to base64
    image_base64 = base64.standard_b64encode(file_content).decode("utf-8")

    if not settings.GROQ_API_KEY:
        # Fallback: Return mock parsed data for demo
        return _mock_parse_response(image_base64)

    try:
        import httpx

        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": "llama-3.2-90b-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}",
                            },
                        },
                        {
                            "type": "text",
                            "text": """Extract the timetable information from this image. Return a JSON response with this structure:
{
    "extracted_text": "the raw text extracted from the image",
    "entries": [
        {
            "day_of_week": "Monday",
            "start_time": "09:00",
            "end_time": "10:30",
            "subject": "Data Structures",
            "room": "A101",
            "faculty_name": "Dr. Smith"
        }
    ]
}

If you can't extract the data, still return valid JSON with extracted_text and empty entries array.
Make sure all times are in HH:MM format (24-hour).
Days should be full day names (Monday, Tuesday, etc.).
Return ONLY the JSON, no markdown or extra text.""",
                        },
                    ],
                }
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            result = response.json()

            # Extract the text response
            text_content = result["choices"][0]["message"]["content"]

            # Try to parse JSON from response (handle markdown code blocks)
            try:
                # First try to extract JSON from markdown code blocks
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text_content, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(1))
                else:
                    # Fallback to finding JSON object directly
                    json_match = re.search(r'\{.*\}', text_content, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group())
                    else:
                        parsed = None
                
                if parsed:
                    extracted_text = parsed.get("extracted_text", "")
                    # Handle empty extracted text case - return empty string, not error
                    if not extracted_text:
                        extracted_text = ""
                    
                    return {
                        "success": True,
                        "extracted_text": extracted_text,
                        "entries": parsed.get("entries", []),
                        "errors": [],
                    }
            except (json.JSONDecodeError, AttributeError) as e:
                logger.error(
                    f"JSON parsing failed: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
                )
                pass

            # Fallback: return raw text
            return {
                "success": True,
                "extracted_text": text_content,
                "entries": [],
                "errors": ["Could not parse structured data from response"],
            }

    except TimeoutError as e:
        logger.error(
            f"OCR timeout error: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        )
        return {
            "success": False,
            "extracted_text": "",
            "entries": [],
            "errors": ["OCR extraction timeout: The request exceeded 30 seconds"],
        }
    except Exception as e:
        logger.error(
            f"OCR parsing failed: {type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
        )
        return {
            "success": False,
            "extracted_text": "",
            "entries": [],
            "errors": [f"OCR parsing failed: {str(e)}"],
        }


def _mock_parse_response(image_b64: str) -> dict:
    """Mock response for demo without Claude API key."""
    return {
        "success": True,
        "extracted_text": "Mock timetable: Classes from Monday to Friday, 9am to 5pm",
        "entries": [
            {
                "day_of_week": "Monday",
                "start_time": "09:00",
                "end_time": "10:30",
                "subject": "Data Structures",
                "room": "A101",
                "faculty_name": "Dr. Smith",
            },
            {
                "day_of_week": "Monday",
                "start_time": "11:00",
                "end_time": "12:30",
                "subject": "Web Development",
                "room": "B202",
                "faculty_name": "Prof. Johnson",
            },
            {
                "day_of_week": "Tuesday",
                "start_time": "09:00",
                "end_time": "10:30",
                "subject": "Database Design",
                "room": "A101",
                "faculty_name": "Dr. Smith",
            },
            {
                "day_of_week": "Wednesday",
                "start_time": "14:00",
                "end_time": "15:30",
                "subject": "AI & Machine Learning",
                "room": "C303",
                "faculty_name": "Dr. Patel",
            },
            {
                "day_of_week": "Friday",
                "start_time": "10:00",
                "end_time": "11:30",
                "subject": "Software Engineering",
                "room": "D404",
                "faculty_name": "Prof. Chen",
            },
        ],
        "errors": [],
    }


def parse_time(time_str: str) -> time:
    """Parse time string to time object."""
    if isinstance(time_str, time):
        return time_str
    try:
        # Handle HH:MM format
        parts = time_str.strip().split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        return time(hour=hour, minute=minute)
    except (ValueError, IndexError):
        return time(9, 0)  # Default to 9 AM
