"""CLI for AITokenProxy.

Commands:
    serve   — Start the proxy server
    stats   — Show compression statistics
    compress — Compress a prompt/file and show savings
"""

from __future__ import annotations

import argparse
import json
import sys


def cmd_serve(args):
    """Start the proxy server."""
    import uvicorn

    port = getattr(args, "port", 9090)
    host = getattr(args, "host", "0.0.0.0")
    print(f"🚀 AITokenProxy listening on {host}:{port}")
    print(f"   OpenAI proxy:  http://localhost:{port}/openai/v1/...")
    print(f"   Anthropic proxy: http://localhost:{port}/anthropic/v1/...")
    print(f"   Stats: http://localhost:{port}/stats")
    uvicorn.run("aitokenproxy.proxy:app", host=host, port=port, reload=False)


def cmd_stats(args):
    """Fetch and display stats from a running proxy."""
    import urllib.request

    port = getattr(args, "port", 9090)
    url = f"http://localhost:{port}/stats"
    try:
        req = urllib.request.urlopen(url, timeout=5)
        data = json.loads(req.read())
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error fetching stats: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_compress(args):
    """Compress a prompt or file and show savings."""
    from .compressor import CompressionPipeline

    pipeline = CompressionPipeline()
    text = args.text
    if args.file:
        with open(args.file) as f:
            text = f.read()

    if not text:
        print("No input text provided.", file=sys.stderr)
        sys.exit(1)

    _, result = pipeline.compress_prompt(text)
    print(f"Original tokens:  {result.original_tokens}")
    print(f"Compressed tokens: {result.compressed_tokens}")
    print(f"Savings: {result.savings_pct}% ({result.savings_tokens} tokens)")
    print(f"Strategy: {result.strategy}")


def main():
    parser = argparse.ArgumentParser(prog="aitokenproxy", description="AI Token Compression Proxy")
    sub = parser.add_subparsers(dest="command")

    # serve
    serve_p = sub.add_parser("serve", help="Start the proxy server")
    serve_p.add_argument("--port", type=int, default=9090)
    serve_p.add_argument("--host", default="0.0.0.0")
    serve_p.set_defaults(func=cmd_serve)

    # stats
    stats_p = sub.add_parser("stats", help="Show compression stats")
    stats_p.add_argument("--port", type=int, default=9090)
    stats_p.set_defaults(func=cmd_stats)

    # compress
    comp_p = sub.add_parser("compress", help="Compress a prompt")
    comp_p.add_argument("text", nargs="?", default="")
    comp_p.add_argument("--file", "-f", default=None)
    comp_p.set_defaults(func=cmd_compress)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
