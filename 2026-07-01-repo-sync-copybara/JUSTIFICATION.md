# Project Justification

**Problem**: Teams frequently need to keep multiple Git repositories in sync, such as mirroring internal forks to external mirrors or propagating changes across microservice repos. While Google’s **Copybara** tool can perform these migrations, its configuration complexity and Java runtime requirements make it cumbersome for day‑to‑day automation.

**User**: Developers and DevOps engineers within the Jarmes ecosystem who maintain multiple related repositories and need a lightweight, scriptable way to invoke copybara without manually crafting YAML configs each time.

**Why existing solutions are inadequate**:
- **Copybara** itself is powerful but requires verbose config files and a Java environment; ad‑hoc use is error‑prone.
- Simple `git remote add / push` scripts lack the transformation capabilities (e.g., path rewrites) that copybara provides.
- No out‑of‑the‑box CLI that abstracts the config generation and execution steps.

**Solution**: A tiny Python wrapper (`copysync`) that generates a minimal Copybara configuration on‑the‑fly, invokes the Copybara binary, and provides clear exit codes. It enables quick one‑off syncs and can be scheduled via cron or integrated into CI pipelines.

**Success criteria**:
- Able to sync a source branch to a destination repo with optional path rewrites.
- Runs on Windows and Unix hosts (uses subprocess).
- Returns a non‑zero exit code on failure and prints informative logs.
- Includes unit tests mocking subprocess to verify behavior.
