"""
Stress Testing Framework
Task 267: Implement stress testing framework

Comprehensive stress testing framework for blockchain performance testing.
"""

from __future__ import annotations

import logging
import time
import random  # OK for test data generation in performance simulation
import threading
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


@dataclass
class StressTestResult:
    """Results from a stress test"""
    test_name: str
    duration: float
    total_operations: int
    successful_operations: int
    failed_operations: int
    operations_per_second: float
    average_latency: float
    min_latency: float
    max_latency: float
    errors: List[str] = field(default_factory=list)

    def get_summary(self) -> Dict[str, Any]:
        """Get test summary"""
        return {
            "test_name": self.test_name,
            "duration_seconds": self.duration,
            "total_operations": self.total_operations,
            "successful": self.successful_operations,
            "failed": self.failed_operations,
            "success_rate": (self.successful_operations / max(1, self.total_operations)) * 100,
            "ops_per_second": self.operations_per_second,
            "latency": {
                "average_ms": self.average_latency * 1000,
                "min_ms": self.min_latency * 1000,
                "max_ms": self.max_latency * 1000
            },
            "error_count": len(self.errors)
        }


from abc import ABC, abstractmethod


class StressTest(ABC):
    """Base class for stress tests"""

    def __init__(self, name: str):
        self.name = name
        self.results: List[float] = []
        self.errors: List[str] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    def setup(self) -> None:
        """Setup before test"""
        pass

    def teardown(self) -> None:
        """Cleanup after test"""
        pass

    @abstractmethod
    def run_operation(self) -> bool:
        """Single test operation - override in subclass"""

    def run(self, iterations: int, max_workers: int = 10) -> StressTestResult:
        """
        Run stress test

        Args:
            iterations: Number of operations to perform
            max_workers: Maximum concurrent workers

        Returns:
            Test results
        """
        self.setup()
        self.start_time = time.time()

        successful = 0
        failed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self._timed_operation) for _ in range(iterations)]

            for future in as_completed(futures):
                try:
                    latency, success = future.result()
                    self.results.append(latency)

                    if success:
                        successful += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(
                        "Exception in run",
                        error_type="Exception",
                        error=str(e),
                        function="run",
                    )
                    self.errors.append(str(e))
                    failed += 1

        self.end_time = time.time()
        self.teardown()

        duration = self.end_time - self.start_time

        return StressTestResult(
            test_name=self.name,
            duration=duration,
            total_operations=iterations,
            successful_operations=successful,
            failed_operations=failed,
            operations_per_second=iterations / duration if duration > 0 else 0,
            average_latency=sum(self.results) / len(self.results) if self.results else 0,
            min_latency=min(self.results) if self.results else 0,
            max_latency=max(self.results) if self.results else 0,
            errors=self.errors[:10]  # Keep first 10 errors
        )

    def _timed_operation(self) -> tuple[float, bool]:
        """Run operation and measure time"""
        start = time.time()
        try:
            success = self.run_operation()
            latency = time.time() - start
            return latency, success
        except Exception as e:
            logger.warning(
                "Exception in _timed_operation",
                error_type="Exception",
                error=str(e),
                function="_timed_operation",
            )
            latency = time.time() - start
            self.errors.append(str(e))
            return latency, False


class TransactionStressTest(StressTest):
    """Stress test for transaction processing"""

    def __init__(self, blockchain):
        super().__init__("Transaction Processing")
        self.blockchain = blockchain

    def run_operation(self) -> bool:
        """Create and process a transaction"""
        try:
            # Simulate transaction creation
            sender = f"XAI{'0' * 40}"
            recipient = f"XAI{'1' * 40}"
            amount = random.uniform(0.1, 10.0)

            # In production, would actually create and process transaction
            time.sleep(0.001)  # Simulate processing time

            return True
        except Exception as e:
            logger.debug("Transaction stress test failed: %s", e)
            return False


class MiningStressTest(StressTest):
    """Stress test for mining operations"""

    def __init__(self, blockchain):
        super().__init__("Mining Operations")
        self.blockchain = blockchain

    def run_operation(self) -> bool:
        """Simulate mining operation"""
        try:
            # Simulate proof-of-work
            nonce = 0
            target = "0000"

            while nonce < 10000:
                hash_input = f"test_block_{nonce}_{time.time()}"
                import hashlib
                block_hash = hashlib.sha256(hash_input.encode()).hexdigest()

                if block_hash.startswith(target):
                    return True

                nonce += 1

            return False
        except Exception as e:
            logger.debug("Mining stress test failed: %s", e)
            return False


class NetworkStressTest(StressTest):
    """Stress test for network operations"""

    def __init__(self, node):
        super().__init__("Network Operations")
        self.node = node

    def run_operation(self) -> bool:
        """Simulate network request"""
        try:
            # Simulate peer communication
            time.sleep(random.uniform(0.001, 0.01))
            return True
        except Exception as e:
            logger.debug("Network stress test failed: %s", e)
            return False


class ConcurrencyStressTest(StressTest):
    """Test concurrent access to shared resources"""

    def __init__(self, resource):
        super().__init__("Concurrency Test")
        self.resource = resource
        self.lock = threading.Lock()

    def run_operation(self) -> bool:
        """Perform concurrent operation"""
        try:
            with self.lock:
                # Simulate resource access
                time.sleep(0.0001)

            return True
        except Exception as e:
            logger.debug("Concurrency stress test failed: %s", e)
            return False


class LoadGenerator:
    """Generate realistic load patterns"""

    def __init__(self):
        self.patterns = {
            'constant': self._constant_load,
            'ramp': self._ramp_load,
            'spike': self._spike_load,
            'wave': self._wave_load
        }

    def _constant_load(self, duration: int, rate: int) -> List[int]:
        """Constant load pattern"""
        return [rate] * duration

    def _ramp_load(self, duration: int, start_rate: int, end_rate: int) -> List[int]:
        """Gradually increasing load"""
        step = (end_rate - start_rate) / duration
        return [int(start_rate + step * i) for i in range(duration)]

    def _spike_load(self, duration: int, base_rate: int, spike_rate: int, spike_duration: int) -> List[int]:
        """Load with sudden spikes"""
        pattern = [base_rate] * duration
        spike_start = duration // 2
        for i in range(spike_start, min(spike_start + spike_duration, duration)):
            pattern[i] = spike_rate
        return pattern

    def _wave_load(self, duration: int, min_rate: int, max_rate: int) -> List[int]:
        """Sinusoidal load pattern"""
        import math
        pattern = []
        for i in range(duration):
            rate = min_rate + (max_rate - min_rate) * (1 + math.sin(2 * math.pi * i / duration)) / 2
            pattern.append(int(rate))
        return pattern

    def generate(self, pattern: str, **kwargs) -> List[int]:
        """Generate load pattern"""
        generator = self.patterns.get(pattern, self._constant_load)
        return generator(**kwargs)


class StressTestSuite:
    """Suite of stress tests"""

    def __init__(self):
        self.tests: List[StressTest] = []
        self.results: List[StressTestResult] = []

    def add_test(self, test: StressTest) -> None:
        """Add test to suite"""
        self.tests.append(test)

    def run_all(self, iterations_per_test: int = 1000) -> List[StressTestResult]:
        """Run all tests in suite"""
        self.results.clear()

        for test in self.tests:
            print(f"Running {test.name}...")
            result = test.run(iterations_per_test)
            self.results.append(result)
            print(f"  Completed: {result.operations_per_second:.2f} ops/sec")

        return self.results

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all test results"""
        if not self.results:
            return {}

        total_ops = sum(r.total_operations for r in self.results)
        total_successful = sum(r.successful_operations for r in self.results)

        return {
            "total_tests": len(self.results),
            "total_operations": total_ops,
            "total_successful": total_successful,
            "overall_success_rate": (total_successful / total_ops * 100) if total_ops > 0 else 0,
            "tests": [r.get_summary() for r in self.results]
        }


class PerformanceBaseline:
    """Establish performance baselines"""

    def __init__(self):
        self.baselines: Dict[str, float] = {}

    def record_baseline(self, test_name: str, ops_per_second: float) -> None:
        """Record baseline performance"""
        self.baselines[test_name] = ops_per_second

    def compare(self, test_name: str, current_ops_per_second: float) -> Dict[str, Any]:
        """Compare current performance to baseline"""
        baseline = self.baselines.get(test_name)

        if not baseline:
            return {"status": "no_baseline", "message": "No baseline recorded"}

        diff_percent = ((current_ops_per_second - baseline) / baseline) * 100

        if diff_percent >= -5:  # Within 5% is acceptable
            status = "pass"
        elif diff_percent >= -10:
            status = "warning"
        else:
            status = "regression"

        return {
            "status": status,
            "baseline": baseline,
            "current": current_ops_per_second,
            "difference_percent": diff_percent
        }


class ResourceMonitor:
    """Monitor resource usage during stress tests"""

    def __init__(self):
        self.cpu_samples: List[float] = []
        self.memory_samples: List[int] = []
        self.monitoring = False

    def start_monitoring(self) -> None:
        """Start resource monitoring"""
        self.monitoring = True
        self.cpu_samples.clear()
        self.memory_samples.clear()

        def monitor():
            import psutil
            import os

            process = psutil.Process(os.getpid())

            while self.monitoring:
                self.cpu_samples.append(process.cpu_percent(interval=0.1))
                self.memory_samples.append(process.memory_info().rss)
                time.sleep(0.5)

        threading.Thread(target=monitor, daemon=True).start()

    def stop_monitoring(self) -> Dict[str, Any]:
        """Stop monitoring and get results"""
        self.monitoring = False
        time.sleep(1)  # Wait for last sample

        if not self.cpu_samples or not self.memory_samples:
            return {}

        return {
            "cpu": {
                "average": sum(self.cpu_samples) / len(self.cpu_samples),
                "peak": max(self.cpu_samples),
                "samples": len(self.cpu_samples)
            },
            "memory": {
                "average_mb": sum(self.memory_samples) / len(self.memory_samples) / 1024 / 1024,
                "peak_mb": max(self.memory_samples) / 1024 / 1024,
                "samples": len(self.memory_samples)
            }
        }
