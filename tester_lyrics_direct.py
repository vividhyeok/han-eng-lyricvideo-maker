from ytmusicapi import YTMusic

def test_lyrics_direct():
    yt = YTMusic()
    v_id = "pSUydWEqKwE" # NewJeans Ditto
    print(f"Fetching watch playlist for: {v_id}")
    try:
        watch = yt.get_watch_playlist(v_id)
        lyrics_id = watch.get('lyrics')
        if lyrics_id:
            print(f"Lyrics ID: {lyrics_id}")
            lyrics_data = yt.get_lyrics(lyrics_id)
            print(f"Lyrics data keys: {lyrics_data.keys()}")
            print(f"Lyrics text: {lyrics_data.get('lyrics')[:100]}...")
        else:
            print("No lyrics ID found.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_lyrics_direct()
