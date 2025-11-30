"""
Test script for improved Korean rap lyrics translation
Tests English detection and mixed language handling
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set test artist and title
os.environ['CURRENT_ARTIST'] = 'Test Artist'
os.environ['CURRENT_TITLE'] = 'Test Song'

from app.lyrics.openai_handler import translate_lyrics, is_english

async def test_translation():
    print("=" * 60)
    print("Testing Korean Rap Lyrics Translation Improvements")
    print("=" * 60)
    
    # Test cases
    test_lyrics = [
        "Yeah yeah let's go",  # 100% English - should skip
        "I'm on the 탑",  # Mixed - should translate 탑 to top
        "나는 rapper야",  # Mixed - should translate to "I'm a rapper"
        "시작해볼까",  # 100% Korean - should translate
        "",  # Empty line
        "이건 내가",  # Multi-line sentence part 1
        "만든 노래야",  # Multi-line sentence part 2
        "Yo what's up 형들",  # Mixed with slang
    ]
    
    print("\n📝 Test Lyrics:")
    for i, lyric in enumerate(test_lyrics, 1):
        is_eng = is_english(lyric)
        print(f"{i}. '{lyric}' - English: {is_eng}")
    
    print("\n🔄 Translating...")
    try:
        translated = await translate_lyrics(test_lyrics)
        
        print("\n✅ Translation Results:")
        print("-" * 60)
        for i, (original, trans) in enumerate(zip(test_lyrics, translated), 1):
            print(f"{i}. Original: '{original}'")
            print(f"   Translated: '{trans}'")
            print()
        
        print("=" * 60)
        print("✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Translation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_translation())
