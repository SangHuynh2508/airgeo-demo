from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_package_version():
    import airgeo
    assert airgeo.__version__ == "0.2.0"


def test_requirements_txt_matches_pyproject_pins():
    # requirements.txt giữ lại cho người đọc/cài kiểu cũ; 2 nơi phải ghim cùng phiên bản
    tomllib = pytest.importorskip("tomllib")
    deps = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["dependencies"]
    req = [line.strip() for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
           if line.strip() and not line.lstrip().startswith("#")]
    assert sorted(req) == sorted(deps)
