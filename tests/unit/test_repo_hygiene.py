"""Guards against leaking the SH3 work git identity into this public repository."""

import subprocess
from pathlib import Path

PERSONAL_EMAIL = "saracristina@gmail.com"
REPO_ROOT = Path(__file__).resolve().parents[2]


def _git_local_config(key: str) -> str:
    result = subprocess.run(
        ["git", "config", "--local", "--get", key],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _git_check_ignore(relative_path: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", relative_path],
        cwd=REPO_ROOT,
    )
    return result.returncode == 0


def test_local_git_email_is_personal_not_work():
    email = _git_local_config("user.email")
    assert "sh3" not in email.lower()
    assert email == PERSONAL_EMAIL


def test_gitignore_covers_python_essentials_and_model_cache():
    paths_expected_ignored = [
        ".venv/lib/python3.12/site-packages/foo.py",
        "src/rag/__pycache__/module.cpython-312.pyc",
        ".env",
        ".cache/huggingface/models--intfloat--multilingual-e5-base/model.safetensors",
    ]
    for path in paths_expected_ignored:
        assert _git_check_ignore(path), f"{path} should be ignored by .gitignore"
