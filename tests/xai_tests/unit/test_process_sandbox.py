import json
import os
import subprocess
import sys


def _pythonpath_env():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    src_path = os.path.join(repo_root, "src")
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{src_path}{os.pathsep}{env.get('PYTHONPATH', '')}"
    return env


def test_process_sandbox_disabled_when_env_not_set(monkeypatch):
    env = _pythonpath_env()
    env.pop("XAI_ENABLE_PROCESS_SANDBOX", None)
    script = "from xai.core.process_sandbox import maybe_enable_process_sandbox; print(maybe_enable_process_sandbox())"
    result = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True, check=True)
    assert result.stdout.strip() in {"False", "{}", ""}  # {} on non-posix


def test_process_sandbox_applies_limits_in_subprocess():
    env = _pythonpath_env()
    env.update(
        {
            "XAI_ENABLE_PROCESS_SANDBOX": "true",
            "XAI_SANDBOX_MAX_MEM_MB": "64",
            "XAI_SANDBOX_MAX_CPU_SECONDS": "120",
            "XAI_SANDBOX_MAX_OPEN_FILES": "256",
        }
    )
    script = """
import json
import os
try:
    import resource
except ImportError:
    resource = None

from xai.core.process_sandbox import maybe_enable_process_sandbox

res = maybe_enable_process_sandbox()
limits = {}
if os.name == "posix" and resource:
    limits = {
        "as": resource.getrlimit(resource.RLIMIT_AS)[0],
        "cpu": resource.getrlimit(resource.RLIMIT_CPU)[0],
        "nofile": resource.getrlimit(resource.RLIMIT_NOFILE)[0],
    }
print(json.dumps({"res": res, "limits": limits, "os": os.name}))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout.strip())
    if os.name != "posix":
        assert data["res"] in (False, {})
        assert data["limits"] == {}
    else:
        assert data["res"] is not False
        # Ensure limits are at or below requested thresholds (allow small slack)
        assert data["limits"]["as"] <= 64 * 1024 * 1024
        assert data["limits"]["cpu"] <= 120
        assert data["limits"]["nofile"] <= 256
