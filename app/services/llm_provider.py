"""LLM Provider abstraction layer"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import base64
import httpx
import json
import re
import asyncio
from app.core.config import settings


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def extract_document(
        self,
        file_data: bytes,
        mime_type: str,
        prompt: str
    ) -> Dict[str, Any]:
        """Extract structured data from a document"""
        pass
    
    @abstractmethod
    async def validate_documents(
        self,
        extractions: list,
        prompt: str
    ) -> Dict[str, Any]:
        """Validate multiple documents for compliance"""
        pass


class GeminiProvider(LLMProvider):
    """Google Gemini provider implementation"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.max_retries = 5
        self.base_delay = 5.0  # Base delay in seconds (increased from 2s)
    
    async def _make_request_with_retry(self, client, url, params, payload, operation_name="request"):
        """Make HTTP request with exponential backoff for rate limits"""
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                response = await client.post(url, params=params, json=payload)
                
                # Check for rate limit (429)
                if response.status_code == 429:
                    # Get Retry-After header or calculate backoff
                    retry_after_header = response.headers.get('Retry-After')
                    if retry_after_header:
                        wait_time = int(retry_after_header)
                    else:
                        # Exponential backoff: 5s, 10s, 20s, 40s, 80s (capped at 60s)
                        wait_time = min(int(self.base_delay * (2 ** attempt)), 60)
                    
                    print(f"⚠️  Rate limited for {operation_name}. Attempt {attempt + 1}/{self.max_retries}. Waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                
                # Raise for other errors
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                last_exception = e
                if e.response.status_code == 429 and attempt < self.max_retries - 1:
                    retry_after_header = e.response.headers.get('Retry-After')
                    if retry_after_header:
                        wait_time = int(retry_after_header)
                    else:
                        wait_time = min(int(self.base_delay * (2 ** attempt)), 60)
                    
                    print(f"⚠️  Rate limited for {operation_name}. Attempt {attempt + 1}/{self.max_retries}. Waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                raise
            except httpx.RequestError as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    wait_time = min(int(self.base_delay * (2 ** attempt)), 60)
                    print(f"Request failed for {operation_name}: {str(e)}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                raise
        
        # If we exhausted all retries, raise the last exception
        if last_exception:
            raise last_exception
        raise Exception(f"Failed to complete {operation_name} after {self.max_retries} attempts")
    
    async def extract_document(
        self,
        file_data: bytes,
        mime_type: str,
        prompt: str
    ) -> Dict[str, Any]:
        base64_data = base64.b64encode(file_data).decode('utf-8')
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64_data
                        }
                    }
                ]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 4096
            }
        }
        
        async with httpx.AsyncClient(timeout=settings.JOB_TIMEOUT) as client:
            result = await self._make_request_with_retry(
                client,
                f"{self.base_url}/models/{settings.LLM_MODEL}:generateContent",
                {"key": self.api_key},
                payload,
                "extract_document"
            )
            
            # Extract text from response
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            return self._parse_json_response(text)
    
    async def validate_documents(
        self,
        extractions: list,
        prompt: str
    ) -> Dict[str, Any]:
        payload = {
            "contents": [{
                "parts": [{"text": prompt + "\n\nExtractions:\n" + json.dumps(extractions, indent=2)}]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 4096
            }
        }
        
        async with httpx.AsyncClient(timeout=settings.JOB_TIMEOUT) as client:
            result = await self._make_request_with_retry(
                client,
                f"{self.base_url}/models/{settings.LLM_MODEL}:generateContent",
                {"key": self.api_key},
                payload,
                "validate_documents"
            )
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            return self._parse_json_response(text)
    
    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Extract JSON from LLM response, handling markdown code fences"""
        # Remove markdown code fences if present
        text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\s*```$', '', text, flags=re.MULTILINE)
        
        # Find JSON between braces
        start = text.find('{')
        end = text.rfind('}') + 1
        
        if start != -1 and end > start:
            json_str = text[start:end]
            return json.loads(json_str)
        
        raise ValueError("No valid JSON found in response")


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider implementation"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1"
    
    async def extract_document(
        self,
        file_data: bytes,
        mime_type: str,
        prompt: str
    ) -> Dict[str, Any]:
        base64_data = base64.b64encode(file_data).decode('utf-8')
        
        payload = {
            "model": settings.LLM_MODEL,
            "max_tokens": 4096,
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime_type,
                            "data": base64_data
                        }
                    },
                    {"type": "text", "text": prompt}
                ]
            }]
        }
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=settings.JOB_TIMEOUT) as client:
            response = await client.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            text = result["content"][0]["text"]
            return self._parse_json_response(text)
    
    async def validate_documents(
        self,
        extractions: list,
        prompt: str
    ) -> Dict[str, Any]:
        payload = {
            "model": settings.LLM_MODEL,
            "max_tokens": 4096,
            "messages": [{
                "role": "user",
                "content": [{"type": "text", "text": prompt + "\n\nExtractions:\n" + json.dumps(extractions, indent=2)}]
            }]
        }
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=settings.JOB_TIMEOUT) as client:
            response = await client.post(
                f"{self.base_url}/messages",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            text = result["content"][0]["text"]
            return self._parse_json_response(text)
    
    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\s*```$', '', text, flags=re.MULTILINE)
        
        start = text.find('{')
        end = text.rfind('}') + 1
        
        if start != -1 and end > start:
            json_str = text[start:end]
            return json.loads(json_str)
        
        raise ValueError("No valid JSON found in response")


# Provider factory
def get_llm_provider(provider_name: str | None = None, api_key: str | None = None) -> LLMProvider:
    """Factory function to get LLM provider instance"""
    provider_name = provider_name or settings.LLM_PROVIDER
    api_key = api_key or settings.LLM_API_KEY
    
    providers = {
        "gemini": GeminiProvider,
        "anthropic": AnthropicProvider,
    }
    
    provider_class = providers.get(provider_name.lower())
    if not provider_class:
        raise ValueError(f"Unsupported LLM provider: {provider_name}")
    
    return provider_class(api_key)
