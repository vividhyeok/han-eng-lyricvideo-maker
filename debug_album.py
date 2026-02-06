from ytmusicapi import YTMusic
import sys
import json

# Force UTF-8 for print
sys.stdout.reconfigure(encoding='utf-8')

def debug_album():
    yt = YTMusic(language='ko')
    # Search for an album first to get a valid browseId
    query = "system seoul ss-pop" 
    print(f"--- Debugging Album Search for '{query}' ---")
    
    albums = yt.search(query, filter="albums", limit=1)
    if not albums:
        print("No albums found.")
        return

    album = albums[0]
    browse_id = album.get("browseId")
    title = album.get("title")
    print(f"Found Album: {title} (ID: {browse_id})")
    
    # 2. Get Album Details
    print(f"\n--- Fetching Album Details for {browse_id} ---")
    try:
        album_data = yt.get_album(browse_id)
        # print("Album Data Keys:", album_data.keys())
        tracks = album_data.get('tracks', [])
        print(f"Found {len(tracks)} tracks.")
        
        for i, track in enumerate(tracks):
            vid = track.get('videoId')
            print(f"{i+1}. {track.get('title')} (ID: {vid})")
            if not vid and i == 0:
                 print("DEBUG: Track 1 Raw Data:")
                 print(json.dumps(track, indent=2, ensure_ascii=False))
            
        if not tracks:
            print("Full Album Data Dump:")
            print(json.dumps(album_data, indent=2, ensure_ascii=False))
            
    except Exception as e:
        print(f"Error getting album: {e}")

if __name__ == "__main__":
    debug_album()
