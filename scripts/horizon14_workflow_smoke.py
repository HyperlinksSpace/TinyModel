#!/usr/bin/env python3
"""Horizon 14: orchestrated workflow DAG — deterministic topological execution order.

Defines a tiny inference-shaped DAG (ingest → tokenize → classify → emit_log), verifies
sort order and absence of cycles. Writes horizon14_workflow_run/1.0."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict, deque
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_SCHEMA = "horizon14_workflow_run/1.0"
_OUT = _REPO / ".tmp" / "horizon14-workflow" / "run.json"


def topo_sort(nodes: list[str], edges: list[tuple[str, str]]) -> list[str]:
    """edges (u,v): v depends on u (u runs before v)."""
    indeg: dict[str, int] = {n: 0 for n in nodes}
    adj: dict[str, list[str]] = defaultdict(list)
    node_set = set(nodes)
    for u, v in edges:
        if u not in node_set or v not in node_set:
            raise ValueError(f"edge references unknown node: {(u, v)!r}")
        adj[u].append(v)
        indeg[v] += 1
    q = deque([n for n in nodes if indeg[n] == 0])
    out: list[str] = []
    while q:
        n = q.popleft()
        out.append(n)
        for w in adj[n]:
            indeg[w] -= 1
            if indeg[w] == 0:
                q.append(w)
    if len(out) != len(nodes):
        raise ValueError("cycle or disconnected nodes")
    return out


def run_verify() -> tuple[dict, bool]:
    nodes = ["ingest", "tokenize", "classify", "emit_log"]
    edges = [
        ("ingest", "tokenize"),
        ("tokenize", "classify"),
        ("classify", "emit_log"),
    ]
    order = topo_sort(nodes, edges)
    ok = order == ["ingest", "tokenize", "classify", "emit_log"]

    cycle_ok = False
    try:
        topo_sort(["a", "b"], [("a", "b"), ("b", "a")])
    except ValueError:
        cycle_ok = True

    parallel_ok = False
    par = topo_sort(["x", "y", "z"], [])  # three roots — order among ties by deque (alphabetical insert order from indeg 0)
    parallel_ok = set(par) == {"x", "y", "z"} and len(par) == 3

    return (
        {
            "workflow_id": "tiny_infer_v1",
            "nodes": nodes,
            "edges": [{"from": u, "to": v} for u, v in edges],
            "topological_order": order,
            "order_matches_linear_chain": ok,
            "cycle_detected_on_ab": cycle_ok,
            "parallel_three_nodes_ok": parallel_ok,
        },
        ok and cycle_ok and parallel_ok,
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--verify", action="store_true")
    p.add_argument("--output-json", type=str, default=str(_OUT))
    return p.parse_args()


def main() -> int:
    a = parse_args()
    if not a.verify:
        print("Use --verify.", file=sys.stderr)
        return 2
    body, ok = run_verify()
    out = Path(a.output_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "horizon": 14,
        "schema": _SCHEMA,
        "mode": "dag_topological_smoke",
        "ok": ok,
        **body,
        "note": "Swap in your orchestrator (Airflow, Temporal, custom); this validates sort + cycle handling only.",
    }
    out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    if not ok:
        print("horizon14 verify: FAILED", file=sys.stderr)
        return 1
    print(f"horizon14 verify: OK wrote {out}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
