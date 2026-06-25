"""
AI/LLM API wrapper (OpenAI-compatible) for structured document extraction.
Sends document text to an LLM and enforces structured JSON output.
"""
import asyncio
import json
from typing import Optional
import httpx
from src.config import LLM_API_KEY, LLM_MODEL, LLM_BASE_URL


class LLMError(Exception):
    """Base exception for LLM API errors."""
    pass


class LLMClient:
    """Async client for an OpenAI-compatible LLM with structured output support."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or LLM_API_KEY
        self.model = model or LLM_MODEL
        self.base_url = base_url or LLM_BASE_URL

        if not self.api_key:
            raise LLMError(
                "LLM_API_KEY is not set. "
                "Set it in the Actor's environment variables (or your local .env)."
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
        max_tokens: int = 8000,
    ) -> dict:
        """
        Send document text to the LLM and get structured JSON output.

        Args:
            text: The extracted document text (max ~50K chars).
            system_prompt: Specialized instruction for the extraction task.
            output_schema: JSON schema for the expected output structure.
            temperature: LLM temperature (low = more deterministic).
            max_tokens: Maximum tokens in the response.

        Returns:
            Structured data as a Python dict matching output_schema.

        Raises:
            LLMError: On API errors, parsing failures, or timeouts.
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

        # Retry on transient errors (timeouts, rate limits, 5xx) with backoff.
        max_attempts = 3
        last_error: Optional[Exception] = None
        response = None
        for attempt in range(max_attempts):
            try:
                response = await self.client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                )
                response.raise_for_status()
                break
            except httpx.TimeoutException as e:
                last_error = LLMError("LLM API request timed out (max 60s)")
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                # Retry only on rate limit / server errors; fail fast on 4xx.
                if status == 429 or status >= 500:
                    last_error = LLMError(
                        f"LLM API error {status}: {self._parse_error_response(e.response)}"
                    )
                else:
                    raise LLMError(
                        f"LLM API error {status}: {self._parse_error_response(e.response)}"
                    )
            except Exception as e:
                last_error = LLMError(f"LLM API request failed: {str(e)}")

            # Backoff before the next attempt (0.5s, 1s) — not after the last one.
            if attempt < max_attempts - 1:
                await asyncio.sleep(0.5 * (attempt + 1))

        if response is None:
            raise last_error or LLMError("LLM API request failed after retries")

        try:
            result = response.json()
        except Exception as e:
            raise LLMError(f"Failed to parse LLM response JSON: {str(e)}")

        # Check for API-level errors
        if "error" in result:
            raise LLMError(f"LLM API error: {result['error']}")

        # Extract JSON from response content (response_format: json_object)
        try:
            choice = result["choices"][0]
            content = choice.get("message", {}).get("content", "")

            if not content:
                raise LLMError("Empty response from the LLM")

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

            raise LLMError(f"Could not parse JSON from response: {content[:200]}")

        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise LLMError(f"Failed to parse LLM structured output: {str(e)}")

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
