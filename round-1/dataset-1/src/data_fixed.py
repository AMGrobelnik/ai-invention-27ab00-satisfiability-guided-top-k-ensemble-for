#!/usr/bin/env python3
"""Load and standardize datasets to exp_sel_data_out.json schema."""

import json
from pathlib import Path
from loguru import logger

logger.remove()
logger.add("logs/data.log", rotation="30 MB", level="DEBUG")
logger.add(lambda msg: print(msg, end=""), level="INFO")

OUTPUT_FILE = Path("full_data_out.json")

@logger.catch(reraise=True)
def main():
    """Load all datasets and standardize to exp_sel_data_out schema."""
    datasets = []

    # 1. RuleTaker
    try:
        with open("temp/datasets/full_ruletaker.json") as f:
            data = json.load(f)
        examples = []
        for i, ex in enumerate(data):
            # RuleTaker uses 'label' field for answer
            examples.append({
                "input": f"Context: {ex.get('context', '')}\nQuestion: {ex.get('query', '')}",
                "output": str(ex.get('label', ex.get('answer', ''))),
                "metadata_source": "tasksource/ruletaker",
                "metadata_config": ex.get('config', 'train'),
                "metadata_example_id": i
            })
        datasets.append({"dataset": "ruletaker", "examples": examples})
        logger.info(f"RuleTaker: {len(examples)} examples")
    except Exception as e:
        logger.error(f"RuleTaker failed: {e}")

    # 2. FOLIO
    try:
        with open("temp/datasets/full_folio.json") as f:
            data = json.load(f)
        examples = []
        for i, ex in enumerate(data):
            examples.append({
                "input": f"Premises:\n{ex.get('premises', ex.get('context', ''))}\nConclusion: {ex.get('conclusion', ex.get('query', ''))}",
                "output": str(ex.get('answer', '')),
                "metadata_source": "tasksource/folio",
                "metadata_fol_gold": ex.get('premises-FOL', '') + "\nConclusion: " + ex.get('conclusion-FOL', ''),
                "metadata_example_id": ex.get('example_id', f"folio_{i}")
            })
        datasets.append({"dataset": "folio", "examples": examples})
        logger.info(f"FOLIO: {len(examples)} examples")
    except Exception as e:
        logger.error(f"FOLIO failed: {e}")

    # 3. ProofWriter
    try:
        with open("temp/datasets/full_proofwriter.json") as f:
            data = json.load(f)
        examples = []
        for i, ex in enumerate(data):
            examples.append({
                "input": f"Theory:\n{ex.get('theory', ex.get('context', ''))}\nQuestion: {ex.get('question', '')}",
                "output": str(ex.get('answer', '')),
                "metadata_source": "tasksource/proofwriter",
                "metadata_fol_gold": ex.get('allProofs', ''),
                "metadata_config": ex.get('config', 'train'),
                "metadata_example_id": ex.get('id', f"proofwriter_{i}")
            })
        datasets.append({"dataset": "proofwriter", "examples": examples})
        logger.info(f"ProofWriter: {len(examples)} examples")
    except Exception as e:
        logger.error(f"ProofWriter failed: {e}")

    # 4. CLUTRR
    try:
        with open("temp/datasets/full_clutrr.json") as f:
            data = json.load(f)
        examples = []
        for i, ex in enumerate(data):
            examples.append({
                "input": f"Story:\n{ex.get('story', ex.get('context', ''))}\nQuery: {ex.get('query', '')}",
                "output": str(ex.get('target_text', ex.get('answer', ''))),
                "metadata_source": "kendrivp/CLUTRR_v1_extracted",
                "metadata_example_id": ex.get('id', f"clutrr_{i}")
            })
        datasets.append({"dataset": "clutrr", "examples": examples})
        logger.info(f"CLUTRR: {len(examples)} examples")
    except Exception as e:
        logger.error(f"CLUTRR failed: {e}")

    # 5. LogicalReasoning
    try:
        with open("temp/datasets/full_logical_reasoning.json") as f:
            data = json.load(f)
        examples = []
        for i, ex in enumerate(data):
            premises_nl = "\n".join(ex.get('premises_nl', []))
            question_nl = ex.get('question_nl', '')
            examples.append({
                "input": f"Premises:\n{premises_nl}\nQuestion: {question_nl}",
                "output": str(ex.get('answer', '')),
                "metadata_source": "flaitenberger/LogicalReasoning-hard-v3",
                "metadata_fol_gold": "\n".join(ex.get('premises_fol', [])) + "\nQuery: " + ex.get('question_fol', ''),
                "metadata_config": ex.get('split', 'train'),
                "metadata_example_id": ex.get('id', f"logical_reasoning_{i}")
            })
        datasets.append({"dataset": "logical_reasoning", "examples": examples})
        logger.info(f"LogicalReasoning: {len(examples)} examples")
    except Exception as e:
        logger.error(f"LogicalReasoning failed: {e}")

    # 6. SNLI
    try:
        with open("temp/datasets/full_snli.json") as f:
            data = json.load(f)
        examples = []
        for i, ex in enumerate(data):
            examples.append({
                "input": f"Premise: {ex.get('premise', ex.get('context', ''))}\nHypothesis: {ex.get('hypothesis', ex.get('query', ''))}",
                "output": str(ex.get('answer', '')),
                "metadata_source": "stanfordnlp/snli",
                "metadata_example_id": i
            })
        datasets.append({"dataset": "snli", "examples": examples})
        logger.info(f"SNLI: {len(examples)} examples")
    except Exception as e:
        logger.error(f"SNLI failed: {e}")

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
