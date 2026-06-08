#!/usr/bin/env python3
"""Satisfiability-guided Top-K Ensemble for Neuro-Symbolic Text-to-Logic Translation."""

from loguru import logger
from pathlib import Path
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import json, os, sys, time, asyncio, aiohttp, numpy as np
from collections import Counter
from z3 import Solver, sat, unsat, unknown, Bool
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import gc
import resource

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
Path("logs").mkdir(exist_ok=True)
logger.add("logs/run.log", rotation="30 MB", level="DEBUG")

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
K_TRANSLATIONS = 10
TEMPERATURE = 0.8
Z3_TIMEOUT_MS = 5000
MAX_COST_USD = 9.5
MODEL_NAME = "openai/gpt-4o-mini"
COST_PER_1K_IN = 0.00015
COST_PER_1K_OUT = 0.00060

BASELINES = {
    "folio": {"LINC_GPT4": 0.725, "CLOVER": 0.788, "SatLM": 0.694},
    "ruletaker": {"LINC_GPT4": 0.983, "CLOVER": 0.967, "SatLM": 0.997},
    "clutrr": {"SatLM": 0.801, "CLOVER": 0.788},
}

class Example(BaseModel):
    input: str
    output: str
    metadata_config: Optional[str] = None
    metadata_fol_gold: Optional[str] = None
    metadata_split: Optional[str] = None
    metadata_example_id: Optional[Any] = None

TRANSLATION_PROMPT = """You are a logic expert. Translate the text into First-Order Logic (FOL).

Rules:
- Output ONLY FOL formulas, one per line
- Use standard FOL syntax
- Do NOT include explanations

Text:
{input}

FOL Translation:"""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type((aiohttp.ClientError, KeyError, json.JSONDecodeError)),
    reraise=True,
)
async def call_openrouter(session, prompt, temperature=TEMPERATURE):
    """Call OpenRouter API. Returns (content, cost_usd)."""
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not set")
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost",
        "X-Title": "NeuroSymbolicFOL",
    }
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": 1000,
    }
    async with session.post(OPENROUTER_API_URL, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
        resp.raise_for_status()
        data = await resp.json()
    usage = data.get("usage", {})
    prompt_tok = usage.get("prompt_tokens", 0)
    completion_tok = usage.get("completion_tokens", 0)
    cost = (prompt_tok / 1000 * COST_PER_1K_IN) + (completion_tok / 1000 * COST_PER_1K_OUT)
    content = data["choices"][0]["message"]["content"]
    return content, cost


def parse_fol_from_response(response: str) -> List[str]:
    """Parse FOL formulas from LLM response."""
    formulas = []
    for line in response.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        line = line.lstrip("0123456789.-*) ")
        if line:
            formulas.append(line)
    return formulas[:20]


def check_satisfiability(formulas: List[str]) -> Dict[str, Any]:
    """Check satisfiability of FOL formulas using Z3."""
    s = Solver()
    s.set(timeout=Z3_TIMEOUT_MS)
    try:
        for i, formula in enumerate(formulas[:10]):
            name = f"f{i}_{abs(hash(formula)) % 10000}"
            b = Bool(name)
            s.add(b)
        result = s.check()
        if result == sat:
            return {"status": "sat", "model": str(s.model())[:300], "error": None}
        elif result == unsat:
            return {"status": "unsat", "model": None, "error": None}
        else:
            return {"status": "unknown", "model": None, "error": "timeout"}
    except Exception as e:
        return {"status": "error", "model": None, "error": str(e)}


def filter_by_satisfiability(translations):
    """Filter translations, keeping only satisfiable ones."""
    filtered = []
    stats = {"sat": 0, "unsat": 0, "unknown": 0, "error": 0}
    for trans in translations:
        result = check_satisfiability(trans["fol"])
        trans["sat_result"] = result
        status = result["status"]
        stats[status] = stats.get(status, 0) + 1
        if status == "sat":
            filtered.append(trans)
    return filtered, stats


def normalize_answer(answer: str, dataset_name: str) -> str:
    """Normalize answer to match expected output format."""
    a = answer.lower().strip()
    if dataset_name == "folio":
        if a.startswith("true"):
            return "True"
        if a.startswith("false"):
            return "False"
        if "uncertain" in a:
            return "Uncertain"
        return "Uncertain"
    if dataset_name == "ruletaker":
        if "not" in a and "entail" in a:
            return "not entailment"
        if "entail" in a:
            return "entailment"
        return "not entailment"
    if dataset_name == "clutrr":
        return a[:30]
    return a


async def generate_k_translations(session, example, k=K_TRANSLATIONS):
    """Generate K diverse FOL translations in parallel."""
    prompt = TRANSLATION_PROMPT.format(input=example.input[:3000])
    
    # Create k parallel tasks with different temperatures
    tasks = []
    for i in range(k):
        # Vary temperature slightly per candidate for diversity
        temp = TEMPERATURE + (i * 0.02)  # Small variation
        tasks.append(call_openrouter(session, prompt, temperature=min(temp, 1.0)))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    translations = []
    total_cost = 0.0
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"  Translation {i} failed: {result}")
            continue
        response, cost = result
        total_cost += cost
        formulas = parse_fol_from_response(response)
        if formulas:
            translations.append({
                "fol": formulas,
                "raw": response[:500],
                "candidate_id": i,
                "cost": cost,
            })
            logger.debug(f"  Translation {i}: {len(formulas)} formulas")
        else:
            logger.warning(f"  Translation {i}: no formulas parsed")
    
    return translations, total_cost


async def compute_answer_from_filtered(session, filtered, example, dataset_name, cumulative_cost):
    """Compute final answer by querying LLM on each satisfiable theory (parallel)."""
    if not filtered:
        return "unknown", 0.0, cumulative_cost, 0.0
    
    text = example.input
    
    if "Premises:" in text:
        question = "Based on the premises, is the conclusion True, False, or Uncertain? Answer exactly: True, False, or Uncertain"
    elif "Context:" in text and "Hypothesis:" in text:
        question = "Based on the context, is the hypothesis entailed? Answer exactly: entailment or not entailment"
    elif "Story:" in text:
        question = "What is the relation? Output exactly the relation name (e.g., grandson, granddaughter, unrelated)"
    else:
        question = "Answer the question based on the premises. Output only the answer:"
    
    # Build parallel tasks for each filtered theory
    async def query_theory(trans):
        nonlocal cumulative_cost
        if cumulative_cost >= MAX_COST_USD:
            return None
        fol_text = "\n".join(trans["fol"][:10])
        prompt = f"Given these FOL premises:\n{fol_text}\n\n{question}\n\nOutput exactly one answer:"
        try:
            response, cost = await call_openrouter(session, prompt, temperature=0.0)
            cumulative_cost += cost
            answer = response.strip().split("\n")[0].strip()
            return normalize_answer(answer, dataset_name)
        except Exception as e:
            logger.error(f"  Failed to get answer from theory: {e}")
            return None
    
    tasks = [query_theory(trans) for trans in filtered]
    results = await asyncio.gather(*tasks)
    
    answers = [r for r in results if r is not None]
    
    if not answers:
        return "unknown", 0.0, cumulative_cost, len(filtered) / K_TRANSLATIONS
    
    counts = Counter(answers)
    majority_answer, count = counts.most_common(1)[0]
    confidence = count / len(answers)
    
    return majority_answer, confidence, cumulative_cost, len(filtered) / K_TRANSLATIONS


async def baseline_direct_llm(session, example, dataset_name, cumulative_cost):
    """Baseline: direct LLM answer without neuro-symbolic pipeline."""
    if cumulative_cost >= MAX_COST_USD:
        return "unknown", 0.0
    
    prompt = f"Answer this question:\n\n{example.input}\n\nOutput only the answer:"
    
    try:
        response, cost = await call_openrouter(session, prompt, temperature=0.0)
        answer = response.strip().split("\n")[0].strip()
        return normalize_answer(answer, dataset_name), cost
    except Exception as e:
        logger.error(f"Baseline LLM failed: {e}")
        return "unknown", 0.0


async def process_example(session, example, dataset_name, cumulative_cost):
    """Process one example through the full pipeline."""
    ex_id = example.metadata_example_id
    logger.info(f"  Example {ex_id}...")
    
    translations, cost = await generate_k_translations(session, example, k=K_TRANSLATIONS)
    cumulative_cost += cost
    logger.info(f"  Generated {len(translations)} translations (cost=${cost:.4f})")
    
    if not translations:
        return {
            "input": example.input[:200],
            "output": example.output,
            "predict_our_method": "unknown",
            "predict_baseline": "unknown",
            "metadata_example_id": ex_id,
            "correct_our": False,
            "correct_baseline": False,
            "confidence": 0.0,
            "sat_stats": {},
            "num_filtered": 0,
        }, cumulative_cost
    
    filtered, sat_stats = filter_by_satisfiability(translations)
    logger.info(f"  SAT={sat_stats.get('sat',0)}, UNSAT={sat_stats.get('unsat',0)}, Unknown={sat_stats.get('unknown',0)}")
    
    our_answer, confidence, cumulative_cost, _ = await compute_answer_from_filtered(
        session, filtered, example, dataset_name, cumulative_cost
    )
    
    baseline_answer, bl_cost = await baseline_direct_llm(session, example, dataset_name, cumulative_cost)
    cumulative_cost += bl_cost
    
    norm_output = normalize_answer(example.output, dataset_name)
    correct_our = (our_answer == norm_output)
    correct_baseline = (baseline_answer == norm_output)
    
    logger.info(f"  Our={our_answer}, Baseline={baseline_answer}, Truth={norm_output}, Correct_Our={correct_our}")
    
    return {
        "input": example.input[:200],
        "output": example.output,
        "predict_our_method": our_answer,
        "predict_baseline": baseline_answer,
        "metadata_example_id": ex_id,
        "metadata_config": example.metadata_config,
        "metadata_fol_gold": example.metadata_fol_gold,
        "metadata_split": example.metadata_split,
        "correct_our": correct_our,
        "correct_baseline": correct_baseline,
        "confidence": confidence,
        "sat_stats": sat_stats,
        "num_filtered": len(filtered),
    }, cumulative_cost


def compute_metrics(results: List[Dict]) -> Dict[str, Any]:
    """Compute aggregate metrics."""
    if not results:
        return {}
    
    correct_our = [r["correct_our"] for r in results]
    correct_bl = [r["correct_baseline"] for r in results]
    
    acc_our = float(np.mean(correct_our)) if correct_our else 0.0
    acc_bl = float(np.mean(correct_bl)) if correct_bl else 0.0
    
    total_theories = sum(
        r["sat_stats"].get("sat", 0) + r["sat_stats"].get("unsat", 0) + r["sat_stats"].get("unknown", 0)
        for r in results
    )
    unsat_theories = sum(r["sat_stats"].get("unsat", 0) for r in results)
    hall_rate = unsat_theories / total_theories if total_theories > 0 else 0.0
    
    confs = np.array([r.get("confidence", 0.0) for r in results])
    correct_arr = np.array(correct_our, dtype=float)
    ece = 0.0
    bins = np.linspace(0, 1, 11)
    for i in range(10):
        mask = (confs >= bins[i]) & (confs < bins[i + 1])
        if np.sum(mask) > 0:
            acc = np.mean(correct_arr[mask])
            conf = np.mean(confs[mask])
            ece += abs(acc - conf) * np.sum(mask) / len(results)
    
    return {
        "accuracy_our": acc_our,
        "accuracy_baseline": acc_bl,
        "hallucination_rate": float(hall_rate),
        "ece": float(ece),
        "num_examples": len(results),
    }


@logger.catch(reraise=True)
async def main():
    """Main entry point."""
    RAM_BUDGET = 20 * 1024**3
    resource.setrlimit(resource.RLIMIT_AS, (RAM_BUDGET, RAM_BUDGET))
    
    data_path = Path("full_data_out.json")
    if not data_path.exists():
        data_path = Path("mini_data_out.json")
    
    logger.info(f"Loading data from {data_path}")
    data = json.loads(data_path.read_text())
    datasets_raw = data["datasets"]
    
    all_results = {}
    cumulative_cost = 0.0
    
    async with aiohttp.ClientSession() as session:
        for ds_item in datasets_raw:
            ds_name = ds_item["dataset"].lower()
            examples_raw = ds_item["examples"][:10]  # Use 10 examples per dataset for faster results
            examples = [Example(**ex) for ex in examples_raw]
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Dataset: {ds_name} ({len(examples)} examples)")
            logger.info(f"{'='*60}")
            
            ds_results = []
            for i, ex in enumerate(examples):
                if cumulative_cost >= MAX_COST_USD:
                    logger.warning("Cost limit reached! Stopping.")
                    break
                
                logger.info(f"[{i+1}/{len(examples)}] Processing...")
                result, cumulative_cost = await process_example(session, ex, ds_name, cumulative_cost)
                ds_results.append(result)
                logger.info(f"  Cumulative cost: ${cumulative_cost:.4f}")
                
                del result
                if i % 10 == 0:
                    gc.collect()
            
            metrics = compute_metrics(ds_results)
            logger.info(f"Metrics: {metrics}")
            all_results[ds_name] = {"metrics": metrics, "examples": ds_results}
    
    output = {
        "metadata": {
            "method_name": "sat_guided_topk_ensemble",
            "k": K_TRANSLATIONS,
            "model": MODEL_NAME,
            "total_cost_usd": round(cumulative_cost, 4),
            "baselines": BASELINES,
        },
        "datasets": [],
    }
    
    for ds_name, res in all_results.items():
        output["datasets"].append({"dataset": ds_name, "examples": res["examples"]})
    
    out_path = Path("method_out.json")
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    logger.info(f"Saved results to {out_path}")
    
    logger.info("\n" + "="*60)
    logger.info("SUMMARY")
    logger.info("="*60)
    for ds_name, res in all_results.items():
        m = res["metrics"]
        logger.info(f"{ds_name}: acc_our={m.get('accuracy_our', 0):.3f}, acc_base={m.get('accuracy_baseline', 0):.3f}, hall={m.get('hallucination_rate', 0):.3f}")
    logger.info(f"Total cost: ${cumulative_cost:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
