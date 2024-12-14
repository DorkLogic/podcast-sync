#!/usr/bin/env python3
import logging
import sys
import yaml
from pathlib import Path
from src.ai.create_excerpt import create_excerpt, ExcerptGenerationError

# Define directory paths
SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from config.yaml"""
    try:
        config_path = ROOT_DIR / 'config.yaml'
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        raise

def test_excerpt_generation():
    """Test generating excerpts with various inputs"""
    config = load_config()
    
    test_cases = [
        {
            "name": "Basic test",
            "tokens": ["AI", "machine learning", "future", "technology"],
            "length": 150,
            "should_succeed": True
        },
        {
            "name": "Short excerpt",
            "tokens": ["quick", "test"],
            "length": 50,
            "should_succeed": True
        },
        {
            "name": "Empty tokens",
            "tokens": [],
            "length": 100,
            "should_succeed": False
        },
        {
            "name": "Length too short",
            "tokens": ["test"],
            "length": 5,
            "should_succeed": False
        }
    ]
    
    for test_case in test_cases:
        logger.info(f"\nRunning test case: {test_case['name']}")
        try:
            excerpt = create_excerpt(
                tokens=test_case["tokens"],
                desired_length=test_case["length"],
                config=config
            )
            
            if not test_case["should_succeed"]:
                logger.error(f"Test case should have failed but succeeded: {test_case['name']}")
                continue
                
            logger.info(f"Generated excerpt ({len(excerpt)} chars):")
            logger.info(f"'{excerpt}'")
            
            # Verify all tokens are present (case-insensitive)
            excerpt_lower = excerpt.lower()
            missing_tokens = [
                token for token in test_case["tokens"]
                if token.lower() not in excerpt_lower
            ]
            
            if missing_tokens:
                logger.warning(f"Missing tokens in excerpt: {missing_tokens}")
            
            # Check length constraints
            length_diff = abs(len(excerpt) - test_case["length"])
            if length_diff > test_case["length"] * 0.2:
                logger.warning(
                    f"Excerpt length ({len(excerpt)}) differs from target "
                    f"({test_case['length']}) by more than 20%"
                )
                
        except ExcerptGenerationError as e:
            if test_case["should_succeed"]:
                logger.error(f"Test case should have succeeded but failed: {test_case['name']}")
                logger.error(f"Error: {e}")
            else:
                logger.info(f"Expected failure occurred: {e}")
                
        except Exception as e:
            logger.error(f"Unexpected error in test case {test_case['name']}: {e}")

def main():
    """Run all excerpt generation tests"""
    try:
        logger.info("Starting excerpt generation tests...")
        test_excerpt_generation()
        logger.info("\nExcerpt generation tests completed")
        
    except Exception as e:
        logger.error(f"Test script failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 