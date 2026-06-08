#!/usr/bin/env python3
"""Download datasets with strict size limits - sequential processing."""

import json
from pathlib import Path
from datasets import load_dataset
from loguru import logger

logger.remove()
logger.add("logs/download.log", rotation="30 MB", level="DEBUG")
logger.add(lambda msg: print(msg, end=""), level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")

OUTPUT_DIR = Path("temp/datasets")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def download_limited(dataset_name, output_name, split="train", config=None, max_mb=300, max_examples=100000):
    """Download dataset with strict size limit using streaming."""
    try:
        logger.info(f"Downloading {dataset_name} (limit: {max_mb}MB)...")
        
        # Load in streaming mode
        load_kwargs = {"path": dataset_name, "split": split, "streaming": True}
        if config:
            load_kwargs["name"] = config
        
        ds = load_dataset(**load_kwargs)
        
        examples = []
        current_size_mb = 0
        
        for i, example in enumerate(ds):
            if i >= max_examples:
                logger.info(f"Hit example limit: {max_examples}")
                break
            
            # Check size before adding
            example_json = json.dumps(example)
            example_size_mb = len(example_json.encode('utf-8')) / (1024 * 1024)
            
            if current_size_mb + example_size_mb > max_mb:
                logger.info(f"Hit size limit: {current_size_mb:.1f}MB")
                break
            
            examples.append(example)
            current_size_mb += example_size_mb
            
            if (i + 1) % 10000 == 0:
                logger.info(f"Processed {i+1} examples ({current_size_mb:.1f}MB)")
        
        logger.info(f"Collected {len(examples)} examples ({current_size_mb:.1f}MB)")
        
        # Save
        output_path = OUTPUT_DIR / f"full_{output_name}.json"
        with open(output_path, 'w') as f:
            json.dump(examples, f, indent=2)
        
        actual_size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"Saved to {output_path} (actual: {actual_size_mb:.1f}MB)")
        
        # Create mini (3 examples)
        if len(examples) >= 3:
            mini = examples[:3]
            mini_path = OUTPUT_DIR / f"mini_{output_name}.json"
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
            
            preview_path = OUTPUT_DIR / f"preview_{output_name}.json"
            with open(preview_path, 'w') as f:
                json.dump(preview, f, indent=2)
            
            logger.info(f"Saved mini and preview")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed {dataset_name}: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting sequential dataset downloads...")
    
    # 1. Download RuleTaker (limit to ~100MB to leave room)
    download_limited("tasksource/ruletaker", "ruletaker", split="train", max_mb=100, max_examples=50000)
    
    logger.info("RuleTaker done. Moving to ProofWriter...")
    
    # 2. Download ProofWriter (limit to ~100MB)
    download_limited("tasksource/proofwriter", "proofwriter", split="train", max_mb=100, max_examples=50000)
    
    logger.info("ProofWriter done. Moving to SNLI...")
    
    # 3. Download SNLI as 6th dataset
    try:
        logger.info("Downloading SNLI...")
        ds = load_dataset("snli", split="train", streaming=True)
        
        examples = []
        current_size_mb = 0
        max_mb = 100
        
        for i, example in enumerate(ds):
            if i >= 10000:
                break
            
            example_json = json.dumps(example)
            example_size_mb = len(example_json.encode('utf-8')) / (1024 * 1024)
            
            if current_size_mb + example_size_mb > max_mb:
                break
            
            examples.append(example)
            current_size_mb += example_size_mb
        
        logger.info(f"Collected {len(examples)} SNLI examples ({current_size_mb:.1f}MB)")
        
        output_path = OUTPUT_DIR / "full_snli.json"
        with open(output_path, 'w') as f:
            json.dump(examples, f, indent=2)
        
        actual_size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"Saved SNLI to {output_path} ({actual_size_mb:.1f}MB)")
        
    except Exception as e:
        logger.error(f"Failed SNLI: {e}")
    
    logger.info("All downloads complete!")
