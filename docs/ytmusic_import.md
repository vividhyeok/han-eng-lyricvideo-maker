# YouTube Music JSON Import

This document explains how to import YouTube Music playlists/albums/queues that were exported via a Chrome extension.

## Export JSON schema

* `schema_version`: **1** (required)
* `type`: `"playlist" | "album" | "queue"` (string)
* `name`: name of the collection
* `source`: `"ytmusic"` (required)
* `exportedAt`: ISO8601 timestamp string
* `items`: array of track objects with:
  * `videoId` (required)
  * `title` (required)
  * `artist` (required)
  * `album` (optional)
  * `durationMs` (optional)
  * `thumbnails` (optional array) — first entry’s `url`/`src` is used as album art

See `ytmusic_export.sample.json` for a concrete example.

## Importing via UI

1. Open the app and click **Import YT Music JSON** in the top bar.
2. Pick the exported JSON file.
3. A preview dialog shows the track list; sort if needed, then click **Enqueue All**.
4. Tracks are added to the queue with YouTube Music audio (video ID based) and will process like normal jobs.

## Batch processing

`batch_jobs.json` supports a new job entry:

```json
[
  { "type": "ytmusic_export", "path": "ytmusic_export.sample.json" }
]
```

`run_batch.py` will expand the export into individual jobs automatically, preferring the video IDs for audio downloads.

## Lyric sourcing & caching

When processing a track:

1. Try to fetch LRC from Genie (auto).
2. If a cached mapping exists under `data/cache/lrc_mapping.json`, reuse the stored LRC.
3. Otherwise the Lyric Sync dialog is shown so you can sync manually. The resulting LRC is saved to `data/lyrics/` **and** recorded in the mapping cache so future runs become automatic.

Manual syncing uses the track’s audio (downloaded by video ID) and your pasted lyrics.
