"""
Performance Benchmarking Suite
Task 268: Add performance benchmarking suite

Comprehensive benchmarking tools for measuring blockchain performance.
"""

from __future__ import annotations

import time
import statistics
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass, field
import json


@dataclass
class BenchmarkResult:
    """Result from a single benchmark"""
    name: str
    iterations: int
    total_time: float
    mean_time: float
    median_time: float
    min_time: float
    max_time: float
    std_dev: float
    operations_per_second: float
    measurements: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "iterations": self.iterations,
            "total_time_seconds": self.total_time,
            "mean_time_ms": self.mean_time * 1000,
            "median_time_ms": self.median_time * 1000,
            "min_time_ms": self.min_time * 1000,
            "max_time_ms": self.max_time * 1000,
            "std_dev_ms": self.std_dev * 1000,
            "ops_per_second": self.operations_per_second
        }


class Benchmark:
    """Single benchmark"""

    def __init__(self, name: str, func: Callable, iterations: int = 100):
        """
        Initialize benchmark

        Args:
            name: Benchmark name
            func: Function to benchmark
            iterations: Number of iterations to run
        """
        self.name = name
        self.func = func
        self.iterations = iterations
        self.measurements: List[float] = []

    def run(self) -> BenchmarkResult:
        """Run benchmark and collect results"""
        self.measurements.clear()

        # Warmup
        for _ in range(min(10, self.iterations // 10)):
            self.func()

        # Actual measurements
        for _ in range(self.iterations):
            start = time.perf_counter()
            self.func()
            elapsed = time.perf_counter() - start
            self.measurements.append(elapsed)

        return self._calculate_results()

    def _calculate_results(self) -> BenchmarkResult:
        """Calculate benchmark statistics"""
        total_time = sum(self.measurements)
        mean_time = statistics.mean(self.measurements)
        median_time = statistics.median(self.measurements)
        min_time = min(self.measurements)
        max_time = max(self.measurements)
        std_dev = statistics.stdev(self.measurements) if len(self.measurements) > 1 else 0
        ops_per_second = self.iterations / total_time if total_time > 0 else 0

        return BenchmarkResult(
            name=self.name,
            iterations=self.iterations,
            total_time=total_time,
            mean_time=mean_time,
            median_time=median_time,
            min_time=min_time,
            max_time=max_time,
            std_dev=std_dev,
            operations_per_second=ops_per_second,
            measurements=self.measurements
        )


class BenchmarkSuite:
    """Suite of benchmarks"""

    def __init__(self, name: str = "Blockchain Benchmarks"):
        self.name = name
        self.benchmarks: List[Benchmark] = []
        self.results: List[BenchmarkResult] = []

    def add_benchmark(self, name: str, func: Callable, iterations: int = 100) -> None:
        """Add benchmark to suite"""
        self.benchmarks.append(Benchmark(name, func, iterations))

    def run_all(self) -> List[BenchmarkResult]:
        """Run all benchmarks"""
        self.results.clear()

        print(f"\n{'='*60}")
        print(f"{self.name}")
        print(f"{'='*60}\n")

        for benchmark in self.benchmarks:
            print(f"Running: {benchmark.name}...")
            result = benchmark.run()
            self.results.append(result)
            print(f"  {result.operations_per_second:,.2f} ops/sec "
                  f"({result.mean_time*1000:.3f}ms avg)\n")

        return self.results

    def export_results(self, filename: str) -> None:
        """Export results to JSON"""
        data = {
            "suite_name": self.name,
            "benchmarks": [r.to_dict() for r in self.results]
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

    def compare_with_baseline(self, baseline_file: str) -> Dict[str, Any]:
        """Compare current results with baseline"""
        try:
            with open(baseline_file, 'r') as f:
                baseline = json.load(f)

            comparisons = []

            for current in self.results:
                # Find matching baseline
                baseline_result = None
                for b in baseline.get('benchmarks', []):
                    if b['name'] == current.name:
                        baseline_result = b
                        break

                if baseline_result:
                    current_ops = current.operations_per_second
                    baseline_ops = baseline_result['ops_per_second']
                    diff_percent = ((current_ops - baseline_ops) / baseline_ops) * 100

                    comparisons.append({
                        "name": current.name,
                        "current_ops": current_ops,
                        "baseline_ops": baseline_ops,
                        "difference_percent": diff_percent,
                        "status": "improved" if diff_percent > 0 else "regressed"
                    })

            return {"comparisons": comparisons}

        except FileNotFoundError:
            return {"error": "Baseline file not found"}


class BlockchainBenchmarks:
    """Predefined blockchain benchmarks"""

    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.suite = BenchmarkSuite("Blockchain Core Benchmarks")

    def setup_benchmarks(self) -> BenchmarkSuite:
        """Setup standard blockchain benchmarks"""

        # Transaction validation
        self.suite.add_benchmark(
            "Transaction Hash Calculation",
            self._bench_tx_hash,
            iterations=1000
        )

        self.suite.add_benchmark(
            "Transaction Signature Verification",
            self._bench_tx_verify,
            iterations=100
        )

        # Block operations
        self.suite.add_benchmark(
            "Block Hash Calculation",
            self._bench_block_hash,
            iterations=1000
        )

        self.suite.add_benchmark(
            "Merkle Root Calculation",
            self._bench_merkle_root,
            iterations=500
        )

        # Database operations
        self.suite.add_benchmark(
            "Balance Lookup",
            self._bench_balance_lookup,
            iterations=1000
        )

        return self.suite

    def _bench_tx_hash(self) -> None:
        """Benchmark transaction hash calculation"""
        import hashlib
        data = {"sender": "XAI"+"0"*40, "recipient": "XAI"+"1"*40, "amount": 10.0}
        json_str = json.dumps(data, sort_keys=True)
        hashlib.sha256(json_str.encode()).hexdigest()

    def _bench_tx_verify(self) -> None:
        """Benchmark transaction verification"""
        # Simplified - in production would verify actual signatures
        import hashlib
        data = "transaction_data"
        for _ in range(10):
            hashlib.sha256(data.encode()).hexdigest()

    def _bench_block_hash(self) -> None:
        """Benchmark block hash calculation"""
        import hashlib
        data = {
            "index": 1,
            "previous_hash": "0" * 64,
            "timestamp": time.time(),
            "nonce": 12345
        }
        json_str = json.dumps(data, sort_keys=True)
        hashlib.sha256(json_str.encode()).hexdigest()

    def _bench_merkle_root(self) -> None:
        """Benchmark merkle root calculation"""
        import hashlib

        # Create sample transaction hashes
        tx_hashes = [f"tx_{i}_hash" for i in range(100)]
        hashes = tx_hashes.copy()

        while len(hashes) > 1:
            if len(hashes) % 2 != 0:
                hashes.append(hashes[-1])

            new_hashes = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i + 1]
                new_hash = hashlib.sha256(combined.encode()).hexdigest()
                new_hashes.append(new_hash)

            hashes = new_hashes

    def _bench_balance_lookup(self) -> None:
        """Benchmark balance lookup"""
        # Simulate dictionary lookup
        balances = {f"XAI{'0'*40}": 100.0}
        _ = balances.get(f"XAI{'0'*40}", 0.0)


class PerformanceComparison:
    """Compare performance across different implementations"""

    def __init__(self):
        self.implementations: Dict[str, List[BenchmarkResult]] = {}

    def add_implementation(self, name: str, results: List[BenchmarkResult]) -> None:
        """Add implementation results"""
        self.implementations[name] = results

    def compare(self) -> Dict[str, Any]:
        """Compare all implementations"""
        if len(self.implementations) < 2:
            return {"error": "Need at least 2 implementations to compare"}

        # Find common benchmarks
        all_benchmark_names = set()
        for results in self.implementations.values():
            all_benchmark_names.update(r.name for r in results)

        comparisons = {}

        for bench_name in all_benchmark_names:
            bench_comparison = {}

            for impl_name, results in self.implementations.items():
                result = next((r for r in results if r.name == bench_name), None)
                if result:
                    bench_comparison[impl_name] = {
                        "ops_per_second": result.operations_per_second,
                        "mean_time_ms": result.mean_time * 1000
                    }

            if bench_comparison:
                # Find fastest
                fastest = max(bench_comparison.items(), key=lambda x: x[1]["ops_per_second"])
                comparisons[bench_name] = {
                    "implementations": bench_comparison,
                    "fastest": fastest[0]
                }

        return comparisons


class MicroBenchmark:
    """Micro-benchmark for small code segments"""

    @staticmethod
    def time_function(func: Callable, iterations: int = 10000) -> float:
        """
        Time a function execution

        Args:
            func: Function to time
            iterations: Number of iterations

        Returns:
            Average time per iteration in seconds
        """
        start = time.perf_counter()

        for _ in range(iterations):
            func()

        elapsed = time.perf_counter() - start
        return elapsed / iterations

    @staticmethod
    def compare_functions(funcs: Dict[str, Callable], iterations: int = 10000) -> Dict[str, float]:
        """
        Compare multiple function implementations

        Args:
            funcs: Dictionary of name -> function
            iterations: Number of iterations per function

        Returns:
            Dictionary of name -> average time
        """
        results = {}

        for name, func in funcs.items():
            avg_time = MicroBenchmark.time_function(func, iterations)
            results[name] = avg_time

        return results


class ThroughputMeasurement:
    """Measure system throughput"""

    def __init__(self):
        self.start_time: Optional[float] = None
        self.operation_count = 0

    def start(self) -> None:
        """Start measurement"""
        self.start_time = time.time()
        self.operation_count = 0

    def record_operation(self) -> None:
        """Record an operation"""
        self.operation_count += 1

    def get_throughput(self) -> float:
        """
        Get current throughput

        Returns:
            Operations per second
        """
        if not self.start_time:
            return 0.0

        elapsed = time.time() - self.start_time
        if elapsed == 0:
            return 0.0

        return self.operation_count / elapsed

    def reset(self) -> None:
        """Reset measurement"""
        self.start_time = None
        self.operation_count = 0
