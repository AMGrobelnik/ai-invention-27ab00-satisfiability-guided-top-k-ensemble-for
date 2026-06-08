#!/usr/bin/env python3
"""Load and standardize datasets to exp_sel_data_out.json schema.

Selected datasets for neuro-symbolic FOL translation evaluation:
1. RuleTaker - near-propositional fragment, rule-based reasoning
2. FOLIO - has FOL gold annotations for translation quality
3. CLUTRR - multi-hop reasoning, kinship relations
"""

import json
from pathlib import Path
from loguru import logger

logger.remove()
logger.add("logs/data.log", rotation="30 MB", level="DEBUG")
logger.add(lambda msg: print(msg, end=""), level="INFO")

OUTPUT_FILE = Path("full_data_out.json")

@logger.catch(reraise=True)
def main():
    """Load selected datasets and standardize to exp_sel_data_out schema."""
    datasets = []

    # 1. RuleTaker - near-propositional fragment, rule-based reasoning
    try:
        with open("temp/datasets/full_ruletaker.json") as f:
            data = json.load(f)
        examples = []
        for i, ex in enumerate(data):
            answer = str(ex.get('label', ex.get('answer', '')))
            examples.append({
                "input": f"Context: {ex.get('context', '')}\nQuestion: {ex.get('query', '')}",
                "output": answer,
                "metadata_config": ex.get('config', 'train'),
                "metadata_example_id": i
            })
        datasets.append({"dataset": "ruletaker", "examples": examples})
        logger.info(f"RuleTaker: {len(examples)} examples")
    except Exception as e:
        logger.error(f"RuleTaker failed: {e}")

    # 2. FOLIO - has FOL gold annotations for translation quality
    try:
        with open("temp/datasets/full_folio.json") as f:
            data = json.load(f)
        examples = []
        for i, ex in enumerate(data):
            answer = str(ex.get('answer', ''))
            examples.append({
                "input": f"Premises:\n{ex.get('context', '')}\nConclusion: {ex.get('query', '')}",
                "output": answer,
                "metadata_fol_gold": ex.get('fol_gold', ''),
                "metadata_split": ex.get('split', 'train'),
                "metadata_example_id": ex.get('id', f"folio_{i}")
            })
        datasets.append({"dataset": "folio", "examples": examples})
        logger.info(f"FOLIO: {len(examples)} examples")
    except Exception as e:
        logger.error(f"FOLIO failed: {e}")

    # 3. CLUTRR - multi-hop reasoning, kinship relations
    try:
        with open("temp/datasets/full_clutrr.json") as f:
            data = json.load(f)
        examples = []
        for i, ex in enumerate(data):
            examples.append({
                "input": f"Story:\n{ex.get('story', ex.get('context', ''))}\nQuery: {ex.get('query', '')}",
                "output": str(ex.get('target_text', ex.get('answer', ''))),
                "metadata_example_id": ex.get('id', f"clutrr_{i}")
            })
        datasets.append({"dataset": "clutrr", "examples": examples})
        logger.info(f"CLUTRR: {len(examples)} examples")
    except Exception as e:
        logger.error(f"CLUTRR failed: {e}")

    # Save output
    output = {"datasets": datasets}
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)

    total_examples = sum(len(d['examples']) for d in datasets)
    logger.info(f"Saved to {OUTPUT_FILE}")
    logger.info(f"Total datasets: {len(datasets)}")
    logger.info(f"Total examples: {total_examples}")

if __name__ == "__main__":
    logger.info("Starting...")
    main()
    logger.info("Done!")
