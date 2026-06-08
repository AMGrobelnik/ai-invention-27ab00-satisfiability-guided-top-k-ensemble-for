#!/usr/bin/env python3
"""Download smaller subsets of large datasets."""

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
def download_subset(dataset_name, output_name, split="train", config=None, max_examples=5000):
    """Download a subset of dataset."""
    try:
        logger.info(f"Downloading {dataset_name} (max {max_examples} examples)...")
        
        load_kwargs = {"path": dataset_name, "split": split, "streaming": True}
        if config:
            load_kwargs["name"] = config
        
        ds = load_dataset(**load_kwargs)
        
        examples = []
        for i, example in enumerate(ds):
            if i >= max_examples:
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
    # Download smaller RuleTaker subset
    download_subset(
        "tasksource/ruletaker",
        "ruletaker",
        split="train",
        max_examples=50000  # Should be under 300MB
    )
    
    # Download smaller ProofWriter subset  
    download_subset(
        "tasksource/proofwriter",
        "proofwriter",
        split="train",
        max_examples=50000  # Should be under 300MB
    )
    
    # Download SNLI as 6th dataset
    try:
        logger.info("Downloading SNLI dataset...")
        ds = load_dataset("snli", split="train", streaming=True)
        
        examples = []
        for i, example in enumerate(ds):
            if i >= 10000:
                break
            examples.append({
                "premise": example.get("premise", ""),
                "hypothesis": example.get("hypothesis", ""),
                "label": example.get("label", "")
            })
        
        logger.info(f"Downloaded {len(examples)} SNLI examples")
        
        # Save
        output_path = OUTPUT_DIR / "full_snli.json"
        with open(output_path, 'w') as f:
            json.dump(examples, f, indent=2)
        
        file_size = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"Saved to {output_path} ({file_size:.1f} MB)")
        
        # Create mini and preview
        if len(examples) >= 3:
            mini = examples[:3]
            mini_path = OUTPUT_DIR / "mini_snli.json"
            with open(mini_path, 'w') as f:
                json.dump(mini, f, indent=2)
            
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
        
    except Exception as e:
        logger.error(f"Failed to download SNLI: {e}")
    
    logger.info("All subsets downloaded!")
