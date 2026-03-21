from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import base64
import httpx
import json
import re
from config import LLM_API_KEY, JOB_TIMEOUT


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
        
        async with httpx.AsyncClient(timeout=JOB_TIMEOUT) as client:
            response = await client.post(
                f"{self.base_url}/models/{LLM_MODEL}:generateContent",
                params={"key": self.api_key},
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            
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
        
        async with httpx.AsyncClient(timeout=JOB_TIMEOUT) as client:
            response = await client.post(
                f"{self.base_url}/models/{LLM_MODEL}:generateContent",
                params={"key": self.api_key},
                json=payload
            )
            response.raise_for_status()
            result = response.json()
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
            "model": LLM_MODEL,
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
        
        async with httpx.AsyncClient(timeout=JOB_TIMEOUT) as client:
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
            "model": LLM_MODEL,
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
        
        async with httpx.AsyncClient(timeout=JOB_TIMEOUT) as client:
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


class GroqProvider(LLMProvider):
    """Groq provider (using Llama vision models)"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.groq.com/openai/v1"
    
    async def extract_document(
        self,
        file_data: bytes,
        mime_type: str,
        prompt: str
    ) -> Dict[str, Any]:
        # Groq doesn't support images directly in API yet
        # This is a placeholder - would need different approach
        raise NotImplementedError("Groq vision support not yet implemented")


# Provider factory
def get_provider(provider_name: str, api_key: str) -> LLMProvider:
    providers = {
        "gemini": GeminiProvider,
        "anthropic": AnthropicProvider,
        "groq": GroqProvider,
    }
    
    provider_class = providers.get(provider_name.lower())
    if not provider_class:
        raise ValueError(f"Unsupported LLM provider: {provider_name}")
    
    return provider_class(api_key)


# Global LLM model name
LLM_MODEL = ""  # Will be set from config
