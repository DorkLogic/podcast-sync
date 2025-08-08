# Image Optimizer

A tool for optimizing images in a directory and its subdirectories without destroying the originals.

## Features

- Resizes images while maintaining aspect ratio
- Converts to web-friendly formats (WEBP, JPEG, PNG)
- Optimizes quality and compression
- Creates backups of original files
- Processes directories recursively
- Provides detailed statistics on optimization results
- Supports dry-run mode to preview changes

## Requirements

- Python 3.6+
- Pillow (PIL Fork) library

## Installation

```bash
pip install Pillow
```

## Usage

### Basic Usage

To optimize all images in a directory:

```bash
python image_optimizer.py /path/to/images
```

This will:
1. Find all images in the directory and its subdirectories
2. Create backups of original files (with `_original` suffix)
3. Create optimized versions (with `_optimized` suffix)
4. Print statistics on the optimization results

### Advanced Options

```bash
# Specify output directory
python image_optimizer.py /path/to/images -o /path/to/output

# Set maximum dimensions
python image_optimizer.py /path/to/images --max-width 800 --max-height 600

# Set quality (1-100)
python image_optimizer.py /path/to/images --quality 90

# Choose output format (WEBP, JPEG, PNG)
python image_optimizer.py /path/to/images --format JPEG

# Custom suffix for optimized files
python image_optimizer.py /path/to/images --suffix _web

# Do not process subdirectories
python image_optimizer.py /path/to/images --no-recursive

# Do not create backups
python image_optimizer.py /path/to/images --no-backup

# Preview changes without making them
python image_optimizer.py /path/to/images --dry-run

# Enable verbose output
python image_optimizer.py /path/to/images --verbose
```

## How It Works

The image optimizer:

1. **Finds Images**: Scans directories for common image formats (.png, .jpg, .jpeg, .gif, .webp, .bmp, .tiff)
2. **Creates Backups**: Makes copies of original files with `_original` suffix
3. **Optimizes Images**:
   - Resizes if larger than specified dimensions
   - Converts to RGB/RGBA mode if needed
   - Optimizes quality and compression
   - Saves in the specified format
4. **Tracks Statistics**: Counts processed, skipped, and failed images
5. **Reports Results**: Shows size reduction and other metrics

## Safety Features

- **Backups**: Original files are preserved with `_original` suffix
- **Skip Existing**: Files that are already optimized and up-to-date are skipped
- **Error Handling**: Corrupted or invalid images are skipped with error messages
- **Dry Run**: Preview changes without making them

## Example Output

```
2023-06-15 10:30:45,123 - INFO - Found 25 images to process
2023-06-15 10:30:45,234 - INFO - Resizing image from (2400, 1600) to (1200, 800)
2023-06-15 10:30:45,345 - INFO - Image optimized: example.jpg
2023-06-15 10:30:45,456 - INFO - Original size: 2048.0KB
2023-06-15 10:30:45,567 - INFO - Optimized size: 512.0KB
2023-06-15 10:30:45,678 - INFO - Size reduction: 75.0%
...
2023-06-15 10:31:15,789 - INFO - Processed 25 images in 30.67 seconds
2023-06-15 10:31:15,890 - INFO - Summary:
2023-06-15 10:31:15,901 - INFO -   Processed: 25 images
2023-06-15 10:31:15,912 - INFO -   Skipped: 0 images
2023-06-15 10:31:15,923 - INFO -   Failed: 0 images
2023-06-15 10:31:15,934 - INFO -   Total size before: 50.25MB
2023-06-15 10:31:15,945 - INFO -   Total size after: 12.50MB
2023-06-15 10:31:15,956 - INFO -   Total reduction: 75.1%
``` 