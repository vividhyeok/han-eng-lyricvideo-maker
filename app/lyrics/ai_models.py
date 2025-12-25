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
        
        # Create indexed lyrics for better AI guidance
        indexed_lyrics = [{"index": i, "text": line} for i, line in enumerate(lyrics)]
        
        user_content = {
            "context": f"Artist: {artist}, Title: {title}",
            "lyrics": indexed_lyrics
        }
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_content, ensure_ascii=False)}
                ],
                temperature=0.1,
            )
            
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.strip("`")
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            try:
                parsed_content = json.loads(content)
                translated_list = []
                
                # Handle new object format
                if isinstance(parsed_content, list) and len(parsed_content) > 0 and isinstance(parsed_content[0], dict):
                    print("[DEBUG] AI returned object list format")
                    # Sort by index just in case
                    parsed_content.sort(key=lambda x: x.get('index', 0))
                    # Create a map
                    trans_map = {item.get('index'): item.get('translated', '') for item in parsed_content}
                    
                    for i in range(len(lyrics)):
                        translated_list.append(trans_map.get(i, "")) # Empty string if missing
                        
                elif isinstance(parsed_content, list):
                    print("[DEBUG] AI returned string list format (fallback)")
                    # Fallback for string array
                    translated_list = [str(line).strip() for line in parsed_content]
                else:
                    print("[DEBUG] AI returned unknown format (fallback)")
                    # Fallback
                    translated_list = [line.strip() for line in content.splitlines() if line.strip()]
            
            except json.JSONDecodeError:
                print("[DEBUG] JSON decode error (fallback)")
                translated_list = [line.strip() for line in content.splitlines() if line.strip()]
            
            return translated_list
            
        except Exception as e:
            print(f"[ERROR] OpenAI translation failed: {e}")
            return lyrics
    
    def _get_system_prompt(self) -> str:
        return (
            "You are a strict lyric translation engine specialized in HIP-HOP/RAP. Your priority is 1:1 LINE ALIGNMENT.\n"
            "You will receive a list of objects: [{'index': 0, 'text': '...'}, ...]\n"
            "You MUST return a JSON array of objects: [{'index': 0, 'translated': '...'}, ...]\n"
            "\n"
            "CRITICAL RULES:\n"
            "1. The output array MUST have the EXACT SAME length as the input array.\n"
            "2. Every 'index' from the input MUST appear in the output with a translation.\n"
            "3. DO NOT MERGE LINES. If the input has 3 short lines, output 3 short lines.\n"
            "4. HANDLE ENJAMBMENT (Split Sentences):\n"
            "   - If a sentence is split across lines, understand the full context from adjacent lines.\n"
            "   - Translate the fragment in the current line so it flows naturally into the next line.\n"
            "   - Example Input: ['Yo, ZENE놈은 양산', '하나 없던 채로 시작해서']\n"
            "   - Example Output: ['Yo, ZENE started without', 'even a single parasol']\n"
            "5. TONE & STYLE (HIP-HOP):\n"
            "   - Use slang, street language, and AAVE where appropriate.\n"
            "   - DO NOT CENSOR profanity. Keep the translation raw and aggressive if the original is.\n"
            "   - Interpret context markers like '여긴' (Here) based on the genre. In Hip-hop, 'Here' often refers to the 'scene', 'game', or 'industry'.\n"
            "6. For mixed Korean-English lines: Keep English AS IS, translate Korean.\n"
            "7. For 100% English lines: Copy them exactly.\n"
            "8. Output English ONLY (no Korean characters in 'translated' field).\n"
        )


class DeepSeekModel(TranslationModel):
    """DeepSeek AI models"""
    
    def __init__(self, model_name: str = "deepseek-chat"):
        self.model_name = model_name
        self.client = None
        
        try:
            from openai import AsyncOpenAI  # DeepSeek uses OpenAI-compatible API
            api_key = os.getenv("DEEPSEEK_API_KEY")
            base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
            
            if api_key:
                self.client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=base_url
                )
        except ImportError:
            pass
    
    def is_available(self) -> bool:
        return self.client is not None
    
    async def translate(self, lyrics: List[str], artist: str, title: str) -> List[str]:
        if not self.client:
            return lyrics
        
        system_prompt = self._get_system_prompt()
        
        # Create indexed lyrics for better AI guidance
        indexed_lyrics = [{"index": i, "text": line} for i, line in enumerate(lyrics)]
        
        user_content = {
            "context": f"Artist: {artist}, Title: {title}",
            "lyrics": indexed_lyrics
        }
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_content, ensure_ascii=False)}
                ],
                temperature=0.1,
            )
            
            content = response.choices[0].message.content.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.strip("`")
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            try:
                parsed_content = json.loads(content)
                translated_list = []
                
                # Handle new object format
                if isinstance(parsed_content, list) and len(parsed_content) > 0 and isinstance(parsed_content[0], dict):
                    # Sort by index just in case
                    parsed_content.sort(key=lambda x: x.get('index', 0))
                    # Create a map
                    trans_map = {item.get('index'): item.get('translated', '') for item in parsed_content}
                    
                    for i in range(len(lyrics)):
                        translated_list.append(trans_map.get(i, "")) # Empty string if missing
                        
                elif isinstance(parsed_content, list):
                    # Fallback for string array
                    translated_list = [str(line).strip() for line in parsed_content]
                else:
                    # Fallback
                    translated_list = [line.strip() for line in content.splitlines() if line.strip()]
            
            except json.JSONDecodeError:
                translated_list = [line.strip() for line in content.splitlines() if line.strip()]
            
            return translated_list
            
        except Exception as e:
            print(f"[ERROR] DeepSeek translation failed: {e}")
            return lyrics
    
    def _get_system_prompt(self) -> str:
        return (
            "You are a strict lyric translation engine specialized in HIP-HOP/RAP. Your priority is 1:1 LINE ALIGNMENT.\n"
            "You will receive a list of objects: [{'index': 0, 'text': '...'}, ...]\n"
            "You MUST return a JSON array of objects: [{'index': 0, 'translated': '...'}, ...]\n"
            "\n"
            "CRITICAL RULES:\n"
            "1. The output array MUST have the EXACT SAME length as the input array.\n"
            "2. Every 'index' from the input MUST appear in the output with a translation.\n"
            "3. DO NOT MERGE LINES. If the input has 3 short lines, output 3 short lines.\n"
            "4. HANDLE ENJAMBMENT (Split Sentences):\n"
            "   - If a sentence is split across lines, understand the full context from adjacent lines.\n"
            "   - Translate the fragment in the current line so it flows naturally into the next line.\n"
            "   - Example Input: ['Yo, ZENE놈은 양산', '하나 없던 채로 시작해서']\n"
            "   - Example Output: ['Yo, ZENE started without', 'even a single parasol']\n"
            "5. TONE & STYLE (HIP-HOP):\n"
            "   - Use slang, street language, and AAVE where appropriate.\n"
            "   - DO NOT CENSOR profanity. Keep the translation raw and aggressive if the original is.\n"
            "   - Interpret context markers like '여긴' (Here) based on the genre. In Hip-hop, 'Here' often refers to the 'scene', 'game', or 'industry'.\n"
            "6. For mixed Korean-English lines: Keep English AS IS, translate Korean.\n"
            "7. For 100% English lines: Copy them exactly.\n"
            "8. Output English ONLY (no Korean characters in 'translated' field).\n"
        )


class GeminiModel(TranslationModel):
    """Google Gemini models"""
    
    def __init__(self, model_name: str = "gemini-2.0-flash"):
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
        
        # Create indexed lyrics for better AI guidance
        indexed_lyrics = [{"index": i, "text": line} for i, line in enumerate(lyrics)]
        
        user_content = {
            "context": f"Artist: {artist}, Title: {title}",
            "lyrics": indexed_lyrics
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
                parsed_content = json.loads(content)
                translated_list = []
                
                # Handle new object format
                if isinstance(parsed_content, list) and len(parsed_content) > 0 and isinstance(parsed_content[0], dict):
                    # Sort by index just in case
                    parsed_content.sort(key=lambda x: x.get('index', 0))
                    # Create a map
                    trans_map = {item.get('index'): item.get('translated', '') for item in parsed_content}
                    
                    for i in range(len(lyrics)):
                        translated_list.append(trans_map.get(i, "")) # Empty string if missing
                        
                elif isinstance(parsed_content, list):
                    # Fallback for string array
                    translated_list = [str(line).strip() for line in parsed_content]
                else:
                    # Fallback
                    translated_list = [line.strip() for line in content.splitlines() if line.strip()]
            
            except json.JSONDecodeError:
                translated_list = [line.strip() for line in content.splitlines() if line.strip()]
            
            return translated_list
            
        except Exception as e:
            print(f"[ERROR] Gemini translation failed: {e}")
            return lyrics
    
    def _get_system_prompt(self) -> str:
        return (
            "You are a strict lyric translation engine specialized in HIP-HOP/RAP. Your priority is 1:1 LINE ALIGNMENT.\n"
            "You will receive a list of objects: [{'index': 0, 'text': '...'}, ...]\n"
            "You MUST return a JSON array of objects: [{'index': 0, 'translated': '...'}, ...]\n"
            "\n"
            "CRITICAL RULES:\n"
            "1. The output array MUST have the EXACT SAME length as the input array.\n"
            "2. Every 'index' from the input MUST appear in the output with a translation.\n"
            "3. DO NOT MERGE LINES. If the input has 3 short lines, output 3 short lines.\n"
            "4. HANDLE ENJAMBMENT (Split Sentences):\n"
            "   - If a sentence is split across lines, understand the full context from adjacent lines.\n"
            "   - Translate the fragment in the current line so it flows naturally into the next line.\n"
            "   - Example Input: ['Yo, ZENE놈은 양산', '하나 없던 채로 시작해서']\n"
            "   - Example Output: ['Yo, ZENE started without', 'even a single parasol']\n"
            "5. TONE & STYLE (HIP-HOP):\n"
            "   - Use slang, street language, and AAVE where appropriate.\n"
            "   - DO NOT CENSOR profanity. Keep the translation raw and aggressive if the original is.\n"
            "   - Interpret context markers like '여긴' (Here) based on the genre. In Hip-hop, 'Here' often refers to the 'scene', 'game', or 'industry'.\n"
            "6. For mixed Korean-English lines: Keep English AS IS, translate Korean.\n"
            "7. For 100% English lines: Copy them exactly.\n"
            "8. Output English ONLY (no Korean characters in 'translated' field).\n"
        )


# Model registry
AVAILABLE_MODELS = {
    "gpt-4o-mini": ("OpenAI GPT-4o Mini", lambda: OpenAIModel("gpt-4o-mini")),
    "gpt-4o": ("OpenAI GPT-4o", lambda: OpenAIModel("gpt-4o")),
    "gpt-4-turbo": ("OpenAI GPT-4 Turbo", lambda: OpenAIModel("gpt-4-turbo")),
    "deepseek-chat": ("DeepSeek Chat", lambda: DeepSeekModel("deepseek-chat")),
    "gemini-2.0-flash": ("Google Gemini 2.0 Flash", lambda: GeminiModel("gemini-2.0-flash")),
    "gemini-2.0-flash-lite": ("Google Gemini 2.0 Flash Lite", lambda: GeminiModel("gemini-2.0-flash-lite")),
    "gemini-1.5-pro": ("Google Gemini 1.5 Pro", lambda: GeminiModel("gemini-1.5-pro")),
    "gemini-pro": ("Google Gemini Pro (Legacy)", lambda: GeminiModel("gemini-2.0-flash")), # Fallback alias
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
