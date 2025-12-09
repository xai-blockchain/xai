# Network Protocol (Placeholder)

This should describe P2P handshakes, inventory/getdata, partial/checkpoint sync, subnet/ASN diversity, bandwidth limits, and reset-storm handling.

For now, see:
- `docs/api/p2p_handshake.md`, `docs/api/p2p_versions.md`
- Code in `src/xai/core/node_p2p.py`, `p2p_quic.py`, `network_security.py`
- Tests in `tests/xai_tests/unit/test_gossip_validator.py`, `test_packet_filter.py`, `test_partition_detector.py`, `test_eclipse_protector.py`.***
