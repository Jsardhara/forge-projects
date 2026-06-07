"""Repo state management — INDEX.md, git operations, project scanning."""

import datetime
import subprocess
from pathlib import Path
from typing import List, Dict, Optional

DEFAULT_REPO = Path("C:/Users/jyot2/jarvis/projects/forge-projects-repo")


def scan_projects(repo_path: Path = DEFAULT_REPO) -> List[Dict[str, str]]:
    """Scan the repo for existing projects and return metadata."""
    projects = []
    for item in sorted(repo_path.iterdir()):
        if not item.is_dir():
            continue
        if item.name.startswith("."):
            continue
        # Expected format: YYYY-MM-DD-project-slug
        parts = item.name.split("-", 3)
        if len(parts) >= 4 and len(parts[0]) == 4:
            date_str = "-".join(parts[:3])
            slug = parts[3]
            readme = item / "README.md"
            desc = ""
            if readme.exists():
                first_lines = readme.read_text().splitlines()
                for line in first_lines:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        desc = line[:100]
                        break
            projects.append({
                "date": date_str,
                "slug": slug,
                "folder": item.name,
                "description": desc,
            })
    return projects


def read_index(repo_path: Path = DEFAULT_REPO) -> str:
    """Read the current INDEX.md content."""
    index_path = repo_path / "INDEX.md"
    if index_path.exists():
        return index_path.read_text()
    return ""


def update_index(repo_path: Path = DEFAULT_REPO) -> str:
    """Rebuild INDEX.md from scratch by scanning the repo."""
    projects = scan_projects(repo_path)
    today = datetime.date.today().isoformat()

    lines = [
        "# Forge — Daily Projects",
        "",
        "One project per day, autonomously generated from world news.",
        "",
        "| Date | Project | Source | Folder |",
        "|------|---------|--------|--------|",
    ]

    for p in projects:
        project_name = p["slug"].replace("-", " ").title()
        folder_link = f"./{p['folder']}"
        lines.append(
            f"| {p['date']} | {project_name} | [Pipeline](https://github.com/Jsardhara/forge-projects) | [{p['folder']}]({folder_link}) |"
        )

    content = "\n".join(lines) + "\n"
    (repo_path / "INDEX.md").write_text(content)
    return content


def git_status(repo_path: Path = DEFAULT_REPO) -> str:
    """Return git status output."""
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        cwd=str(repo_path),
    )
    return result.stdout.strip()


def git_commit_all(message: str, repo_path: Path = DEFAULT_REPO) -> bool:
    """Stage all changes and commit."""
    subprocess.run(["git", "add", "-A"], cwd=str(repo_path), check=True)
    result = subprocess.run(
        ["git", "commit", "-m", message],
        capture_output=True,
        text=True,
        cwd=str(repo_path),
    )
    return result.returncode == 0


def git_push(repo_path: Path = DEFAULT_REPO) -> bool:
    """Push to origin/main."""
    result = subprocess.run(
        ["git", "push", "origin", "main"],
        capture_output=True,
        text=True,
        cwd=str(repo_path),
    )
    if result.returncode != 0:
        print(f"Push failed: {result.stderr}")
        return False
    return True


def get_last_project(repo_path: Path = DEFAULT_REPO) -> Optional[Dict[str, str]]:
    """Get the most recent project from the repo."""
    projects = scan_projects(repo_path)
    return projects[-1] if projects else None


def get_project_count(repo_path: Path = DEFAULT_REPO) -> int:
    """Count projects in the repo."""
    return len(scan_projects(repo_path))
