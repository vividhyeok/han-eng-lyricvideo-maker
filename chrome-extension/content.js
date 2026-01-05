chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'scrapeQueue') {
    scrapeQueue().then(sendResponse);
    return true; // Keep channel open for async response
  }
});

function getText(el) {
  return el ? el.innerText.trim() : null;
}

function getAttr(el, attr) {
  return el ? el.getAttribute(attr) : null;
}

async function scrapeQueue() {
  const items = [];
  const url = window.location.href;
  console.log("[YTMusic Exporter] Scraping URL:", url);

  // --- Strategy 1: Playlist / Album Page ---
  // URL contains 'playlist?list=' or 'browse/' (albums often use browse endpoints)
  // BUT NOT 'watch?v=' (which is playing a playlist)
  if ((url.includes('playlist?list=') || url.includes('/browse/')) && !url.includes('watch?v=')) {
    console.log("[YTMusic Exporter] Detected Playlist/Album View");
    
    // 1. Try to find a global artist from the header (useful for albums)
    // User Selector: #contents > ytmusic-responsive-header-renderer > div.strapline.style-scope.ytmusic-responsive-header-renderer > yt-formatted-string > a
    let headerArtist = "Unknown Artist";
    const headerArtistEl = document.querySelector('#contents > ytmusic-responsive-header-renderer .strapline yt-formatted-string a');
    if (headerArtistEl) {
      headerArtist = getText(headerArtistEl);
    } else {
      // Fallback: sometimes it's just text in the strapline
      const strapline = document.querySelector('ytmusic-responsive-header-renderer .strapline');
      if (strapline) {
        // Strapline often looks like "Album • Artist • Year"
        const text = getText(strapline);
        if (text) {
           const parts = text.split('•');
           if (parts.length >= 2) {
             headerArtist = parts[1].trim();
           } else {
             headerArtist = text;
           }
        }
      }
    }
    console.log("[YTMusic Exporter] Header Artist:", headerArtist);

    // 2. Iterate over list items
    // User Selector: #contents > ytmusic-responsive-list-item-renderer
    const listItems = document.querySelectorAll('#contents > ytmusic-responsive-list-item-renderer');
    console.log("[YTMusic Exporter] Found list items:", listItems.length);
    
    listItems.forEach(item => {
      // Title
      // User Selector: div.flex-columns.style-scope.ytmusic-responsive-list-item-renderer > div.title-column.style-scope.ytmusic-responsive-list-item-renderer > yt-formatted-string > a
      const titleEl = item.querySelector('div.title-column yt-formatted-string a') || item.querySelector('div.title-column yt-formatted-string');
      const title = getText(titleEl);

      // Video ID
      // Look for href in the title link or overlay
      let videoId = null;
      const link = item.querySelector('a[href*="watch?v="]');
      if (link) {
        const href = getAttr(link, 'href');
        const urlParams = new URLSearchParams(href.split('?')[1]);
        videoId = urlParams.get('v');
      }

      // Artist
      // Try secondary column first (playlists often have different artists)
      // Selector: .secondary-flex-columns yt-formatted-string
      let artist = null;
      const secondary = item.querySelectorAll('.secondary-flex-columns yt-formatted-string');
      if (secondary.length > 0) {
        // Usually the first element in secondary columns is the artist
        // It might be a link or text.
        artist = getText(secondary[0]);
        // If it contains bullets (Artist • Album), split it
        if (artist && artist.includes('•')) {
            artist = artist.split('•')[0].trim();
        }
      }
      
      // Fallback to header artist if individual artist not found (common in albums)
      if (!artist || artist === "Unknown Artist") {
        artist = headerArtist;
      }

      // Thumbnail
      const img = item.querySelector('img');
      const thumbnail = getAttr(img, 'src');

      if (videoId && title) {
        items.push({
          video_id: videoId,
          title: title,
          artist: artist,
          thumbnail_url: thumbnail
        });
      }
    });
  }

  // --- Strategy 2: Watch Page (Player) ---
  // URL contains 'watch?v='
  if (url.includes('watch?v=')) {
    console.log("[YTMusic Exporter] Detected Watch/Player View");
    
    // 1. Current Song from Player Bar
    // User Selector for Artist: #layout > ytmusic-player-bar > div.middle-controls.style-scope.ytmusic-player-bar > div.content-info-wrapper.style-scope.ytmusic-player-bar > span > span.subtitle.style-scope.ytmusic-player-bar > yt-formatted-string > a:nth-child(1)
    // User Selector for Title: #layout > ytmusic-player-bar > div.middle-controls.style-scope.ytmusic-player-bar > div.content-info-wrapper.style-scope.ytmusic-player-bar > yt-formatted-string
    
    const playerBar = document.querySelector('ytmusic-player-bar');
    if (playerBar) {
      const contentInfo = playerBar.querySelector('.content-info-wrapper');
      if (contentInfo) {
        // Title
        const titleEl = contentInfo.querySelector('yt-formatted-string.title') || contentInfo.querySelector('.title');
        const title = getText(titleEl);
        
        // Artist
        let artist = "Unknown Artist";
        const subtitleEl = contentInfo.querySelector('.subtitle');
        if (subtitleEl) {
            // Try to find the first link (usually artist)
            const artistLink = subtitleEl.querySelector('a');
            if (artistLink) {
                artist = getText(artistLink);
            } else {
                // Text fallback: "Artist • Album • Year"
                const text = getText(subtitleEl);
                if (text) artist = text.split('•')[0].trim();
            }
        }

        const img = playerBar.querySelector('.image');

        // Video ID from URL (most reliable for current song)
        const urlParams = new URLSearchParams(window.location.search);
        const currentVideoId = urlParams.get('v');

        if (currentVideoId && title) {
           console.log("[YTMusic Exporter] Found current song:", title);
           items.push({
             video_id: currentVideoId,
             title: title,
             artist: artist,
             thumbnail_url: getAttr(img, 'src')
           });
        }
      }
    }

    // 2. Queue (Up Next)
    // Selector: ytmusic-player-queue-item
    const queueItems = document.querySelectorAll('ytmusic-player-queue-item');
    console.log("[YTMusic Exporter] Found queue items:", queueItems.length);
    
    queueItems.forEach(item => {
      const titleEl = item.querySelector('.song-title');
      const artistEl = item.querySelector('.byline');
      const img = item.querySelector('img');
      
      let videoId = null;
      // Try to find video ID in play button or links
      const link = item.querySelector('a[href*="watch?v="]');
      if (link) {
          const href = getAttr(link, 'href');
          const urlParams = new URLSearchParams(href.split('?')[1]);
          videoId = urlParams.get('v');
      } else {
          // Sometimes stored in data attributes
          videoId = getAttr(item, 'data-video-id'); 
      }

      if (videoId) {
        // Avoid duplicates if the current song is also in the queue list
        if (!items.some(i => i.video_id === videoId)) {
            items.push({
                video_id: videoId,
                title: getText(titleEl),
                artist: getText(artistEl),
                thumbnail_url: getAttr(img, 'src')
            });
        }
      }
    });
  }

  console.log("[YTMusic Exporter] Total items scraped:", items.length);
  return { items: items };
}
    queueItems.forEach(item => {
      const titleEl = item.querySelector('.song-title');
      const artistEl = item.querySelector('.byline');
      const img = item.querySelector('img');
      
      let videoId = null;
      // Try to find video ID in play button or links
      const link = item.querySelector('a[href*="watch?v="]');
      if (link) {
          const href = getAttr(link, 'href');
          const urlParams = new URLSearchParams(href.split('?')[1]);
          videoId = urlParams.get('v');
      } else {
          // Sometimes stored in data attributes
          videoId = getAttr(item, 'data-video-id'); 
      }

      if (videoId) {
        // Avoid duplicates if the current song is also in the queue list
        if (!items.some(i => i.video_id === videoId)) {
            items.push({
                video_id: videoId,
                title: getText(titleEl),
                artist: getText(artistEl),
                thumbnail_url: getAttr(img, 'src')
            });
        }
      }
    });
  }

  return { items: items };
}
