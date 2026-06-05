#!/usr/bin/env python3
"""Quick test of the healthpulse CLI against real logs."""
import sys
sys.path.insert(0, r"C:\Users\jyot2\jarvis\projects\forge-projects-repo\2026-06-05-jarmes-health-pulse")

from healthpulse.cli import main
sys.argv = ["healthpulse", "summary"]
main()
