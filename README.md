# PODCAST SYNC AUTOMATION

## Overview
`podcast_sync.py` automates the process of syncing podcast episodes from an RSS feed to a Webflow CMS collection, including transcription, Q&A generation, and thumbnail creation.

## Key Features

### RSS Feed Integration
- Fetches episodes from the Buzzsprout RSS feed
- Extracts episode details: title, number, description, and audio URL
- Cleans HTML from descriptions
- Formats episode titles consistently

### Audio Processing
- Downloads episode audio files
- Transcribes audio using OpenAI Whisper API
- Formats transcripts as conversation between configured hosts
- Generates HTML and Markdown versions of transcripts

### AI-Powered Features
- Automatic episode categorization using OpenAI
- Generates Q&A pairs from episode content
- Formats Q&A content for Webflow publishing
- Conversation-style transcript formatting with host names

### Image Generation
- Creates episode thumbnails with episode numbers
- Uploads thumbnails to Webflow as assets
- Supports custom background images
- Configurable text styling

### Platform Link Generation
- Apple Podcasts: Scrapes episode-specific links
- Spotify: Uses the Spotify API to retrieve episode links
- Goodpods: Generates links using episode number and title

### Webflow Integration
- Maps RSS feed data to Webflow collection fields
- Validates fields against collection schema
- Supports v2 Webflow API
- Handles asset uploads and management
- Debug mode for testing without publishing

## Configuration
Uses `config.yaml` for:
- Webflow API credentials and collection IDs
- RSS feed URL
- Platform-specific settings (Spotify API, base URLs)
- OpenAI API configuration
- Host names and display preferences
- Default episode styling
- Directory paths and file locations

## Debug Features
- Detailed logging to `debug_log.txt`
- Saves network requests and responses
- Debug mode for testing without API calls
- Stores intermediate files (transcripts, Q&A, thumbnails)
- API response inspection tools

## Directory Structure
├── debug/
│ ├── audio/ # Episode audio files
│ ├── images/ # Image assets
│ │ └── thumbnails/
│ └── network/ # API request/response logs
├── src/
│ ├── ai/ # AI classification
│ ├── media/ # Audio and image processing
│ ├── webflow/ # Webflow API integration
│ └── utils/ # Helper functions
└── test/ # Test scripts


## Requirements
- Python 3.x
- Required packages:
  - `requests>=2.31.0`
  - `pyyaml>=6.0.1`
  - `Pillow>=10.2.0`
  - `markdown>=3.5.1`
  - `openai`
  - `feedparser`
  - `beautifulsoup4`
- Valid API credentials:
  - Webflow API token
  - OpenAI API key
  - Spotify API credentials (optional)

## Usage
Basic usage:
python src/podcast_sync.py


## Testing
Test scripts available for:
- Webflow API integration
- Platform link generation (Apple, Spotify, Goodpods)
- RSS feed parsing