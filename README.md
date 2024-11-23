# PODCAST SYNC AUTOMATION

## Overview
`podcast_sync.py` automates the process of syncing the latest podcast episode from an RSS feed to a Webflow CMS collection. It handles fetching episode details, formatting content, and publishing to Webflow.

---

## Key Features

### RSS Feed Integration
- Fetches the latest episode from the Buzzsprout RSS feed.
- Extracts episode details: title, number, description, and audio URL.
- Cleans HTML from descriptions.

### Platform Link Generation
- **Apple Podcasts**: Scrapes episode-specific links.
- **Spotify**: Uses the Spotify API to retrieve episode links.
- **Goodpods**: Generates links using the episode number and title.

### Content Formatting
- Generates URL-friendly slugs.
- Cleans HTML from descriptions.
- Formats excerpts to 73 characters.
- Applies default episode color.
- Sets featured status.

### Webflow Integration
- Maps RSS feed data to Webflow collection fields.
- Validates fields against the collection schema.
- Publishes episodes using the Webflow v2 API.
- Includes error reporting and logging.

---

## Configuration
- Uses `config.yaml` for:
  - Webflow API credentials and collection ID.
  - RSS feed URL.
  - Platform-specific settings (Spotify API, base URLs).
  - Default episode styling.

---

## Logging
- Writes detailed debug logs to `debug_log.txt`.
- Logs API responses and errors.
- Saves request bodies to `test_rest.json` for debugging purposes.

---

## Error Handling
- **Custom Error Handling**: `PodcastSyncError` for specific error cases.
- Detailed error logging for API responses.
- Validates required fields.
- Normalizes field names.

---

## Usage
- To run the script:
  ```bash
  python3 podcast_sync.py
  ```

---

## Requirements
- **Python 3.x**
- Required packages:
  - `feedparser`
  - `requests`
  - `beautifulsoup4`
  - `pyyaml`
- Valid Webflow API token and collection access.
- Spotify API credentials (for Spotify links).
