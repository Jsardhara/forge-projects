"""Entry point for the copysync CLI.

Usage:
    copysync --src <source-repo> --dst <dest-repo> [--branch <branch>] [--rewrite <old:new> ...]

The tool generates a minimal Copybara configuration on the fly and invokes the
Copybara binary (Java JAR). It requires the Copybara JAR to be available via the
environment variable ``COPYBARA_JAR`` or at ``/usr/local/bin/copybara.jar``.

If the JAR is not found, the command exits with a non‑zero status and prints an
informative error message.
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

def generate_copybara_config(src: str, dst: str, branch: str | None, rewrites: list[tuple[str, str]]) -> str:
    """Return a temporary file path containing a minimal Copybara config.

    The config performs a simple `git.origin` -> `git.destination` migration with
    optional path rewrites. ``rewrites`` is a list of (old, new) strings that are
    applied via a ``sky.transformation`` step using Copybara's ``replace``
    expression.
    """
    config_lines = [
        "core.workflow('default')", "",
        "origin = git.origin(",
        f"    url = '{src}',",
        "    ref = 'refs/heads/master',",
        ")",
        "",
        "destination = git.destination(",
        f"    url = '{dst}',",
        "    push = 'FORCE',",
        ")",
        "",
        "transformation = core.transformation(",
        "    core.replace(['" + ", ".join([f"{old}:{new}" for old, new in rewrites]) + "'])",
        ")",
        "",
        "core.copy(",
        "    origin = origin,",
        "    destination = destination,",
        "    transformations = [transformation]",
        f"    origin_ref = '{branch}' if branch else 'refs/heads/master'",
        ")",
    ]
    fd, path = tempfile.mkstemp(suffix='.java', prefix='copybara_config_')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write('\n'.join(config_lines))
    return path

def locate_copybara_jar() -> str:
    """Return path to copybara JAR or raise FileNotFoundError."""
    env_path = os.getenv('COPYBARA_JAR')
    candidates = []
    if env_path:
        candidates.append(env_path)
    candidates.append('/usr/local/bin/copybara.jar')
    for p in candidates:
        if Path(p).is_file():
            return p
    raise FileNotFoundError('Copybara JAR not found. Set $COPYBARA_JAR or place at /usr/local/bin/copybara.jar')

def main() -> None:
    parser = argparse.ArgumentParser(prog='copysync', description='Lightweight wrapper for Google Copybara')
    parser.add_argument('--src', required=True, help='Source Git repository URL')
    parser.add_argument('--dst', required=True, help='Destination Git repository URL')
    parser.add_argument('--branch', help='Branch to sync (default: master)')
    parser.add_argument('--rewrite', action='append', default=[], help='Path rewrite in old:new form; can be repeated')
    args = parser.parse_args()

    rewrites = []
    for rw in args.rewrite:
        if ':' not in rw:
            print(f'Invalid rewrite spec "{rw}" – expected old:new', file=sys.stderr)
            sys.exit(2)
        old, new = rw.split(':', 1)
        rewrites.append((old, new))

    try:
        jar_path = locate_copybara_jar()
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    config_path = generate_copybara_config(args.src, args.dst, args.branch, rewrites)
    # Run copybara using java -jar
    cmd = ['java', '-jar', jar_path, config_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    finally:
        # Clean up temporary config
        try:
            os.remove(config_path)
        except OSError:
            pass

    if result.returncode != 0:
        print('Copybara execution failed:', file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    else:
        print('Copybara sync completed successfully.')
        print(result.stdout)
        sys.exit(0)

if __name__ == '__main__':
    main()
