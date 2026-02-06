from ytmusicapi import YTMusic
import json

def test():
    yt = YTMusic(language='ko')
    query = "IU"
    print(f"Searching for: {query}")
    results = yt.search(query, filter="songs", limit=3)
    
    for i, res in enumerate(results):
        print(f"\nResult {i}: {res.get('resultType')}")
        # print(f"Full data: {json.dumps(res, indent=2)}")
        print(f"Title: {res.get('title')}")
        v_id = res.get('videoId')
        print(f"VideoId: {v_id}")
        if v_id:
            try:
                watch = yt.get_watch_playlist(v_id)
                lyrics_id = watch.get('lyrics')
                if lyrics_id:
                    print(f"Lyrics ID: {lyrics_id}")
                    lyrics = yt.get_lyrics(lyrics_id)
                    print(f"Lyrics snippet: {lyrics.get('lyrics')[:50]}...")
                else:
                    print("No lyrics found.")
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    test()
