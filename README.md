# Podcast Sync Automation

## Overview

`podcast_sync.py` automates the process of syncing podcast episodes from an RSS feed to a Webflow CMS collection. It includes transcription, Q&A generation, and thumbnail creation.

---

## Podcast Retro Sync

`src/podcast_retro_sync.py` is a utility script for retroactively processing existing podcast episodes. It:

- **Processes episodes** that are missing transcripts or other content.
- **Downloads and transcribes** episode audio using OpenAI's Whisper API.
- **Generates AI-powered questions and answers** about each episode.
- **Updates existing Webflow episodes** with:
  - Episode transcripts.
  - Q&A sections.
  - Other missing content.

### Features

- **Batch Processing**: Processes episodes in batches (configurable via command line).
- **Large File Handling**: Handles large audio files by processing initial segments.
- **Automatic Publishing**: Automatically publishes updates to Webflow.
- **Error Handling and Logging**: Includes robust error handling and logging.
- **Debug Output**: Creates debug output in the `debug/audio/` directory.

---

## Podcast Sync

`src/podcast_sync.py` is the main script for processing and publishing new podcast episodes. It:

- **Fetches the latest episode** from the RSS feed.
- **Creates episode content** for Webflow, including:
  - Episode title and description.
  - Platform links (Apple Podcasts, Spotify, Goodpods).
  - AI-generated transcript using OpenAI's Whisper API.
  - AI-generated Q&A section about the episode.
  - AI-classified episode category.
  - Custom episode thumbnail.

### Features

- **Automatic Platform Link Generation**:
  - Apple Podcasts.
  - Spotify.
  - Goodpods.
- **AI-Powered Content Generation**:
  - Episode transcription.
  - Q&A generation.
  - Category classification.
- **Custom Thumbnail Generation**.
- **Webflow Integration**:
  - Automatic publishing.
  - Asset management.
  - Category management.

### Usage

**Normal mode** - Fetch and publish the latest episode:

```bash
python src/podcast_sync.py
```

**Debug mode** - Prepare content without publishing:

```bash
python src/podcast_sync.py --debug
```

The script creates debug output in various subdirectories under `debug/`:

- `debug/audio/` - Episode audio and transcripts.
- `debug/images/thumbnails/` - Generated episode thumbnails.
- `debug/network/` - API request/response data.

---

## Scheduled Run

`src/scheduled_run.py` is an automated scheduler that monitors the podcast RSS feed for new episodes. It:

- Runs at configurable intervals to check for new episodes.
- Manages episode tracking to avoid duplicate processing.
- Automatically triggers the podcast sync process when new episodes are found.

### Features

- **Configurable Scheduling**:
  - Custom start time.
  - Adjustable check intervals.
  - Timezone support.
- **Episode Tracking**:
  - Maintains record of processed episodes in `episode_ids.jsonl`.
  - Prevents duplicate processing.
- **Automated Sync Triggering**:
  - Automatically runs `podcast_sync.py` when new episodes are found.
  - Handles errors and retries.
- **Detailed Logging**:
  - Logs all activities to `scheduled_log_runs.txt`.
  - Console output for monitoring.

### Configuration

In `config.yaml`:

```yaml
schedule:
  start_datetime: "2024-01-01 00:00:00"  # When to start checking
  interval_minutes: 60                   # How often to check
  timezone_offset: -5                    # GMT offset (e.g., -5 for EST)
```

Start the scheduler:

```bash
python src/scheduled_run.py
```

---

## Key Features

### RSS Feed Integration

- **Fetches episodes** from the Buzzsprout RSS feed.
- **Extracts episode details**:
  - Title.
  - Number.
  - Description.
  - Audio URL.
- **Cleans HTML** from descriptions.
- **Formats episode titles** consistently.

### Audio Processing

- **Downloads episode audio files**.
- **Transcribes audio** using OpenAI's Whisper API.
- **Formats transcripts** as conversations between configured hosts.
- **Generates HTML and Markdown** versions of transcripts.

### AI-Powered Features

- **Automatic episode categorization** using OpenAI.
- **Generates Q&A pairs** from episode content.
- **Formats Q&A content** for Webflow publishing.
- **Conversation-style transcript formatting** with host names.

### Image Generation

- **Creates episode thumbnails** with episode numbers.
- **Uploads thumbnails** to Webflow as assets.
- **Supports custom background images**.
- **Configurable text styling**.

### Platform Link Generation

- **Apple Podcasts**: Scrapes episode-specific links.
- **Spotify**: Uses the Spotify API to retrieve episode links.
- **Goodpods**: Generates links using episode number and title.

### Webflow Integration

- **Maps RSS feed data** to Webflow collection fields.
- **Validates fields** against collection schema.
- **Supports v2 Webflow API**.
- **Handles asset uploads and management**.
- **Debug mode** for testing without publishing.

---

## Configuration

Configuration is handled via `config.yaml` for:

- **Webflow API credentials and collection IDs**.
- **RSS feed URL**.
- **Platform-specific settings**:
  - Spotify API.
  - Base URLs.
- **OpenAI API configuration**.
- **Host names and display preferences**.
- **Default episode styling**.
- **Directory paths and file locations**.

---

## Debug Features

- **Detailed logging** to `debug_log.txt`.
- **Saves network requests and responses**.
- **Debug mode** for testing without API calls.
- **Stores intermediate files**:
  - Transcripts.
  - Q&A.
  - Thumbnails.
- **API response inspection tools**.

---

## Directory Structure

```
├── assets/                   # Static assets used by the application
│   ├── fonts/                # Font files
│   └── images/               # Image templates and backgrounds
│
├── debug/                    # Debug output and logs
│   ├── audio/                # Episode audio files and transcripts
│   ├── images/               # Generated images
│   │   └── thumbnails/       # Episode thumbnail images
│   ├── network/              # API request/response logs
│   └── *.json, *.txt, *.html # Various debug output files
│
├── src/                      # Source code
│   ├── ai/                   # AI/ML related code
│   ├── link_providers/       # Code for different podcast platforms
│   ├── media/                # Media processing (audio, images)
│   ├── utils/                # Utility functions
│   ├── webflow/              # Webflow API integration
│   └── *.py                  # Main application files
│
├── test/                     # Test files
│   └── *.py                  # Test scripts for different components
│
├── config.yaml               # Main configuration (git-ignored)
├── config.yaml.example       # Example configuration template
└── requirements.txt          # Python dependencies
```

---

## Requirements

- **Python 3.x**

- **Required Packages**:
  - `requests>=2.31.0`
  - `pyyaml>=6.0.1`
  - `Pillow>=10.2.0`
  - `markdown>=3.5.1`
  - `openai`
  - `feedparser`
  - `beautifulsoup4`

- **Valid API Credentials**:
  - Webflow API token.
  - OpenAI API key.
  - Spotify API credentials (optional).

---

## Usage

**Basic Usage**:

```bash
python src/podcast_sync.py
```

---

## Testing

Test scripts are available for:

- **Webflow API integration**.
- **Platform link generation** (Apple, Spotify, Goodpods).
- **RSS feed parsing**.

---