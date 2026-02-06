from ytmusicapi import YTMusic
import json

def test_ytmusic_search(query):
    yt = YTMusic()
    print(f"Searching for: {query}")
    
    # 1. Search for songs
    search_results = yt.search(query, limit=5)
    
    # print(f"Raw results: {json.dumps(search_results, indent=2)}")
    
    if not search_results:
        print("No results found.")
        return

    results = []
    for song in search_results:
        # print(f"DEBUG: Song keys: {song.keys()}")
        video_id = song.get('videoId')
        # If result type is 'video', it might have videoId. If it's 'song', it should too.
        title = song.get('title')
        artists = ", ".join([a.get('name') for a in song.get('artists', [])])
        album = song.get('album', {}).get('name')
        duration = song.get('duration')
        
        print(f"\n--- Found Song: {title} by {artists} ---")
        print(f"Video ID: {video_id}")
        
        # 2. Get lyrics (if available)
        lyrics = None
        try:
            if not video_id:
                print("No video ID for this result, skipping lyrics.")
                continue
                
            watch_playlist = yt.get_watch_playlist(video_id)
            lyrics_browse_id = watch_playlist.get('lyrics')
            
            if lyrics_browse_id:
                lyrics_data = yt.get_lyrics(lyrics_browse_id)
                lyrics = lyrics_data.get('lyrics')
                print("Lyrics found!")
            else:
                print("No lyrics browse ID found for this song.")
        except Exception as e:
            import traceback
            print(f"Error fetching lyrics for {video_id}: {e}")
            traceback.print_exc()
            
        results.append({
            'title': title,
            'artists': artists,
            'album': album,
            'video_id': video_id,
            'duration': duration,
            'has_lyrics': lyrics is not None,
            'lyrics_preview': lyrics[:100] + "..." if lyrics else None
        })
        
    return results

if __name__ == "__main__":
    # Test with a popular song that likely has lyrics
    test_ytmusic_search("NewJeans OMG")
