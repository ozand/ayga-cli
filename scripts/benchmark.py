#!/usr/bin/env python3
"""Benchmark script for A-Parser CLI performance testing.

Tests cache loading, fuzzy search, and command completion times.
"""

import gzip
import json
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from aparser_cli.manifest import ManifestCache, FuzzySearchIndex, Manifest, ParserInfo


def create_test_manifest(num_parsers: int = 1000) -> Manifest:
    """Create a test manifest with specified number of parsers."""
    parsers = {}
    categories = ["SE", "Net", "HTML", "FreeAI", "Social", "Ecommerce"]

    for i in range(num_parsers):
        cat = categories[i % len(categories)]
        name = f"{cat}::Parser{i}"

        parsers[name] = ParserInfo(
            name=name,
            description=f"Test parser {i} for {cat} operations",
            category=cat,
            presets=["default", "fast", "thorough"],
            keywords=[cat.lower(), f"parser{i}", "test"],
        )

    return Manifest(parsers=parsers)


def benchmark_cache_save_load(manifest: Manifest, iterations: int = 10) -> dict:
    """Benchmark cache save and load operations."""
    import tempfile
    import os

    # Create a temporary directory for the cache
    temp_dir = tempfile.mkdtemp()
    cache_path = Path(temp_dir) / "manifest.json.gz"

    # Create a mock config that returns our temp directory
    class MockConfig:
        @staticmethod
        def get_config_dir():
            return Path(temp_dir)

    cache = ManifestCache(config=MockConfig())

    # Benchmark save
    save_times = []
    for _ in range(iterations):
        start = time.perf_counter()
        cache.save(manifest)
        save_times.append(time.perf_counter() - start)

    # Benchmark load
    load_times = []
    for _ in range(iterations):
        start = time.perf_counter()
        _ = cache.load()
        load_times.append(time.perf_counter() - start)

    # Get file size
    file_size = cache.cache_path.stat().st_size

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)

    return {
        "save_avg_ms": (sum(save_times) / len(save_times)) * 1000,
        "save_min_ms": min(save_times) * 1000,
        "save_max_ms": max(save_times) * 1000,
        "load_avg_ms": (sum(load_times) / len(load_times)) * 1000,
        "load_min_ms": min(load_times) * 1000,
        "load_max_ms": max(load_times) * 1000,
        "file_size_kb": file_size / 1024,
    }


def benchmark_fuzzy_search(manifest: Manifest, iterations: int = 100) -> dict:
    """Benchmark fuzzy search performance."""
    from aparser_cli.manifest import FuzzySearchIndex

    # Build search index directly
    engine = FuzzySearchIndex(manifest)
    engine.build(manifest)

    # Benchmark searches
    queries = ["google", "parser", "test", "ai", "social", "parser500", "unknown"]
    search_times = []

    for _ in range(iterations):
        for query in queries:
            start = time.perf_counter()
            _ = engine.search(query, limit=10)
            search_times.append(time.perf_counter() - start)

    return {
        "avg_ms": (sum(search_times) / len(search_times)) * 1000,
        "min_ms": min(search_times) * 1000,
        "max_ms": max(search_times) * 1000,
        "queries_per_sec": len(search_times) / sum(search_times),
    }


def benchmark_compression(manifest: Manifest) -> dict:
    """Benchmark compression ratios."""
    # Raw JSON size
    raw_json = json.dumps(manifest.model_dump(mode='json'), ensure_ascii=False)
    raw_size = len(raw_json.encode("utf-8"))

    # Gzip compressed size
    compressed = gzip.compress(raw_json.encode("utf-8"))
    compressed_size = len(compressed)

    return {
        "raw_size_kb": raw_size / 1024,
        "compressed_size_kb": compressed_size / 1024,
        "compression_ratio": raw_size / compressed_size,
        "space_saved_percent": (1 - compressed_size / raw_size) * 100,
    }


def main():
    """Run all benchmarks."""
    print("=" * 60)
    print("A-Parser CLI Performance Benchmarks")
    print("=" * 60)

    # Create test manifest with 1000 parsers
    print("\n[1/4] Creating test manifest with 1000 parsers...")
    manifest = create_test_manifest(1000)
    print(f"      Created {manifest.parser_count} parsers")

    # Benchmark compression
    print("\n[2/4] Benchmarking compression...")
    compression_results = benchmark_compression(manifest)
    print(f"      Raw size: {compression_results['raw_size_kb']:.1f} KB")
    print(f"      Compressed: {compression_results['compressed_size_kb']:.1f} KB")
    print(f"      Compression ratio: {compression_results['compression_ratio']:.1f}x")
    print(f"      Space saved: {compression_results['space_saved_percent']:.1f}%")

    # Benchmark cache save/load
    print("\n[3/4] Benchmarking cache save/load (10 iterations)...")
    cache_results = benchmark_cache_save_load(manifest)
    print(f"      Save: {cache_results['save_avg_ms']:.1f}ms (min: {cache_results['save_min_ms']:.1f}ms, max: {cache_results['save_max_ms']:.1f}ms)")
    print(f"      Load: {cache_results['load_avg_ms']:.1f}ms (min: {cache_results['load_min_ms']:.1f}ms, max: {cache_results['load_max_ms']:.1f}ms)")
    print(f"      File size: {cache_results['file_size_kb']:.1f} KB")

    # Benchmark fuzzy search
    print("\n[4/4] Benchmarking fuzzy search (700 queries)...")
    search_results = benchmark_fuzzy_search(manifest)
    print(f"      Average: {search_results['avg_ms']:.2f}ms per query")
    print(f"      Min: {search_results['min_ms']:.2f}ms, Max: {search_results['max_ms']:.2f}ms")
    print(f"      Throughput: {search_results['queries_per_sec']:.0f} queries/sec")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    # Check against targets
    targets = {
        "Cache load": (cache_results['load_avg_ms'], 100),
        "Fuzzy search": (search_results['avg_ms'], 50),
        "Command completion": (cache_results['load_avg_ms'] + search_results['avg_ms'], 200),
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
