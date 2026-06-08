#!/usr/bin/env python3
"""Download and standardize datasets for neuro-symbolic FOL translation evaluation."""

import json
import sys
from pathlib import Path
from datasets import load_dataset
from loguru import logger

# Setup logging
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add("logs/dataset_download.log", rotation="30 MB", level="DEBUG")

OUTPUT_DIR = Path("temp/datasets")

def standardize_ruletaker(ds, split="train"):
    """Standardize RuleTaker dataset to unified schema."""
    standardized = []
    for i, example in enumerate(ds):
        standardized.append({
            "id": f"ruletaker_{split}_{i}",
            "context": example.get("context", ""),
            "query": example.get("question", ""),
            "answer": example.get("label", ""),
            "fol_gold": None,  # RuleTaker doesn't have FOL annotations
            "split": example.get("config", split),
            "source": "tasksource/ruletaker"
        })
    return standardized

def standardize_folio(ds, split="train"):
    """Standardize FOLIO dataset to unified schema."""
    standardized = []
    for i, example in enumerate(ds):
        standardized.append({
            "id": f"folio_{split}_{example.get('example_id', i)}",
            "context": example.get("premises", ""),
            "query": example.get("conclusion", ""),
            "answer": str(example.get("label", "")),
            "fol_gold": example.get("premises-FOL", "") + "\nConclusion: " + example.get("conclusion-FOL", ""),
            "split": split,
            "source": "tasksource/folio",
            "story_id": example.get("story_id", None)
        })
    return standardized

def standardize_proofwriter(ds, split="train"):
    """Standardize ProofWriter dataset to unified schema."""
    standardized = []
    for i, example in enumerate(ds):
        standardized.append({
            "id": f"proofwriter_{split}_{example.get('id', i)}",
            "context": example.get("theory", ""),
            "query": example.get("question", ""),
            "answer": str(example.get("answer", "")),
            "fol_gold": example.get("allProofs", None),
            "split": example.get("config", split),
            "source": "tasksource/proofwriter",
            "metadata": {
                "maxD": example.get("maxD", None),
                "NFact": example.get("NFact", None),
                "NRule": example.get("NRule", None),
                "QDep": example.get("QDep", None)
            }
        })
    return standardized

def standardize_entailment_bank(ds, split="train"):
    """Standardize Entailment Bank dataset to unified schema."""
    standardized = []
    for i, example in enumerate(ds):
        standardized.append({
            "id": f"entailment_bank_{split}_{example.get('id', i)}",
            "context": example.get("context", ""),
            "query": example.get("question", "") + " " + example.get("answer", ""),
            "answer": example.get("hypothesis", ""),
            "fol_gold": example.get("proof", None),
            "split": split,
            "source": "ariesutiono/entailment-bank-v3",
            "metadata": {
                "depth_of_proof": example.get("depth_of_proof", None),
                "length_of_proof": example.get("length_of_proof", None)
            }
        })
    return standardized

def standardize_logical_reasoning(ds, config="train_up_to_10_1m", split="train"):
    """Standardize LogicalReasoning dataset to unified schema."""
    standardized = []
    for i, example in enumerate(ds):
        standardized.append({
            "id": f"logical_reasoning_{config}_{i}",
            "context": "\n".join(example.get("premises_nl", [])),
            "query": example.get("question_nl", ""),
            "answer": str(example.get("answer", "")),
            "fol_gold": "\n".join(example.get("premises_fol", [])) + "\nQuery: " + example.get("question_fol", ""),
            "split": f"{config}_{split}",
            "source": "flaitenberger/LogicalReasoning-hard-v3",
            "metadata": {
                "constants": example.get("constants", []),
                "predicates": example.get("predicates", []),
                "depth": example.get("depth", None),
                "proof_nl": example.get("proof_nl", []),
                "proof_fol": example.get("proof_fol", [])
            }
        })
    return standardized

def standardize_clutrr(ds, split="train"):
    """Standardize CLUTRR dataset to unified schema."""
    standardized = []
    for i, example in enumerate(ds):
        standardized.append({
            "id": f"clutrr_{split}_{example.get('id', i)}",
            "context": example.get("story", ""),
            "query": f"What is the relation between {example.get('query', ['', ''])[0]} and {example.get('query', ['', ''])[1]}?",
            "answer": str(example.get("target_text", example.get("target", ""))),
            "fol_gold": None,  # CLUTRR doesn't have FOL annotations
            "split": example.get("task_split", split),
            "source": "kendrivp/CLUTRR_v1_extracted",
            "metadata": {
                "query_edge": example.get("query_edge", None),
                "edge_types": example.get("edge_types", []),
                "genders": example.get("genders", [])
            }
        })
    return standardized

@logger.catch(reraise=True)
def download_and_standardize():
    """Download and standardize all datasets."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    datasets_to_download = [
        {
            "name": "tasksource/ruletaker",
            "config": None,
            "split": "train",
            "standardize_fn": standardize_ruletaker,
            "output_name": "ruletaker"
        },
        {
            "name": "tasksource/folio",
            "config": None,
            "split": "train",
            "standardize_fn": standardize_folio,
            "output_name": "folio"
        },
        {
            "name": "tasksource/proofwriter",
            "config": None,
            "split": "train",
            "standardize_fn": standardize_proofwriter,
            "output_name": "proofwriter"
        },
        {
            "name": "ariesutiono/entailment-bank-v3",
            "config": None,
            "split": "train",
            "standardize_fn": standardize_entailment_bank,
            "output_name": "entailment_bank"
        },
        {
            "name": "flaitenberger/LogicalReasoning-hard-v3",
            "config": "train_up_to_10_1m",
            "split": "train",
            "standardize_fn": standardize_logical_reasoning,
            "output_name": "logical_reasoning"
        },
        {
            "name": "kendrivp/CLUTRR_v1_extracted",
            "config": None,
            "split": "train",
            "standardize_fn": standardize_clutrr,
            "output_name": "clutrr"
        }
    ]
    
    for dataset_info in datasets_to_download:
        try:
            logger.info(f"Downloading {dataset_info['name']}...")
            
            # Load dataset
            load_kwargs = {
                "path": dataset_info["name"],
                "split": dataset_info["split"]
            }
            if dataset_info["config"]:
                load_kwargs["name"] = dataset_info["config"]
            
            ds = load_dataset(**load_kwargs)
            
            # Standardize
            logger.info(f"Standardizing {dataset_info['name']}...")
            if dataset_info["name"] == "flaitenberger/LogicalReasoning-hard-v3":
                standardized = dataset_info["standardize_fn"](ds, config=dataset_info["config"])
            else:
                standardized = dataset_info["standardize_fn"](ds, split=dataset_info["split"])
            
            # Save full dataset
            output_path = OUTPUT_DIR / f"full_{dataset_info['output_name']}.json"
            with open(output_path, 'w') as f:
                json.dump(standardized, f, indent=2)
            logger.info(f"Saved {len(standardized)} examples to {output_path}")
            
            # Save mini dataset (first 3 examples)
            mini_path = OUTPUT_DIR / f"mini_{dataset_info['output_name']}.json"
            with open(mini_path, 'w') as f:
                json.dump(standardized[:3], f, indent=2)
            logger.info(f"Saved mini dataset to {mini_path}")
            
            # Save preview dataset (first 3 examples, truncated)
            preview = []
            for ex in standardized[:3]:
                preview_ex = {}
                for k, v in ex.items():
                    if isinstance(v, str) and len(v) > 200:
                        preview_ex[k] = v[:200] + "..."
                    else:
                        preview_ex[k] = v
                preview.append(preview_ex)
            
            preview_path = OUTPUT_DIR / f"preview_{dataset_info['output_name']}.json"
            with open(preview_path, 'w') as f:
                json.dump(preview, f, indent=2)
            logger.info(f"Saved preview dataset to {preview_path}")
            
        except Exception as e:
            logger.error(f"Failed to download/process {dataset_info['name']}: {e}")
            continue
    
    logger.info("All datasets downloaded and standardized!")

if __name__ == "__main__":
    download_and_standardize()
