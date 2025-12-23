"""
Memory and CPU Profiling Tools
Task 269: Complete memory profiling tools
Task 270: Implement CPU profiling for optimization

Comprehensive profiling tools for performance optimization.
"""

from __future__ import annotations

import cProfile
import io
import linecache
import os
import pstats
import time
import tracemalloc
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable


@dataclass
class MemorySnapshot:
    """Memory snapshot at a point in time"""
    timestamp: float
    current_mb: float
    peak_mb: float
    top_allocations: list[tuple]

class MemoryProfiler:
    """
    Memory profiling tools (Task 269)

    Track memory usage and identify memory leaks
    """

    def __init__(self):
        self.is_profiling = False
        self.snapshots: list[MemorySnapshot] = []
        self.start_snapshot: Any | None = None

    def start(self) -> None:
        """Start memory profiling"""
        tracemalloc.start()
        self.is_profiling = True
        self.snapshots.clear()
        self.start_snapshot = tracemalloc.take_snapshot()

    def stop(self) -> None:
        """Stop memory profiling"""
        if self.is_profiling:
            tracemalloc.stop()
            self.is_profiling = False

    def take_snapshot(self, top_n: int = 10) -> MemorySnapshot:
        """
        Take memory snapshot

        Args:
            top_n: Number of top allocations to record

        Returns:
            Memory snapshot
        """
        if not self.is_profiling:
            raise RuntimeError("Profiler not started")

        current, peak = tracemalloc.get_traced_memory()
        snapshot = tracemalloc.take_snapshot()

        # Get top allocations
        top_stats = snapshot.statistics('lineno')[:top_n]
        top_allocations = [
            (str(stat), stat.size / 1024 / 1024)  # Convert to MB
            for stat in top_stats
        ]

        memory_snapshot = MemorySnapshot(
            timestamp=time.time(),
            current_mb=current / 1024 / 1024,
            peak_mb=peak / 1024 / 1024,
            top_allocations=top_allocations
        )

        self.snapshots.append(memory_snapshot)
        return memory_snapshot

    def compare_snapshots(self, snapshot1_idx: int = 0, snapshot2_idx: int = -1) -> list[str]:
        """
        Compare two snapshots to find memory growth

        Args:
            snapshot1_idx: Index of first snapshot
            snapshot2_idx: Index of second snapshot

        Returns:
            List of differences
        """
        if len(self.snapshots) < 2:
            return ["Need at least 2 snapshots to compare"]

        snap1 = self.snapshots[snapshot1_idx]
        snap2 = self.snapshots[snapshot2_idx]

        differences = [
            f"Memory growth: {snap2.current_mb - snap1.current_mb:.2f} MB",
            f"Time elapsed: {snap2.timestamp - snap1.timestamp:.2f} seconds",
            f"\nCurrent memory:",
            f"  Snapshot 1: {snap1.current_mb:.2f} MB",
            f"  Snapshot 2: {snap2.current_mb:.2f} MB",
            f"\nPeak memory:",
            f"  Snapshot 1: {snap1.peak_mb:.2f} MB",
            f"  Snapshot 2: {snap2.peak_mb:.2f} MB"
        ]

        return differences

    def get_memory_stats(self) -> dict[str, Any]:
        """Get current memory statistics"""
        if not self.is_profiling:
            return {"error": "Profiler not running"}

        current, peak = tracemalloc.get_traced_memory()

        return {
            "current_mb": current / 1024 / 1024,
            "peak_mb": peak / 1024 / 1024,
            "snapshot_count": len(self.snapshots)
        }

    def find_memory_leaks(self, threshold_mb: float = 1.0) -> list[str]:
        """
        Analyze snapshots to find potential memory leaks

        Args:
            threshold_mb: Minimum growth to consider a leak (MB)

        Returns:
            List of potential leaks
        """
        if len(self.snapshots) < 3:
            return ["Need at least 3 snapshots to detect leaks"]

        leaks = []

        # Check for consistent memory growth
        for i in range(len(self.snapshots) - 1):
            growth = self.snapshots[i + 1].current_mb - self.snapshots[i].current_mb

            if growth > threshold_mb:
                leaks.append(
                    f"Memory leak detected between snapshot {i} and {i+1}: "
                    f"+{growth:.2f} MB"
                )

        return leaks if leaks else ["No significant memory leaks detected"]

class CPUProfiler:
    """
    CPU profiling tools (Task 270)

    Identify performance bottlenecks and hot spots
    """

    def __init__(self):
        self.profiler: cProfile.Profile | None = None
        self.is_profiling = False

    def start(self) -> None:
        """Start CPU profiling"""
        self.profiler = cProfile.Profile()
        self.profiler.enable()
        self.is_profiling = True

    def stop(self) -> None:
        """Stop CPU profiling"""
        if self.profiler and self.is_profiling:
            self.profiler.disable()
            self.is_profiling = False

    def get_stats(self, sort_by: str = 'cumulative', top_n: int = 20) -> str:
        """
        Get profiling statistics

        Args:
            sort_by: Sort key ('cumulative', 'time', 'calls')
            top_n: Number of top functions to show

        Returns:
            Formatted statistics string
        """
        if not self.profiler:
            return "No profiling data available"

        stream = io.StringIO()
        stats = pstats.Stats(self.profiler, stream=stream)
        stats.strip_dirs()
        stats.sort_stats(sort_by)
        stats.print_stats(top_n)

        return stream.getvalue()

    def save_stats(self, filename: str) -> None:
        """Save profiling stats to file"""
        if self.profiler:
            self.profiler.dump_stats(filename)

    def get_hotspots(self, top_n: int = 10) -> list[dict[str, Any]]:
        """
        Get CPU hotspots (most time-consuming functions)

        Args:
            top_n: Number of hotspots to return

        Returns:
            List of hotspot information
        """
        if not self.profiler:
            return []

        stats = pstats.Stats(self.profiler)
        stats.strip_dirs()
        stats.sort_stats('cumulative')

        hotspots = []

        # Get top functions
        for func, (cc, nc, tt, ct, callers) in list(stats.stats.items())[:top_n]:
            filename, line, func_name = func

            hotspots.append({
                "function": func_name,
                "file": filename,
                "line": line,
                "calls": nc,
                "total_time": tt,
                "cumulative_time": ct,
                "time_per_call": tt / nc if nc > 0 else 0
            })

        return hotspots

def profile_memory(func: Callable) -> Callable:
    """
    Decorator to profile memory usage of a function

    Usage:
        @profile_memory
        def my_function():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        profiler = MemoryProfiler()
        profiler.start()

        result = func(*args, **kwargs)

        snapshot = profiler.take_snapshot()
        profiler.stop()

        print(f"\nMemory Profile for {func.__name__}:")
        print(f"  Current: {snapshot.current_mb:.2f} MB")
        print(f"  Peak: {snapshot.peak_mb:.2f} MB")
        print(f"\nTop 5 Allocations:")
        for i, (stat, size_mb) in enumerate(snapshot.top_allocations[:5], 1):
            print(f"  {i}. {size_mb:.2f} MB - {stat}")

        return result

    return wrapper

def profile_cpu(func: Callable) -> Callable:
    """
    Decorator to profile CPU usage of a function

    Usage:
        @profile_cpu
        def my_function():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        profiler = CPUProfiler()
        profiler.start()

        result = func(*args, **kwargs)

        profiler.stop()

        print(f"\nCPU Profile for {func.__name__}:")
        print(profiler.get_stats(top_n=10))

        return result

    return wrapper

class PerformanceMonitor:
    """
    Real-time performance monitoring

    Combines CPU and memory monitoring
    """

    def __init__(self):
        self.memory_profiler = MemoryProfiler()
        self.cpu_profiler = CPUProfiler()
        self.monitoring = False

    def start(self) -> None:
        """Start monitoring"""
        self.memory_profiler.start()
        self.cpu_profiler.start()
        self.monitoring = True

    def stop(self) -> dict[str, Any]:
        """Stop monitoring and get results"""
        if not self.monitoring:
            return {}

        self.memory_profiler.stop()
        self.cpu_profiler.stop()
        self.monitoring = False

        memory_snapshot = self.memory_profiler.snapshots[-1] if self.memory_profiler.snapshots else None

        return {
            "memory": {
                "current_mb": memory_snapshot.current_mb if memory_snapshot else 0,
                "peak_mb": memory_snapshot.peak_mb if memory_snapshot else 0
            },
            "cpu_hotspots": self.cpu_profiler.get_hotspots(top_n=5)
        }

class ResourceTracker:
    """Track resource usage over time"""

    def __init__(self):
        self.samples: list[dict[str, Any]] = []
        self.tracking = False

    def start_tracking(self, interval: float = 1.0) -> None:
        """
        Start tracking resource usage

        Args:
            interval: Sampling interval in seconds
        """
        import os
        import threading

        import psutil

        self.tracking = True
        self.samples.clear()

        def track():
            process = psutil.Process(os.getpid())

            while self.tracking:
                sample = {
                    "timestamp": time.time(),
                    "cpu_percent": process.cpu_percent(interval=0.1),
                    "memory_mb": process.memory_info().rss / 1024 / 1024,
                    "threads": process.num_threads(),
                }
                self.samples.append(sample)
                time.sleep(interval)

        threading.Thread(target=track, daemon=True).start()

    def stop_tracking(self) -> dict[str, Any]:
        """Stop tracking and get summary"""
        self.tracking = False
        time.sleep(1)  # Wait for last sample

        if not self.samples:
            return {}

        cpu_values = [s["cpu_percent"] for s in self.samples]
        memory_values = [s["memory_mb"] for s in self.samples]

        return {
            "duration_seconds": self.samples[-1]["timestamp"] - self.samples[0]["timestamp"],
            "sample_count": len(self.samples),
            "cpu": {
                "average": sum(cpu_values) / len(cpu_values),
                "peak": max(cpu_values),
                "min": min(cpu_values)
            },
            "memory": {
                "average_mb": sum(memory_values) / len(memory_values),
                "peak_mb": max(memory_values),
                "min_mb": min(memory_values)
            }
        }

    def export_samples(self, filename: str) -> None:
        """Export samples to JSON file"""
        import json

        with open(filename, 'w') as f:
            json.dump(self.samples, f, indent=2)

class ProfilingReport:
    """Generate comprehensive profiling report"""

    def __init__(self):
        self.sections: dict[str, Any] = {}

    def add_memory_profile(self, profiler: MemoryProfiler) -> None:
        """Add memory profiling results"""
        stats = profiler.get_memory_stats()
        self.sections["memory"] = stats

    def add_cpu_profile(self, profiler: CPUProfiler) -> None:
        """Add CPU profiling results"""
        hotspots = profiler.get_hotspots()
        self.sections["cpu"] = {"hotspots": hotspots}

    def add_custom_section(self, name: str, data: dict[str, Any]) -> None:
        """Add custom section to report"""
        self.sections[name] = data

    def generate_report(self) -> str:
        """Generate formatted report"""
        report = ["=" * 60]
        report.append("PERFORMANCE PROFILING REPORT")
        report.append("=" * 60)

        if "memory" in self.sections:
            report.append("\nMEMORY PROFILE:")
            mem = self.sections["memory"]
            report.append(f"  Current: {mem.get('current_mb', 0):.2f} MB")
            report.append(f"  Peak: {mem.get('peak_mb', 0):.2f} MB")

        if "cpu" in self.sections:
            report.append("\nCPU HOTSPOTS:")
            for i, hotspot in enumerate(self.sections["cpu"]["hotspots"][:5], 1):
                report.append(f"  {i}. {hotspot['function']} - {hotspot['cumulative_time']:.3f}s")

        for name, data in self.sections.items():
            if name not in ["memory", "cpu"]:
                report.append(f"\n{name.upper()}:")
                report.append(f"  {data}")

        report.append("\n" + "=" * 60)

        return "\n".join(report)

    def save_report(self, filename: str) -> None:
        """Save report to file"""
        with open(filename, 'w') as f:
            f.write(self.generate_report())
