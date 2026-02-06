from ytmusicapi import YTMusic
from typing import List, Dict, Any, Optional
import os
import re

def is_korean(text: str) -> bool:
    """Check if the text contains Korean characters"""
    if not text:
        return False
    return bool(re.search("[가-힣]", text))

def calculate_relevance(query: str, item: Dict[str, Any]) -> int:
    """
    Calculate relevance score for sorting results.
    Score components:
    - 50 pts: Artist contains query parts
    - 50 pts: Title contains query score
    - 20 pts: Is Korean (bonus)
    - 100 pts: Exact title match
    """
    score = 0
    query_parts = query.lower().split()
    
    title = item.get('title', '').lower()
    artist = item.get('artist', '').lower()
    
    # 1. Exact Title Match
    if title == query.lower():
        score += 100
    
    # 2. Query parts presence
    matches = 0
    for part in query_parts:
        if part in title or part in artist:
            matches += 1
    
    if len(query_parts) > 0:
        score += (matches / len(query_parts)) * 100

    # 3. Korean Bonus
    if is_korean(title) or is_korean(artist):
        score += 20
        
    return score

class YTMusicHandler:
    def __init__(self):
        self.yt = YTMusic(language='ko')

    def search_songs(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for songs on YouTube Music with merged strategy (Specific + Broad)"""
        try:
            # 1. Fetch from "songs" filter
            results_strict = self.yt.search(query, filter="songs", limit=limit)
            
            # 2. Fetch from general search (unfiltered) to catch items missed by strict filter
            # (e.g. sometimes specific remixes appear as Videos or top results only)
            results_broad = self.yt.search(query, limit=limit)
            
            # 3. Filter broad results
            filtered_broad = []
            for res in results_broad:
                r_type = res.get('resultType', '')
                # Accept songs and videos. 'video' type is common for official audio/MV.
                if r_type in ['song', 'video']:
                    filtered_broad.append(res)
            
            # 4. Merge results (Strict first, then Broad)
            combined_results = []
            seen_ids = set()
            
            def add_result(res):
                vid = res.get('videoId')
                if vid and vid not in seen_ids:
                    seen_ids.add(vid)
                    combined_results.append(res)

            for res in results_strict:
                add_result(res)
                
            for res in filtered_broad:
                add_result(res)
            
            print(f"DEBUG: [V2_MERGED] Found {len(results_strict)} strict, {len(filtered_broad)} broad. Total merged: {len(combined_results)}")
            formatted = []
            
            for res in combined_results:
                video_id = res.get('videoId')
                if not video_id:
                    continue
                    
                artists = res.get('artists', [])
                artist_names = ", ".join([a.get('name') for a in artists])
                
                thumbnails = res.get('thumbnails', [])
                album_art = thumbnails[-1].get('url') if thumbnails else ""
                if album_art and "=w" in album_art:
                    album_art = album_art.split("=w")[0] + "=w1200-h1200"
                
                item = {
                    'title': res.get('title'),
                    'artist': artist_names,
                    'album': res.get('album', {}).get('name', 'Single'),
                    'video_id': video_id,
                    'youtube_url': f"https://www.youtube.com/watch?v={video_id}",
                    'album_art': album_art,
                    'duration': res.get('duration'),
                    'source': 'ytmusic'
                }
                formatted.append(item)
            
            # 5. Sort by relevance (custom scoring)
            formatted.sort(key=lambda x: calculate_relevance(query, x), reverse=True)
            
            return formatted[:limit] 
            
        except Exception as e:
            print(f"[ERROR] YTMusic search failed: {e}")
            return []

    def search_albums(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for albums on YouTube Music"""
        try:
            results = self.yt.search(query, filter="albums", limit=limit)
            formatted = []
            for res in results:
                browse_id = res.get('browseId')
                if not browse_id:
                    continue
                    
                artists = res.get('artists', [])
                artist_names = ", ".join([a.get('name') for a in artists])
                
                thumbnails = res.get('thumbnails', [])
                album_art = thumbnails[-1].get('url') if thumbnails else ""
                if album_art and "=w" in album_art:
                    album_art = album_art.split("=w")[0] + "=w1200-h1200"
                
                item = {
                    'title': res.get('title'),
                    'artist': artist_names,
                    'browse_id': browse_id,
                    'album_art': album_art,
                    'year': res.get('year'),
                    'source': 'ytmusic_album'
                }
                formatted.append(item)
            
            # Sort albums too
            formatted.sort(key=lambda x: calculate_relevance(query, x), reverse=True)
            
            return formatted
        except Exception as e:
            print(f"[ERROR] YTMusic album search failed: {e}")
            return []

    def get_album_tracks(self, browse_id: str) -> List[Dict[str, Any]]:
        """Retrieve all tracks from an album"""
        try:
            album_data = self.yt.get_album(browse_id)
            tracks = album_data.get('tracks', [])
            formatted = []
            
            album_title = album_data.get('title')
            artists = album_data.get('artists', [])
            album_artist = ", ".join([a.get('name') for a in artists])
            
            # Album level art
            thumbnails = album_data.get('thumbnails', [])
            # ... (rest of image code)
            album_art = thumbnails[-1].get('url') if thumbnails else ""
            if album_art and "=w" in album_art:
                album_art = album_art.split("=w")[0] + "=w1200-h1200"

            for i, track in enumerate(tracks):
                video_id = track.get('videoId')
                
                # Album Artist
                track_artists = track.get('artists', [])
                artist_names = ", ".join([a.get('name') for a in track_artists]) if track_artists else album_artist

                # Fallback: If videoId is missing, try searching for the track
                if not video_id:
                    try:
                        search_query = f"{artist_names} {track.get('title')}"
                        # print(f"DEBUG: Recovering missing ID for '{search_query}'...")
                        fallback_res = self.yt.search(search_query, filter="songs", limit=1)
                        if fallback_res:
                            video_id = fallback_res[0].get('videoId')
                    except Exception as e:
                         print(f"Fallback search failed: {e}")

                if not video_id:
                    continue
                
                # Use track artists if available, otherwise fallback to album artist

                formatted.append({
                    'title': track.get('title'),
                    'artist': artist_names,
                    'album': album_title,
                    'video_id': video_id,
                    'youtube_url': f"https://www.youtube.com/watch?v={video_id}",
                    'album_art': album_art,
                    'duration': track.get('duration'),
                    'track_no': i + 1,
                    'source': 'ytmusic'
                })
            return formatted
        except Exception as e:
            print(f"[ERROR] YTMusic get album tracks failed: {e}")
            return []

    def get_lyrics(self, video_id: str) -> Optional[str]:
        """Fetch lyrics for a specific video ID"""
        try:
            watch_playlist = self.yt.get_watch_playlist(video_id)
            lyrics_browse_id = watch_playlist.get('lyrics')
            
            if lyrics_browse_id:
                lyrics_data = self.yt.get_lyrics(lyrics_browse_id)
                return lyrics_data.get('lyrics')
        except Exception as e:
            print(f"[ERROR] YTMusic lyrics fetch failed for {video_id}: {e}")
        return None

def ytmusic_search(query: str, limit: int = 15) -> List[Dict[str, Any]]:
    handler = YTMusicHandler()
    return handler.search_songs(query, limit)

def ytmusic_get_lyrics(video_id: str) -> Optional[str]:
    handler = YTMusicHandler()
    return handler.get_lyrics(video_id)

def ytmusic_search_albums(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    handler = YTMusicHandler()
    return handler.search_albums(query, limit)

def ytmusic_get_album_tracks(browse_id: str) -> List[Dict[str, Any]]:
    handler = YTMusicHandler()
    return handler.get_album_tracks(browse_id)
