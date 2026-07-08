# Copysync

A lightweight Python wrapper around **Google Copybara** that generates a minimal configuration on the fly and invokes the Copybara JAR.

## Features
- One‑line CLI: `copysync --src <src> --dst <dst> [--branch <branch>] [--rewrite old:new]`
- Generates temporary Copybara config with optional path rewrites.
- Handles Copybara JAR location via `$COPYBARA_JAR` or default `/usr/local/bin/copybara.jar`.
- Provides clear exit codes and error messages.
- No external Python dependencies besides the standard library.

## Installation
```bash
pip install .
```

## Usage
```bash
copysync --src git@github.com:myorg/repo.git \
         --dst git@github.com:myorg/mirror.git \
         --branch develop \
         --rewrite oldpath:newpath
```

## Development
Run the test suite:
```bash
pytest -v
```
