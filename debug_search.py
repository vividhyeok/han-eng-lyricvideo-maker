from ytmusicapi import YTMusic
import json
import sys

# Force UTF-8 for print
sys.stdout.reconfigure(encoding='utf-8')

def debug_search():
    yt = YTMusic(language='ko')
    query = "Yin and Yang (FANXY CHILD Ver.) (feat. DEAN, PENOMECO)"
    
    print(f"--- Debugging Query: '{query}' ---")
    
    # 1. Try with filter="songs"
    print("\n[Attempt 1] filter='songs'")
    try:
        results_songs = yt.search(query, filter="songs", limit=10)
        print(f"Found {len(results_songs)} results.")
        for i, res in enumerate(results_songs):
            title = res.get('title', 'No Title')
            type_ = res.get('resultType', 'Unknown')
            print(f"{i+1}. [{type_}] {title}")
    except Exception as e:
        print(f"Error in songs filter: {e}")

    # 2. Try General Search
    print("\n[Attempt 2] General Search (No filter)")
    try:
        results_general = yt.search(query, limit=10)
        print(f"Found {len(results_general)} results.")
        for i, res in enumerate(results_general):
            title = res.get('title', 'No Title')
            type_ = res.get('resultType', 'Unknown')
            print(f"{i+1}. [{type_}] {title}")
    except Exception as e:
        print(f"Error in general search: {e}")

if __name__ == "__main__":
    debug_search()
