"""
AI Model Abstraction Layer for Lyrics Translation
Supports: OpenAI, DeepSeek, Gemini
"""

import json
import os
from typing import List, Optional
from abc import ABC, abstractmethod


class TranslationModel(ABC):
    """Base class for translation models"""
    
    @abstractmethod
    async def translate(self, lyrics: List[str], artist: str, title: str) -> List[str]:
        """Translate lyrics using the model"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the model is available (API key exists)"""
        pass


class OpenAIModel(TranslationModel):
    """OpenAI GPT models"""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model_name = model_name
        self.client = None
        
        try:
            from openai import AsyncOpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.client = AsyncOpenAI(api_key=api_key)
        except ImportError:
            pass
    
    def is_available(self) -> bool:
        return self.client is not None
    
    async def translate(self, lyrics: List[str], artist: str, title: str) -> List[str]:
        if not self.client:
            return lyrics
        
        system_prompt = self._get_system_prompt()
        user_content = {
            "context": f"Artist: {artist}, Title: {title}",
            "lyrics": lyrics
        }
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_content, ensure_ascii=False)}
                ],
                temperature=0.3,
            )
            
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.strip("`")
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            try:
                translated_list = json.loads(content)
            except json.JSONDecodeError:
                translated_list = [line.strip() for line in content.splitlines() if line.strip()]
            
            return translated_list
            
        except Exception as e:
            print(f"[ERROR] OpenAI translation failed: {e}")
            return lyrics
    
    def _get_system_prompt(self) -> str:
        return (
            "You are a professional Korean rap/hip-hop lyric translator. "
            "Translate the following Korean song lyrics into natural, fluent English. "
            "IMPORTANT RULES:\n"
            "1. Return a JSON array of strings with EXACTLY the same number of lines as input.\n"
            "2. For lines with mixed Korean-English: PRESERVE all existing English words/phrases exactly as they are, only translate Korean parts.\n"
            "3. For 100% English lines: keep them unchanged.\n"
            "4. For rap lyrics with wordplay/slang: maintain the vibe and flow, use natural English equivalents.\n"
            "5. When sentences span multiple lines: ensure translation flows naturally across lines.\n"
            "6. Do NOT include original Korean text in output. Output English ONLY.\n"
            "7. Maintain rhythm, emotion, and cultural context.\n"
            "Examples:\n"
            "- 'I'm on the 탑' → 'I'm on the top'\n"
            "- '나는 rapper야' → 'I'm a rapper'\n"
            "- 'Yeah yeah 시작해볼까' → 'Yeah yeah let's get started'"
        )


class DeepSeekModel(TranslationModel):
    """DeepSeek AI models"""
    
    def __init__(self, model_name: str = "deepseek-chat"):
        self.model_name = model_name
        self.client = None
        
        try:
            from openai import AsyncOpenAI  # DeepSeek uses OpenAI-compatible API
            api_key = os.getenv("DEEPSEEK_API_KEY")
            if api_key:
                self.client = AsyncOpenAI(
                    api_key=api_key,
                    base_url="https://api.deepseek.com"
                )
        except ImportError:
            pass
    
    def is_available(self) -> bool:
        return self.client is not None
    
    async def translate(self, lyrics: List[str], artist: str, title: str) -> List[str]:
        if not self.client:
            return lyrics
        
        system_prompt = self._get_system_prompt()
        user_content = {
            "context": f"Artist: {artist}, Title: {title}",
            "lyrics": lyrics
        }
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_content, ensure_ascii=False)}
                ],
                temperature=0.3,
            )
            
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.strip("`")
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            try:
                translated_list = json.loads(content)
            except json.JSONDecodeError:
                translated_list = [line.strip() for line in content.splitlines() if line.strip()]
            
            return translated_list
            
        except Exception as e:
            print(f"[ERROR] DeepSeek translation failed: {e}")
            return lyrics
    
    def _get_system_prompt(self) -> str:
        return (
            "You are a professional Korean rap/hip-hop lyric translator. "
            "Translate the following Korean song lyrics into natural, fluent English. "
            "IMPORTANT RULES:\n"
            "1. Return a JSON array of strings with EXACTLY the same number of lines as input.\n"
            "2. For lines with mixed Korean-English: PRESERVE all existing English words/phrases exactly as they are, only translate Korean parts.\n"
            "3. For 100% English lines: keep them unchanged.\n"
            "4. For rap lyrics with wordplay/slang: maintain the vibe and flow, use natural English equivalents.\n"
            "5. When sentences span multiple lines: ensure translation flows naturally across lines.\n"
            "6. Do NOT include original Korean text in output. Output English ONLY.\n"
            "7. Maintain rhythm, emotion, and cultural context.\n"
            "Examples:\n"
            "- 'I'm on the 탑' → 'I'm on the top'\n"
            "- '나는 rapper야' → 'I'm a rapper'\n"
            "- 'Yeah yeah 시작해볼까' → 'Yeah yeah let's get started'"
        )


class GeminiModel(TranslationModel):
    """Google Gemini models"""
    
    def __init__(self, model_name: str = "gemini-pro"):
        self.model_name = model_name
        self.client = None
        
        try:
            import google.generativeai as genai
            api_key = os.getenv("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                self.client = genai.GenerativeModel(model_name)
        except ImportError:
            pass
    
    def is_available(self) -> bool:
        return self.client is not None
    
    async def translate(self, lyrics: List[str], artist: str, title: str) -> List[str]:
        if not self.client:
            return lyrics
        
        system_prompt = self._get_system_prompt()
        user_content = {
            "context": f"Artist: {artist}, Title: {title}",
            "lyrics": lyrics
        }
        
        prompt = f"{system_prompt}\n\n{json.dumps(user_content, ensure_ascii=False)}"
        
        try:
            response = await self.client.generate_content_async(prompt)
            content = response.text.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.strip("`")
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            try:
                translated_list = json.loads(content)
            except json.JSONDecodeError:
                translated_list = [line.strip() for line in content.splitlines() if line.strip()]
            
            return translated_list
            
        except Exception as e:
            print(f"[ERROR] Gemini translation failed: {e}")
            return lyrics
    
    def _get_system_prompt(self) -> str:
        return (
            "You are a professional Korean rap/hip-hop lyric translator. "
            "Translate the following Korean song lyrics into natural, fluent English. "
            "IMPORTANT RULES:\n"
            "1. Return a JSON array of strings with EXACTLY the same number of lines as input.\n"
            "2. For lines with mixed Korean-English: PRESERVE all existing English words/phrases exactly as they are, only translate Korean parts.\n"
            "3. For 100% English lines: keep them unchanged.\n"
            "4. For rap lyrics with wordplay/slang: maintain the vibe and flow, use natural English equivalents.\n"
            "5. When sentences span multiple lines: ensure translation flows naturally across lines.\n"
            "6. Do NOT include original Korean text in output. Output English ONLY.\n"
            "7. Maintain rhythm, emotion, and cultural context.\n"
            "8. Ensure strict 1:1 mapping between input and output lines.\n"
            "Examples:\n"
            "- 'I'm on the 탑' → 'I'm on the top'\n"
            "- '나는 rapper야' → 'I'm a rapper'\n"
            "- 'Yeah yeah 시작해볼까' → 'Yeah yeah let's get started'"
        )


# Model registry
AVAILABLE_MODELS = {
    "gpt-4o-mini": ("OpenAI GPT-4o Mini", lambda: OpenAIModel("gpt-4o-mini")),
    "gpt-4o": ("OpenAI GPT-4o", lambda: OpenAIModel("gpt-4o")),
    "gpt-4-turbo": ("OpenAI GPT-4 Turbo", lambda: OpenAIModel("gpt-4-turbo")),
    "deepseek-chat": ("DeepSeek Chat", lambda: DeepSeekModel("deepseek-chat")),
    "gemini-pro": ("Google Gemini Pro", lambda: GeminiModel("gemini-pro")),
    "gemini-1.5-pro": ("Google Gemini 1.5 Pro", lambda: GeminiModel("gemini-1.5-pro")),
}


def get_available_models() -> dict:
    """Get list of available models (with API keys configured)"""
    available = {}
    for model_id, (name, factory) in AVAILABLE_MODELS.items():
        model = factory()
        if model.is_available():
            available[model_id] = name
    return available


def create_model(model_id: str) -> Optional[TranslationModel]:
    """Create a translation model instance"""
    if model_id in AVAILABLE_MODELS:
        _, factory = AVAILABLE_MODELS[model_id]
        return factory()
    return None
