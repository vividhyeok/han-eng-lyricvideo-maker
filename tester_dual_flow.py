import asyncio
import os
import sys

# 프로젝트 루트를 path에 추가
sys.path.append(os.getcwd())

from app.sources.ytmusic_handler import ytmusic_search, ytmusic_get_lyrics
from app.sources.genie_handler import search_genie_songs, get_genie_lyrics

async def test_dual_lyrics(query):
    print(f"=== Testing Dual Lyrics Flow for: {query} ===")
    
    # 1. YT Music Search
    yt_results = ytmusic_search(query, limit=1)
    print(f"YT Search output: {yt_results}")
    if not yt_results:
        print("No YT Music results.")
        return

    song = yt_results[0]
    print(f"Found on YT Music: {song['title']} by {song['artist']}")
    print(f"Album Art: {song['album_art']}")

    # 2. Try YT Music Lyrics
    print("\nAttempting Step 1: YouTube Music Lyrics...")
    lyrics = ytmusic_get_lyrics(song['video_id'])
    
    if lyrics:
        print("Success: Lyrics found on YouTube Music!")
        # print(lyrics[:200])
    else:
        print("Failed: No lyrics on YouTube Music.")
        
        # 3. Try Genie Music Lyrics
        print("\nAttempting Step 2: Genie Music Lyrics...")
        genie_results = search_genie_songs(f"{song['artist']} {song['title']}", limit=1)
        if genie_results:
            title, song_id, extra, art, dur = genie_results[0]
            print(f"Found on Genie: {title} (ID: {song_id})")
            lyrics = get_genie_lyrics(song_id)
            if lyrics:
                print("Success: Lyrics found on Genie Music!")
                # print(lyrics[:200])
            else:
                print("Failed: No lyrics on Genie Music.")
        else:
            print("Failed: Could not find song on Genie Music.")

    if not lyrics:
        print("\nFinal Step: Need manual LRC mapping fallback.")
    else:
        print("\nFlow complete: Lyrics acquired.")

if __name__ == "__main__":
    # Test with a song that definitely has lyrics (e.g., IU - Love Wins All)
    asyncio.run(test_dual_lyrics("IU Love Wins All"))
    print("\n" + "="*50 + "\n")
    # Test with a more obscure song or one that might fail on YT but win on Genie
    asyncio.run(test_dual_lyrics("ZENE THE ZILLA"))
