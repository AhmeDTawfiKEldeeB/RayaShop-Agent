"""Retrieval-only evaluation for the search_products tool.

Measures, per golden query:
  - hit@k        : at least one relevant product in top-k
  - MRR          : 1 / rank of the first relevant product (0 if none)
  - precision@k  : relevant results in top-k / k

Negative cases (expect_any == []) are correct when the tool returns nothing.

Usage:
    uv run python -m eval.run_eval                # default k=5
    uv run python -m eval.run_eval --k 3 --verbose
"""

import argparse
import sys
import time

from eval.golden_set import GOLDEN_SET
from src.Agent.tools.retrieval_tool import search_products_raw

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _is_relevant(product: dict, expect_any: list[str]) -> bool:
    name = (product.get("name") or "").lower()
    return any(keyword in name for keyword in expect_any)


def evaluate_case(case: dict, k: int) -> dict:
    query = case["query"]
    expect_any = case["expect_any"]
    negative = len(expect_any) == 0

    start = time.perf_counter()
    results = search_products_raw(query, limit=k)
    latency_ms = (time.perf_counter() - start) * 1000

    if negative:
        correct = len(results) == 0
        return {
            "query": query,
            "note": case["note"],
            "type": "negative",
            "correct": correct,
            "hit": correct,
            "mrr": 1.0 if correct else 0.0,
            "precision": 1.0 if correct else 0.0,
            "returned": len(results),
            "latency_ms": latency_ms,
            "top": "",
        }

    hits = [1 if _is_relevant(p, expect_any) else 0 for p in results]
    first_hit = next((i + 1 for i, h in enumerate(hits) if h), None)
    mrr = (1.0 / first_hit) if first_hit else 0.0

    top_name = results[0]["name"][:38] if results else "(empty)"
    return {
        "query": query,
        "note": case["note"],
        "type": "positive",
        "correct": bool(first_hit),
        "hit": bool(first_hit),
        "mrr": mrr,
        "precision": (sum(hits) / len(results)) if results else 0.0,
        "returned": len(results),
        "latency_ms": latency_ms,
        "top": top_name,
    }


def run(k: int, verbose: bool) -> dict:
    print(f"Retrieval eval — {len(GOLDEN_SET)} cases, k={k}\n")
    print(f"{'query':<28} {'type':<9} {'hit':<5} {'mrr':<6} {'p@k':<6} {'n':<3} {'ms':<7} top")
    print("-" * 100)

    results = []
    for case in GOLDEN_SET:
        r = evaluate_case(case, k)
        results.append(r)
        print(
            f"{r['query']:<28.28} {r['type']:<9} "
            f"{'Y' if r['hit'] else 'N':<5} "
            f"{r['mrr']:<6.3f} {r['precision']:<6.3f} "
            f"{r['returned']:<3} {r['latency_ms']:<7.0f} {r['top']}"
        )
        if verbose:
            print(f"{'':<28} -> {r['note']}")

    positives = [r for r in results if r["type"] == "positive"]
    negatives = [r for r in results if r["type"] == "negative"]

    summary = {
        "cases": len(results),
        "hit_rate": sum(1 for r in positives if r["hit"]) / max(len(positives), 1),
        "mrr": sum(r["mrr"] for r in positives) / max(len(positives), 1),
        "precision_at_k": sum(r["precision"] for r in positives) / max(len(positives), 1),
        "negative_accuracy": sum(1 for r in negatives if r["correct"]) / max(len(negatives), 1),
        "avg_latency_ms": sum(r["latency_ms"] for r in results) / len(results),
    }

    print("-" * 100)
    print(f"Hit@{k}          : {summary['hit_rate']:.1%}  (positive cases)")
    print(f"MRR             : {summary['mrr']:.3f}")
    print(f"Precision@{k}     : {summary['precision_at_k']:.3f}")
    print(f"Negative acc.   : {summary['negative_accuracy']:.1%}  (greetings/nonsense return nothing)")
    print(f"Avg latency     : {summary['avg_latency_ms']:.0f} ms")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the retrieval tool")
    parser.add_argument("--k", type=int, default=5, help="cutoff for hit/precision (default 5)")
    parser.add_argument("--verbose", action="store_true", help="print case notes")
    args = parser.parse_args()
    run(k=args.k, verbose=args.verbose)


if __name__ == "__main__":
    main()
