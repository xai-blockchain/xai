import tempfile
from pathlib import Path

from scripts.tools.trust_store_rotate import main as rotate_main


def write_temp(contents: str) -> Path:
    path = Path(tempfile.mkstemp()[1])
    path.write_text(contents)
    return path


def test_trust_store_rotate_merges_and_drops():
    current_pub = write_temp("pub1\npub2\n")
    current_cert = write_temp("cert1\ncert2\n")
    new_pub = write_temp("pub2\npub3\n")
    new_cert = write_temp("cert2\ncert3\n")

    out_pub = Path(tempfile.mkstemp()[1])
    out_cert = Path(tempfile.mkstemp()[1])

    # Merge without drop
    rotate_main(
        [
            "--current-pubkeys",
            str(current_pub),
            "--current-certs",
            str(current_cert),
            "--new-pubkeys",
            str(new_pub),
            "--new-certs",
            str(new_cert),
            "--out-pubkeys",
            str(out_pub),
            "--out-certs",
            str(out_cert),
        ]
    )
    merged_pub = set(out_pub.read_text().splitlines())
    merged_cert = set(out_cert.read_text().splitlines())
    assert "pub1" in "\n".join(merged_pub)
    assert "pub3" in "\n".join(merged_pub)
    assert "cert1" in "\n".join(merged_cert)
    assert "cert3" in "\n".join(merged_cert)

    # Drop old entries
    rotate_main(
        [
            "--current-pubkeys",
            str(current_pub),
            "--current-certs",
            str(current_cert),
            "--new-pubkeys",
            str(new_pub),
            "--new-certs",
            str(new_cert),
            "--drop-old",
            "--out-pubkeys",
            str(out_pub),
            "--out-certs",
            str(out_cert),
        ]
    )
    dropped_pub = out_pub.read_text()
    dropped_cert = out_cert.read_text()
    assert "pub1" not in dropped_pub
    assert "cert1" not in dropped_cert
    assert "pub3" in dropped_pub
    assert "cert3" in dropped_cert
