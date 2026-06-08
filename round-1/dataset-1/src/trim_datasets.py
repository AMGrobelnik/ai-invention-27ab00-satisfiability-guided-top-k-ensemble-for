#!/usr/bin/env python3
"""Trim large datasets to under 300MB and find 6th dataset."""

import json
import sys
from pathlib import Path
from datasets import load_dataset
from loguru import logger

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")

OUTPUT_DIR = Path("temp/datasets")

@logger.catch(reraise=True)
def trim_dataset(input_path, output_path, max_size_mb=300):
    """Trim dataset to under max_size_mb."""
    logger.info(f"Trimming {input_path} to under {max_size_mb}MB...")
    
    with open(input_path, 'r') as f:
        data = json.load(f)
    
    logger.info(f"Original size: {input_path.stat().st_size / (1024*1024):.1f} MB, {len(data)} examples")
    
    # Binary search for right number of examples
    # Start by estimating average example size
    sample_size = len(json.dumps(data[0]).encode('utf-8'))
    avg_size_mb = sample_size / (1024 * 1024)
    estimated_count = int(max_size_mb / avg_size_mb)
    
    logger.info(f"Estimated {estimated_count} examples for {max_size_mb}MB")
    
    # Trim to estimated count and check actual size
    trimmed = data[:estimated_count]
    temp_path = output_path.with_suffix('.temp.json')
    
    with open(temp_path, 'w') as f:
        json.dump(trimmed, f, indent=2)
    
    actual_size_mb = temp_path.stat().st_size / (1024 * 1024)
    logger.info(f"After trimming to {len(trimmed)} examples: {actual_size_mb:.1f} MB")
    
    # Adjust if needed
    if actual_size_mb > max_size_mb:
        # Need to reduce
        while actual_size_mb > max_size_mb and len(trimmed) > 0:
            trimmed = trimmed[:-100]  # Remove 100 at a time
            with open(temp_path, 'w') as f:
                json.dump(trimmed, f, indent=2)
            actual_size_mb = temp_path.stat().st_size / (1024 * 1024)
        logger.info(f"Reduced to {len(trimmed)} examples: {actual_size_mb:.1f} MB")
    elif actual_size_mb < max_size_mb * 0.8:
        # Can add more
        while actual_size_mb < max_size_mb * 0.9 and len(trimmed) < len(data):
            add_count = min(100, len(data) - len(trimmed))
            trimmed.extend(data[len(trimmed):len(trimmed)+add_count])
            with open(temp_path, 'w') as f:
                json.dump(trimmed, f, indent=2)
            actual_size_mb = temp_path.stat().st_size / (1024 * 1024)
        logger.info(f"Expanded to {len(trimmed)} examples: {actual_size_mb:.1f} MB")
    
    # Rename temp to final
    temp_path.rename(output_path)
    logger.info(f"Saved trimmed dataset to {output_path}")
    
    return len(trimmed)

@logger.catch(reraise=True)
def download_snli_max_examples():
    """Download SNLI dataset as 6th dataset (alternative to Entailment Bank)."""
    try:
        logger.info("Downloading SNLI dataset (alternative to Entailment Bank)...")
        ds = load_dataset("snli", split="train", streaming=True)
        
        examples = []
        for i, example in enumerate(ds):
            if i >= 10000:  # Limit to 10k examples
                break
            examples.append({
                "id": f"snli_{i}",
                "context": example.get("premise", ""),
                "query": example.get("hypothesis", ""),
                "answer": str(example.get("label", "")),
                "fol_gold": None,
                "split": "train",
                "source": "snli"
            })
        
        output_path = OUTPUT_DIR / "full_snli.json"
        with open(output_path, 'w') as f:
            json.dump(examples, f, indent=2)
        
        file_size = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"Saved {len(examples)} examples to {output_path} ({file_size:.1f} MB)")
        
        # Create mini and preview
        if len(examples) >= 3:
            mini = examples[:3]
            with open(OUTPUT_DIR / "mini_snli.json", 'w') as f:
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
            
            with open(OUTPUT_DIR / "preview_snli.json", 'w') as f:
                json.dump(preview, f, indent=2)
            
            logger.info("Saved mini and preview datasets for SNLI")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to download SNLI: {e}")
        return False

if __name__ == "__main__":
    # Trim large datasets
    trim_dataset(
        OUTPUT_DIR / "full_proofwriter.json",
        OUTPUT_DIR / "full_proofwriter.json",
        max_size_mb=300
    )
    
    trim_dataset(
        OUTPUT_DIR / "full_ruletaker.json",
        OUTPUT_DIR / "full_ruletaker.json",
        max_size_mb=300
    )
    
    # Download 6th dataset
    download_snli_max_examples()
    
    logger.info("All datasets processed!")
