#!/usr/bin/env python3
"""Download remaining datasets with size limits."""

import json
import sys
from pathlib import Path
from datasets import load_dataset
from loguru import logger

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")

OUTPUT_DIR = Path("temp/datasets")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

@logger.catch(reraise=True)
def download_dataset(dataset_name, output_name, split="train", config=None, max_examples=10000):
    """Download dataset with size limit."""
    try:
        logger.info(f"Downloading {dataset_name} (max {max_examples} examples)...")
        
        load_kwargs = {"path": dataset_name, "split": split, "streaming": True}
        if config:
            load_kwargs["name"] = config
        
        ds = load_dataset(**load_kwargs)
        
        # Collect examples with limit
        examples = []
        for i, example in enumerate(ds):
            if i >= max_examples:
                logger.info(f"Reached limit of {max_examples} examples")
                break
            examples.append(example)
        
        logger.info(f"Downloaded {len(examples)} examples")
        
        # Save
        output_path = OUTPUT_DIR / f"full_{output_name}.json"
        with open(output_path, 'w') as f:
            json.dump(examples, f, indent=2)
        
        file_size = output_path.stat().st_size / (1024 * 1024)  # MB
        logger.info(f"Saved to {output_path} ({file_size:.1f} MB)")
        
        # Create mini and preview
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
            
            logger.info(f"Saved mini and preview datasets")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to download {dataset_name}: {e}")
        return False

if __name__ == "__main__":
    # Download CLUTRR (smaller subset)
    download_dataset(
        "kendrivp/CLUTRR_v1_extracted",
        "clutrr",
        split="train",
        max_examples=5000
    )
    
    # Download LogicalReasoning (smaller config)
    download_dataset(
        "flaitenberger/LogicalReasoning-hard-v3",
        "logical_reasoning",
        split="train",
        config="train_up_to_5_1m",
        max_examples=5000
    )
    
    logger.info("Download complete!")
