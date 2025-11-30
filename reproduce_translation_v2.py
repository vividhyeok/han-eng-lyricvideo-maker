import asyncio
import os
from app.lyrics.openai_handler import translate_lyrics

# Mock lyrics for testing
TEST_LYRICS = [
    "너를 만나서 행복했어",
    "하지만 이제는 헤어져야 할 시간",
    "우리 다시 만날 수 있을까",
    "바람이 불어오는 곳에서",
    "기다릴게 영원히"
]

async def main():
    print("Original Lyrics:")
    for line in TEST_LYRICS:
        print(f"- {line}")
    
    print("\nTranslating...")
    translated = await translate_lyrics(TEST_LYRICS)
    
    print("\nTranslated Lyrics:")
    for original, trans in zip(TEST_LYRICS, translated):
        print(f"[{original}] -> [{trans}]")

if __name__ == "__main__":
    asyncio.run(main())
