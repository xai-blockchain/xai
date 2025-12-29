import os

from xai.core.chain.blockchain_persistence import BlockchainStorage
from xai.core.api.monitoring import MetricsCollector


def _get_metric_value(collector: MetricsCollector, name: str) -> float:
    metric = collector.get_metric(name)
    return metric.value if metric else 0.0


def test_blockchain_storage_records_performance_metrics(tmp_path):
    collector = MetricsCollector.instance(update_interval=120)
    storage = BlockchainStorage(data_dir=str(tmp_path))

    write_counter_before = _get_metric_value(collector, "xai_storage_writes_total")
    write_histogram = collector.get_metric("xai_storage_write_latency_seconds")
    write_hist_count_before = write_histogram.count if write_histogram else 0
    bytes_written_before = _get_metric_value(collector, "xai_storage_bytes_written_total")

    data = {"chain": [{"index": 1, "data": "genesis"}]}
    success, _ = storage.save_to_disk(data, create_backup=False)
    assert success is True

    write_counter_after = _get_metric_value(collector, "xai_storage_writes_total")
    assert write_counter_after == write_counter_before + 1

    write_hist_count_after = (
        collector.get_metric("xai_storage_write_latency_seconds").count
        if collector.get_metric("xai_storage_write_latency_seconds")
        else 0
    )
    assert write_hist_count_after == write_hist_count_before + 1

    bytes_written_after = _get_metric_value(collector, "xai_storage_bytes_written_total")
    assert bytes_written_after > bytes_written_before

    data_dir_gauge = _get_metric_value(collector, "xai_storage_data_dir_bytes")
    assert data_dir_gauge >= os.path.getsize(storage.blockchain_file)

    read_counter_before = _get_metric_value(collector, "xai_storage_reads_total")
    read_histogram = collector.get_metric("xai_storage_read_latency_seconds")
    read_hist_count_before = read_histogram.count if read_histogram else 0
    bytes_read_before = _get_metric_value(collector, "xai_storage_bytes_read_total")

    loaded, blockchain_data, _ = storage.load_from_disk()
    assert loaded is True
    assert blockchain_data["chain"][0]["index"] == 1

    read_counter_after = _get_metric_value(collector, "xai_storage_reads_total")
    assert read_counter_after == read_counter_before + 1

    read_hist_count_after = (
        collector.get_metric("xai_storage_read_latency_seconds").count
        if collector.get_metric("xai_storage_read_latency_seconds")
        else 0
    )
    assert read_hist_count_after == read_hist_count_before + 1

    bytes_read_after = _get_metric_value(collector, "xai_storage_bytes_read_total")
    assert bytes_read_after > bytes_read_before
