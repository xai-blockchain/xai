"""
Node identity management for P2P authentication.

Generates and persists a secp256k1 keypair per node under the data directory.
Exposes helpers to load/create identity and access public/private keys in hex.
"""

from __future__ import annotations

import json
import os
import stat
import logging
from typing import Dict, Tuple

from xai.core.crypto_utils import (
    generate_secp256k1_keypair_hex,
    derive_public_key_hex,
)


IDENTITY_FILENAME = "node_identity.json"


def _identity_path(data_dir: str) -> str:
    return os.path.join(data_dir, IDENTITY_FILENAME)


def load_or_create_identity(data_dir: str) -> Dict[str, str]:
    """Load an existing node identity or create a new one.

    The identity file contains:
    { "private_key": <hex>, "public_key": <hex>, "version": 1 }
    """
    os.makedirs(data_dir, exist_ok=True)
    path = _identity_path(data_dir)

    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Ensure public key matches private key
        priv = data.get("private_key", "")
        pub = data.get("public_key", "")
        if not priv or not pub or derive_public_key_hex(priv) != pub:
            # Re-derive public if missing/mismatched
            data["public_key"] = derive_public_key_hex(priv)
            _atomic_write_json(path, data)
        return data

    private_hex, public_hex = generate_secp256k1_keypair_hex()
    identity = {"private_key": private_hex, "public_key": public_hex, "version": 1}
    _atomic_write_json(path, identity)

    # Restrict file permissions (owner read/write)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError as exc:
        logger.warning(
            "Failed to set restrictive permissions on %s: %s",
            path,
            exc,
            extra={"event": "node_identity.chmod_failed", "path": path},
        )

    return identity


def _atomic_write_json(path: str, payload: Dict) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
logger = logging.getLogger(__name__)

