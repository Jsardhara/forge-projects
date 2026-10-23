"""Coverage driver: exercise cli.main in-process across pass/fail/error paths."""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
sys.path.insert(0, os.path.join(HERE, "tests"))

from pubgate.cli import main  # noqa: E402
from test_pubgate import make_source, make_wheel  # noqa: E402

td = tempfile.mkdtemp()
src = make_source(os.path.join(td, "s"), {"src/demo/core.py": "x = 1\n"})
man = os.path.join(td, "m.json")
whl = make_wheel(os.path.join(td, "demo-1.0.0-py3-none-any.whl"), {"demo/core.py": b"x = 1\n"})

main(["record", "--source", src, "--name", "demo", "--version", "1.0.0", "--out", man])
main(["verify", "--wheel", whl, "--manifest", man])            # PASS path
main(["verify", "--wheel", whl])                              # SOURCE SKIPPED path
main(["verify", "--wheel", whl, "--manifest", os.path.join(td, "nope.json")])  # error path
main(["record", "--source", "/nope/not/here", "--out", man])  # error path
