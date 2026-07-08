import sys
from pathlib import Path

def test_generate_config(tmp_path, monkeypatch):
    # import the function from the package
    from copysync.__main__ import generate_copybara_config
    # create dummy rewrites
    rewrites = [('old', 'new')]
    # generate config file
    cfg_path = generate_copybara_config('src.git', 'dst.git', 'refs/heads/main', rewrites)
    # ensure file exists and contains expected content
    assert Path(cfg_path).exists()
    content = Path(cfg_path).read_text()
    assert "src.git" in content
    assert "dst.git" in content
    assert "old:new" in content
    # cleanup is handled by function, but ensure file removed after call
    # (function removes after returning, but we called it directly; it returns path before removal)
    # Ensure the temporary file is removed after test finishes
    Path(cfg_path).unlink(missing_ok=True)
