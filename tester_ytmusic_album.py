from ytmusicapi import YTMusic
import json

def test_album_search(query):
    yt = YTMusic(language='ko')
    print(f"Searching for albums with query: {query}")
    results = yt.search(query, filter="albums", limit=3)
    
    for i, album in enumerate(results):
        print(f"\nAlbum {i}:")
        print(f"Title: {album.get('title')}")
        print(f"Artist: {', '.join([a.get('name') for a in album.get('artists', [])])}")
        browse_id = album.get('browseId')
        print(f"Browse ID: {browse_id}")
        
        if browse_id:
            try:
                album_data = yt.get_album(browse_id)
                print(f"Found {len(album_data.get('tracks', []))} tracks.")
                for j, track in enumerate(album_data.get('tracks', [])[:3]):
                    print(f"  Track {j+1}: {track.get('title')} (ID: {track.get('videoId')})")
            except Exception as e:
                print(f"Error fetching album info: {e}")

if __name__ == "__main__":
    test_album_search("NewJeans Get Up")
