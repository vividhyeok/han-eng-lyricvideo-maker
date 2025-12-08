# soundcloud_handler.py

from typing import Optional, List, Dict, Any
import os
import yt_dlp
from app.config.paths import TEMP_DIR, ensure_data_dirs

def search_soundcloud(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search SoundCloud using yt-dlp (scsearch).
    Returns a list of dicts with title, uploader, duration, url, thumbnail.
    """
    opts = {
        'quiet': True,
        'skip_download': True,
        'noplaylist': True,
        'extract_flat': True,
    }

    print(f"[DEBUG] Searching SoundCloud for: {query}")

    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            # scsearch{limit}:{query}
            info = ydl.extract_info(f"scsearch{limit}:{query}", download=False)
            entries = info.get('entries', [])
        except Exception as e:
            print(f"[ERROR] SoundCloud search failed: {e}")
            return []

    formatted_results = []
    for entry in entries:
        duration = entry.get('duration')
        formatted_results.append({
            'title': entry.get('title', 'Unknown Title'),
            'uploader': entry.get('uploader', 'Unknown Artist'),
            'link': entry.get('url', ''),
            'thumbnail': entry.get('thumbnail', ''), # SoundCloud thumbnails might be missing in flat extraction
            'duration': _format_duration(duration) if duration else 'N/A',
            'duration_sec': duration
        })

    return formatted_results

def download_soundcloud_audio(url: str, output_path: Optional[str] = None) -> Optional[str]:
    """
    Download audio from SoundCloud URL.
    """
    ensure_data_dirs()
    
    if not output_path:
        # Default to temp dir with a generic name if not provided (though usually caller provides it)
        # But yt-dlp needs a template. 
        # We'll let yt-dlp handle filename if output_path is directory, or specific if file.
        pass

    # If output_path is provided, we use it as the template
    # But yt-dlp expects a template like "path/to/file.%(ext)s"
    
    # Let's assume output_path is the full desired path WITHOUT extension, or we handle it.
    # Actually, standardizing to MP3 is best.
    
    if output_path and output_path.endswith('.mp3'):
        out_tmpl = output_path[:-4] # Strip extension for yt-dlp template
    elif output_path:
        out_tmpl = output_path
    else:
        out_tmpl = os.path.join(TEMP_DIR, '%(title)s')

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': out_tmpl,
        'quiet': False,
        'overwrite': True,
    }

    print(f"[DEBUG] Downloading SoundCloud audio: {url}")
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        # The file should be at out_tmpl + .mp3
        final_path = out_tmpl + ".mp3"
        if os.path.exists(final_path):
            print(f"[DEBUG] Download successful: {final_path}")
            return final_path
        else:
            # Sometimes yt-dlp might not add extension if it's already in name? 
            # Or if original was used. Check out_tmpl itself?
            if os.path.exists(out_tmpl):
                 return out_tmpl
            print(f"[ERROR] Downloaded file not found at expected path: {final_path}")
            return None
            
    except Exception as e:
        print(f"[ERROR] SoundCloud download failed: {e}")
        return None

def _format_duration(seconds: Optional[float]) -> str:
    if not seconds:
        return "N/A"
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"
