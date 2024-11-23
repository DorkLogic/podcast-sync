import os
import sys
import yaml
import logging
import requests
from typing import Dict, Optional
from dataclasses import dataclass

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@dataclass
class TextStyle:
    """Data class to hold text styling properties"""
    font_family: str
    font_size: int
    color: str
    position: Dict[str, int]
    
class CanvaTextManager:
    """Class for managing text elements in Canva designs"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the Canva text manager with configuration"""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        self.base_url = config['canva']['base_url']
        self.client_id = config['canva']['client_id']
        self.client_secret = config['canva']['client_secret']
        self.api_key = config['canva']['api_key']
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def add_text_to_design(
        self,
        design_id: str,
        text_content: str,
        style: TextStyle
    ) -> Dict:
        """
        Add rich text to an existing Canva design
        
        Args:
            design_id: The ID of the Canva design
            text_content: The text to add
            style: TextStyle object containing styling properties
            
        Returns:
            Dict containing the API response
        """
        endpoint = f"{self.base_url}/designs/{design_id}/elements"
        
        # Construct the text element payload
        payload = {
            "type": "text",
            "content": text_content,
            "position": {
                "x": style.position["x"],
                "y": style.position["y"]
            },
            "style": {
                "fontFamily": style.font_family,
                "fontSize": style.font_size,
                "color": style.color
            }
        }
        
        try:
            response = requests.post(
                endpoint,
                headers=self._get_headers(),
                json=payload
            )
            response.raise_for_status()
            
            logging.info(f"Successfully added text to design {design_id}")
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to add text to design: {str(e)}")
            if hasattr(e.response, 'json'):
                logging.error(f"API Error: {e.response.json()}")
            raise
    
    def update_text_element(
        self,
        design_id: str,
        element_id: str,
        text_content: Optional[str] = None,
        style: Optional[TextStyle] = None
    ) -> Dict:
        """
        Update an existing text element in a Canva design
        
        Args:
            design_id: The ID of the Canva design
            element_id: The ID of the text element to update
            text_content: New text content (optional)
            style: New TextStyle object (optional)
            
        Returns:
            Dict containing the API response
        """
        endpoint = f"{self.base_url}/designs/{design_id}/elements/{element_id}"
        
        payload = {}
        if text_content:
            payload["content"] = text_content
            
        if style:
            payload["style"] = {
                "fontFamily": style.font_family,
                "fontSize": style.font_size,
                "color": style.color
            }
            payload["position"] = style.position
            
        try:
            response = requests.patch(
                endpoint,
                headers=self._get_headers(),
                json=payload
            )
            response.raise_for_status()
            
            logging.info(f"Successfully updated text element {element_id}")
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to update text element: {str(e)}")
            if hasattr(e.response, 'json'):
                logging.error(f"API Error: {e.response.json()}")
            raise

def main():
    """Example usage of the CanvaTextManager"""
    try:
        # Initialize the text manager
        text_manager = CanvaTextManager()
        
        # Example text style
        style = TextStyle(
            font_family="Arial",
            font_size=24,
            color="#000000",
            position={"x": 100, "y": 100}
        )
        
        # Example usage: Add text to design
        design_id = "your_design_id"
        result = text_manager.add_text_to_design(
            design_id=design_id,
            text_content="Hello, Canva!",
            style=style
        )
        
        # Print the element ID for future reference
        element_id = result.get("id")
        logging.info(f"Created text element with ID: {element_id}")
        
        # Example: Update the text element
        updated_style = TextStyle(
            font_family="Helvetica",
            font_size=32,
            color="#FF5733",
            position={"x": 150, "y": 150}
        )
        
        text_manager.update_text_element(
            design_id=design_id,
            element_id=element_id,
            text_content="Updated text!",
            style=updated_style
        )
        
    except Exception as e:
        logging.error(f"Error in main execution: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 