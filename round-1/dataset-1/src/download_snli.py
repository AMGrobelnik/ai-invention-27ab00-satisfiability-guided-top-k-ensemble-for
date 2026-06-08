#!/usr/bin/env python3
"""Download SNLI as 6th dataset."""

import json
from pathlib import Path
from datasets import load_dataset
from loguru import logger

logger.remove()
logger.add("logs/snli_download.log", rotation="30 MB", level="DEBUG")
logger.add(lambda msg: print(msg, end=""), level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")

OUTPUT_DIR = Path("temp/datasets")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

@logger.catch(reraise=True)
def download_snli():
    """Download SNLI dataset."""
    try:
        logger.info("Downloading stanfordnlp/snli...")
        ds = load_dataset("stanfordnlp/snli", split="train", streaming=True)
        
        examples = []
        current_size_mb = 0
        max_mb = 100
        max_examples = 10000
        
        for i, example in enumerate(ds):
            if i >= max_examples:
                logger.info(f"Hit example limit: {max_examples}")
                break
            
            example_json = json.dumps(example)
            example_size_mb = len(example_json.encode('utf-8')) / (1024 * 1024)
            
            if current_size_mb + example_size_mb > max_mb:
                logger.info(f"Hit size limit: {current_size_mb:.1f}MB")
                break
            
            examples.append(example)
            current_size_mb += example_size_mb
            
            if (i + 1) % 1000 == 0:
                logger.info(f"Processed {i+1} examples ({current_size_mb:.1f}MB)")
        
        logger.info(f"Collected {len(examples)} examples ({current_size_mb:.1f}MB)")
        
        # Save
        output_path = OUTPUT_DIR / "full_snli.json"
        with open(output_path, 'w') as f:
            json.dump(examples, f, indent=2)
        
        actual_size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"Saved to {output_path} (actual: {actual_size_mb:.1f}MB)")
        
        # Create mini and preview
        if len(examples) >= 3:
            mini = examples[:3]
            mini_path = OUTPUT_DIR / "mini_snli.json"
            with open(mini_path, 'w') as f:
                json.dump(mini, f, indent=2)
            
            # Preview (truncated)
            preview = []
            for ex in mini:
                preview_ex = {}
                for k, v in ex.items():
                    if isinstance(v, str) and len(v) > 200:
                        preview_ex[k] = v[:200] + "..."
                    else:
                        preview_ex[k] = v
                preview.append(preview_ex)
            
            preview_path = OUTPUT_DIR / "preview_snli.json"
            with open(preview_path, 'w') as f:
                json.dump(preview, f, indent=2)
            
            logger.info("Saved mini and preview datasets for SNLI")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to download SNLI: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting SNLI download...")
    success = download_snli()
    if success:
        logger.info("SNLI download complete!")
    else:
        logger.error("SNLI download failed!")
