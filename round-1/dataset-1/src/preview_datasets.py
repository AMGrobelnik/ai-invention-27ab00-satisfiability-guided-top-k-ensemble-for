#!/usr/bin/env python3
"""Preview HuggingFace datasets for neuro-symbolic FOL translation evaluation."""

import sys
from pathlib import Path
from datasets import load_dataset, get_dataset_config_names
from huggingface_hub import DatasetCard, HfApi

def truncate(text, max_len=500):
    """Truncate text with indicator."""
    if not text:
        return ""
    text = str(text)
    return text[:max_len] + f"... (+{len(text) - max_len} chars)" if len(text) > max_len else text

def truncate_value(value, max_array=3, max_str=200):
    """Truncate values for display."""
    if value is None:
        return None
    if isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:max_str] + "..." if len(value) > max_str else value
    if isinstance(value, bytes):
        return f"<bytes: {len(value)} bytes>"
    if isinstance(value, list):
        return [truncate_value(v) for v in value[:max_array]]
    if isinstance(value, dict):
        return {str(k): truncate_value(v) for k, v in list(value.items())[:max_array]}
    type_name = type(value).__name__
    if hasattr(value, "shape"):
        return f"<{type_name}: shape={value.shape}>"
    if hasattr(value, "size") and hasattr(value, "mode"):
        return f"<{type_name}: size={value.size}, mode={value.mode}>"
    try:
        s = str(value)
        return s[:max_str] + "..." if len(s) > max_str else s
    except Exception:
        return f"<{type_name}>"

def preview_dataset(dataset_id: str, config: str = None, split: str = "train", num_rows: int = 5):
    """Preview a HuggingFace dataset."""
    print(f"\n{'=' * 60}")
    print(f"Dataset: {dataset_id}")
    print(f"{'=' * 60}")
    
    api = HfApi()
    
    # Get dataset info
    try:
        info = api.dataset_info(dataset_id)
        print(f"Downloads: {info.downloads:,} | Likes: {info.likes}")
        if hasattr(info, 'created_at') and info.created_at:
            print(f"Created: {str(info.created_at)[:10]}")
    except Exception as e:
        print(f"Warning: Could not fetch dataset info: {e}")
    
    # Get dataset card
    try:
        card = DatasetCard.load(dataset_id)
        if card and card.text:
            desc = truncate(card.text, 500)
            print(f"\nDescription: {desc}")
    except Exception:
        pass
    
    # Get configs
    try:
        config_names = get_dataset_config_names(dataset_id)
        if config_names:
            print(f"\nConfigs: {', '.join(config_names[:10])}")
            if not config:
                config = config_names[0]
    except Exception:
        config_names = []
    
    print(f"\n--- Sample Rows ({split}) ---")
    
    # Load dataset
    try:
        load_kwargs = {"path": dataset_id, "split": split, "streaming": True}
        if config:
            load_kwargs["name"] = config
        
        ds = load_dataset(**load_kwargs)
        rows = []
        columns = []
        
        for i, row in enumerate(ds):
            if i >= num_rows:
                break
            rows.append(dict(row))
            if i == 0:
                columns = list(row.keys())
        
        if columns:
            print(f"Columns: {', '.join(columns[:15])}")
        
        for i, row in enumerate(rows, 1):
            print(f"\nRow {i}:")
            for k, v in row.items():
                v_str = str(truncate_value(v))
                print(f"  {k}: {v_str}")
        
        print(f"\nSuccessfully loaded {len(rows)} rows")
        return True
        
    except Exception as e:
        print(f"Error loading dataset: {e}")
        return False

if __name__ == "__main__":
    datasets_to_preview = [
        "yale-nlp/FOLIO",
        "CLUTRR/v1",
        "tasksource/ruletaker",
        "tasksource/folio",
        "flaitenberger/LogicalReasoning-hard-v3",
    ]
    
    for dataset_id in datasets_to_preview:
        try:
            preview_dataset(dataset_id, num_rows=3)
        except Exception as e:
            print(f"\nFailed to preview {dataset_id}: {e}")
