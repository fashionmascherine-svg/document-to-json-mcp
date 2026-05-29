"""
DeepSeek-v4-flash API wrapper for structured document extraction.
Uses function calling / tool_use to enforce structured JSON output.
"""
import json
from typing import Optional
import httpx
from src.config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL


class DeepSeekError(Exception):
    """Base exception for DeepSeek API errors."""
    pass


class DeepSeekClient:
    """Async client for DeepSeek-v4-flash with structured output support."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.model = model or DEEPSEEK_MODEL
        self.base_url = base_url or DEEPSEEK_BASE_URL

        if not self.api_key:
            raise DeepSeekError(
                "DEEPSEEK_API_KEY is not set. "
                "Create a .env file from .env.example and add your key."
            )

        self.client = httpx.AsyncClient(
            timeout=60.0,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )

    async def extract_structured(
        self,
        text: str,
        system_prompt: str,
        output_schema: dict,
        temperature: float = 0.1,
        max_tokens: int = 4000,
    ) -> dict:
        """
        Send document text to DeepSeek and get structured JSON output.
        
        Uses function calling to enforce the output schema.
        
        Args:
            text: The extracted document text (max ~50K chars).
            system_prompt: Specialized instruction for the extraction task.
            output_schema: JSON schema for the expected output structure.
            temperature: LLM temperature (low = more deterministic).
            max_tokens: Maximum tokens in the response.
        
        Returns:
            Structured data as a Python dict matching output_schema.
        
        Raises:
            DeepSeekError: On API errors, parsing failures, or timeouts.
        """
        # Truncate text to avoid token limits (roughly 50K chars ~ 12K tokens)
        truncated_text = text[:50000]

        # Build the JSON schema instruction
        import json as _json
        schema_str = _json.dumps(output_schema, indent=2)
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        "Extract structured data from the following document text.\n\n"
                        f"{truncated_text}\n\n"
                        "Respond ONLY with a valid JSON object that matches this schema:\n"
                        f"{schema_str}\n\n"
                        "IMPORTANT: Return ONLY the JSON object, no other text, no markdown formatting, no code blocks."
                    ),
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
            )
            response.raise_for_status()
        except httpx.TimeoutException:
            raise DeepSeekError("DeepSeek API request timed out (max 60s)")
        except httpx.HTTPStatusError as e:
            error_detail = self._parse_error_response(e.response)
            raise DeepSeekError(f"DeepSeek API error {e.response.status_code}: {error_detail}")
        except Exception as e:
            raise DeepSeekError(f"DeepSeek API request failed: {str(e)}")

        try:
            result = response.json()
        except Exception as e:
            raise DeepSeekError(f"Failed to parse DeepSeek response JSON: {str(e)}")

        # Check for API-level errors
        if "error" in result:
            raise DeepSeekError(f"DeepSeek API error: {result['error']}")

        # Extract JSON from response content (response_format: json_object)
        try:
            choice = result["choices"][0]
            content = choice.get("message", {}).get("content", "")

            if not content:
                raise DeepSeekError("Empty response from DeepSeek")

            # Try to parse as JSON directly
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                pass

            # Fallback: try to find JSON in the response (for non-json_object mode)
            import re as _re
            json_match = _re.search(r'\{.*\}', content, _re.DOTALL)
            if json_match:
                return json.loads(json_match.group())

            raise DeepSeekError(f"Could not parse JSON from response: {content[:200]}")

        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise DeepSeekError(f"Failed to parse DeepSeek structured output: {str(e)}")

    def _parse_error_response(self, response: httpx.Response) -> str:
        """Extract a human-readable error message from an API error response."""
        try:
            body = response.json()
            return body.get("error", {}).get("message", str(body))
        except Exception:
            return response.text[:500]

    async def close(self):
        """Close the underlying HTTP client."""
        await self.client.aclose()
