"""
Unit tests for module attachment guard.
"""

import os
import sys
from pathlib import Path

import pytest

from xai.security.module_attachment_guard import ModuleAttachmentError, ModuleAttachmentGuard


def test_allowlisted_repo_module_passes():
    guard = ModuleAttachmentGuard({"xai.core.api_mining"}, require_attribute="ATTACHMENT_SAFE")
    guard.verify_module("xai.core.api_mining")  # Should not raise


def test_non_allowlisted_module_rejected():
    guard = ModuleAttachmentGuard({"xai.core.api_mining"})
    with pytest.raises(ModuleAttachmentError):
        guard.verify_module("json")


def test_untrusted_path_rejected(tmp_path, monkeypatch):
    module_path = tmp_path / "evilmod.py"
    module_path.write_text("ATTACHMENT_SAFE = True\n")
    sys.path.insert(0, str(tmp_path))
    try:
        guard = ModuleAttachmentGuard(
            {"evilmod"},
            trusted_base=Path(__file__).resolve().parents[3],
            require_attribute="ATTACHMENT_SAFE",
        )
        with pytest.raises(ModuleAttachmentError):
            guard.verify_module("evilmod")
    finally:
        sys.path.pop(0)
        sys.modules.pop("evilmod", None)


def test_missing_attribute_rejected(tmp_path, monkeypatch):
    module_path = tmp_path / "tempmod.py"
    module_path.write_text("# no attachment flag\n")
    sys.path.insert(0, str(tmp_path))
    try:
        guard = ModuleAttachmentGuard(
            {"tempmod"},
            trusted_base=tmp_path,
            require_attribute="ATTACHMENT_SAFE",
        )
        with pytest.raises(ModuleAttachmentError):
            guard.verify_module("tempmod")
    finally:
        sys.path.pop(0)
        sys.modules.pop("tempmod", None)


def test_world_writable_module_rejected(tmp_path):
    module_path = tmp_path / "wwmod.py"
    module_path.write_text("ATTACHMENT_SAFE = True\n")
    os.chmod(module_path, 0o666)
    sys.path.insert(0, str(tmp_path))
    try:
        guard = ModuleAttachmentGuard(
            {"wwmod"},
            trusted_base=tmp_path,
            require_attribute="ATTACHMENT_SAFE",
        )
        with pytest.raises(ModuleAttachmentError):
            guard.verify_module("wwmod")
    finally:
        sys.path.pop(0)
        sys.modules.pop("wwmod", None)


def test_symlink_module_rejected(tmp_path):
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    target_mod = target_dir / "targetmod.py"
    target_mod.write_text("ATTACHMENT_SAFE = True\n")

    link_dir = tmp_path / "link"
    link_dir.mkdir()
    symlink_path = link_dir / "symlinkmod.py"
    symlink_path.symlink_to(target_mod)

    sys.path.insert(0, str(link_dir))
    try:
        guard = ModuleAttachmentGuard(
            {"symlinkmod"},
            trusted_base=target_dir,
            require_attribute="ATTACHMENT_SAFE",
        )
        with pytest.raises(ModuleAttachmentError):
            guard.verify_module("symlinkmod")
    finally:
        sys.path.pop(0)
        sys.modules.pop("symlinkmod", None)


def test_world_writable_parent_rejected(tmp_path):
    mod_dir = tmp_path / "wwdir"
    mod_dir.mkdir()
    mod_dir.chmod(0o777)
    module_path = mod_dir / "mod.py"
    module_path.write_text("ATTACHMENT_SAFE = True\n")
    sys.path.insert(0, str(mod_dir))
    try:
        guard = ModuleAttachmentGuard(
            {"mod"},
            trusted_base=mod_dir,
            require_attribute="ATTACHMENT_SAFE",
        )
        with pytest.raises(ModuleAttachmentError):
            guard.verify_module("mod")
    finally:
        sys.path.pop(0)
        sys.modules.pop("mod", None)


def test_stdlib_module_allowed_with_trusted_stdlib(tmp_path):
    guard = ModuleAttachmentGuard(
        {"json"},
        trusted_base=tmp_path,
        require_attribute=None,
    )
    # Should not raise for stdlib module
    guard.verify_module("json")
