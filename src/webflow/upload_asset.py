import hashlib
import logging
import requests
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class AssetUploadError(Exception):
    """Custom exception for asset upload errors"""
    pass

def get_existing_asset(filename: str, config: dict) -> Optional[Dict]:
    """
    Check if an asset with the given filename already exists
    
    Args:
        filename: Name of the file to look for
        config: Application configuration containing Webflow settings
        
    Returns:
        Dict containing asset info if found, None otherwise
    """
    try:
        url = f'https://api.webflow.com/v2/sites/{config["webflow"]["site_id"]}/assets'
        
        headers = {
            'accept': 'application/json',
            'authorization': f'Bearer {config["webflow"]["api_token"]}'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        assets = response.json().get('assets', [])
        
        # Look for asset with matching filename
        for asset in assets:
            if asset.get('originalFileName') == filename:
                logger.info(f"Found existing asset: {asset.get('id')}")
                return {
                    "fileId": asset.get('id'),
                    "url": asset.get('hostedUrl'),
                    "alt": None  # Alt text will be updated by caller
                }
                
        return None
        
    except Exception as e:
        logger.error(f"Failed to check for existing asset: {e}")
        if 'response' in locals():
            logger.error(f"Response: {response.text}")
        return None

def calculate_md5(file_path: Path) -> str:
    """Calculate MD5 hash of file"""
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        # Read file in chunks to handle large files
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

def upload_asset(file_path: Path, config: dict, alt_text: Optional[str] = None) -> Dict:
    """
    Upload a file as an asset to Webflow if it doesn't already exist
    
    Args:
        file_path: Path to the file to upload
        config: Application configuration containing Webflow settings
        alt_text: Optional alt text for the image
        
    Returns:
        Dict containing fileId, url, and alt text for the asset
    """
    try:
        # First check if asset already exists
        existing_asset = get_existing_asset(file_path.name, config)
        if existing_asset:
            logger.info(f"Asset already exists: {file_path.name}")
            existing_asset['alt'] = alt_text  # Update alt text
            return existing_asset
            
        # If asset doesn't exist, proceed with upload
        logger.info(f"Asset not found, proceeding with upload: {file_path.name}")
        
        # Step 1: Create asset metadata
        metadata_url = f'https://api.webflow.com/v2/sites/{config["webflow"]["site_id"]}/assets'
        
        headers = {
            'accept': 'application/json',
            'authorization': f'Bearer {config["webflow"]["api_token"]}',
            'content-type': 'application/json'
        }
        
        # Calculate file hash
        file_hash = calculate_md5(file_path)
        
        # Prepare metadata request
        metadata = {
            "fileName": file_path.name,
            "fileHash": file_hash
        }
        
        logger.info(f"Creating asset metadata for {file_path.name}")
        metadata_response = requests.post(metadata_url, headers=headers, json=metadata)
        metadata_response.raise_for_status()
        
        upload_data = metadata_response.json()
        logger.debug(f"Metadata response: {upload_data}")
        
        # Step 2: Upload file to S3
        upload_url = upload_data['uploadUrl']
        upload_details = upload_data['uploadDetails']
        
        # Prepare file upload
        files = {k: (None, v) for k, v in upload_details.items()}
        files['file'] = (file_path.name, open(file_path, 'rb'), 'image/png')
        
        logger.info(f"Uploading file to {upload_url}")
        upload_response = requests.post(upload_url, files=files)
        upload_response.raise_for_status()
        
        # Return asset information
        return {
            "fileId": upload_data['id'],
            "url": upload_data['hostedUrl'],
            "alt": alt_text
        }
        
    except Exception as e:
        logger.error(f"Failed to upload asset: {e}")
        if 'metadata_response' in locals():
            logger.error(f"Metadata Response: {metadata_response.text}")
        if 'upload_response' in locals():
            logger.error(f"Upload Response: {upload_response.text}")
        raise AssetUploadError(f"Failed to upload asset: {str(e)}") 