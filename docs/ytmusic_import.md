# YouTube Music JSON Import

This document explains how to import YouTube Music playlists/albums/queues that were exported via the included Chrome extension.

## Chrome Extension

The `chrome-extension/` folder contains a Manifest V3 extension that allows you to:
1. Scrape the "Now Playing" queue from `music.youtube.com`.
2. Manage a list of tracks to export.
3. Copy the JSON payload to clipboard or save it.

### Installation
1. Open Chrome and go to `chrome://extensions`.
2. Enable **Developer mode**.
3. Click **Load unpacked** and select the `chrome-extension` folder in this repository.

### Usage
1. Navigate to YouTube Music and play a song/queue.
2. Click the extension icon.
3. Click **Import Queue from Tab**.
4. Click **Copy JSON to Clipboard**.

## Export JSON schema

* `schema_version`: **1** (required)
* `type`: `"playlist" | "album" | "queue"` (string)
* `name`: name of the collection
* `source`: `"ytmusic"` (required)
* `exported_at`: ISO8601 timestamp string
* `items`: array of track objects with:
  * `video_id` (required, snake_case preferred, camelCase `videoId` also supported)
  * `title` (required)
  * `artist` (required)
  * `album` (optional)
  * `duration_ms` (optional)
  * `thumbnail_url` (optional)

See `ytmusic_queue_export.sample.json` for a concrete example.

## Importing via UI

1. Open the app and click **Import YT Music JSON** in the top bar.
2. Choose **Load from File** or **Paste from Clipboard**.
3. A preview dialog shows the track list; sort if needed, then click **Enqueue All**.
4. Tracks are added to the queue with YouTube Music audio (video ID based) and will process like normal jobs.

## Batch processing

`batch_jobs.json` supports a new job entry:

```json
[
  { "type": "ytmusic_export", "path": "ytmusic_queue_export.sample.json" }
]
```

`run_batch.py` will expand the export into individual jobs automatically, preferring the video IDs for audio downloads.

## Lyric sourcing & caching

When processing a track:

1. Try to fetch LRC from Genie (auto).
2. If a cached mapping exists under `data/cache/lrc_mapping.json`, reuse the stored LRC.
3. Otherwise the Lyric Sync dialog is shown so you can sync manually. The resulting LRC is saved to `data/lyrics/` **and** recorded in the mapping cache so future runs become automatic.

Manual syncing uses the track’s audio (downloaded by video ID) and your pasted lyrics.
