#!/usr/bin/env python3
"""Quick benchmark for ayga-parser CLI utility features."""

import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ayga_cli.manifest import Manifest, ParserInfo, FuzzySearchIndex


def create_test_manifest(num_parsers: int = 1000) -> Manifest:
    """Create a test manifest."""
    parsers = {}
    categories = ["SE", "Net", "HTML", "FreeAI", "Social", "Ecommerce"]

    for i in range(num_parsers):
        cat = categories[i % len(categories)]
        name = f"{cat}::Parser{i}"
        parsers[name] = ParserInfo(
            name=name,
            description=f"Test parser {i} for {cat} operations",
            category=cat,
            presets=["default", "fast"],
            keywords=[cat.lower(), f"parser{i}", "test"],
        )

    return Manifest(parsers=parsers)


def main():
    print("=" * 60)
    print("ayga-parser CLI Quick Benchmark")
    print("=" * 60)

    # Create manifest
    print("\n[1/3] Creating test manifest with 1000 parsers...")
    start = time.perf_counter()
    manifest = create_test_manifest(1000)
    elapsed = (time.perf_counter() - start) * 1000
    print(f"      Created {manifest.parser_count} parsers in {elapsed:.1f}ms")

    # Build search index
    print("\n[2/3] Building fuzzy search index...")
    start = time.perf_counter()
    index = FuzzySearchIndex(manifest)
    index.build(manifest)
    elapsed = (time.perf_counter() - start) * 1000
    print(f"      Index built in {elapsed:.1f}ms")
    print(f"      Index size: {len(index._index)} keywords")

    # Search benchmark
    print("\n[3/3] Benchmarking fuzzy search (700 queries)...")
    queries = ["google", "parser", "test", "ai", "social", "parser500", "unknown"]
    search_times = []

    for _ in range(100):
        for query in queries:
            start = time.perf_counter()
            _ = index.search(query, limit=10)
            search_times.append(time.perf_counter() - start)

    avg_ms = (sum(search_times) / len(search_times)) * 1000
    print(f"      Average: {avg_ms:.2f}ms per query")
    print(f"      Throughput: {len(search_times) / sum(search_times):.0f} queries/sec")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    targets = {
        "Fuzzy search": (avg_ms, 50),
    }

    all_passed = True
    for name, (actual, target) in targets.items():
        status = "✓ PASS" if actual < target else "✗ FAIL"
        if actual >= target:
            all_passed = False
        print(f"  {status} {name}: {actual:.1f}ms (target: <{target}ms)")

    print("\n" + ("All benchmarks passed!" if all_passed else "Some benchmarks failed!"))
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
