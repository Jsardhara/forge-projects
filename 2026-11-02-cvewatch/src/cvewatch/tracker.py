"""Read the Ubuntu CVE tracker page into rows: (package, release, status, fix target).

The page is a single table whose first cell uses ``rowspan`` to group releases by source
package. A row's meaning lives in its status cell, and the fix version - when the tracker
knows one - is the token after "work in progress in" or "fix released in". Everything here
is tolerant: an unknown status is kept as ``unknown`` rather than dropped, because a row a
parser silently skips is a CVE a watcher silently stops watching.
"""

import re
from dataclasses import dataclass

CVE_RE = re.compile(r"CVE-\d{4}-\d{4,7}")
TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")
RELEASE_ID_RE = re.compile(r"\d{2}\.\d{2}")
CODENAME_RE = re.compile(r"[a-z][a-z0-9-]*")
WORK_IN_PROGRESS_RE = re.compile(r"work in progress in\s+([0-9][^\s,;]*)", re.I)
FIX_RELEASED_RE = re.compile(r"fix released in\s+([0-9][^\s,;]*)", re.I)
ROWSPAN_RE = re.compile(r'<th[^>]*rowspan="\d+"[^>]*>(.*?)</th>', re.S)
TD_RE = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
TR_RE = re.compile(r"<tr>(.*?)</tr>", re.S)

# Words in a release cell that are not the codename.
_NOISE = {
    "lts", "fips", "real-time", "real", "time", "updates", "esm", "certified",
    "package", "available", "with", "ubuntu", "pro.", "pro", "and", "security",
    "fixes", "fixes.", "support", "extended",
}

_KINDS = ("vulnerable", "patched", "not_in_release", "ignored", "pending", "unknown")


@dataclass(frozen=True)
class Row:
    """One (source package, Ubuntu release) cell from the tracker table."""

    package: str
    release: str
    release_id: str
    codename: str
    qualifier: str
    kind: str
    fixed_version: str
    released: bool
    detail: str

    def is_plain(self):
        return self.qualifier == ""


@dataclass(frozen=True)
class CvePage:
    cve_id: str
    rows: tuple
    source: str = ""


def _text(fragment):
    """Tags to spaces, entities decoded for the handful that matter, whitespace collapsed."""
    text = TAG_RE.sub(" ", fragment)
    for entity, char in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                         ("&quot;", '"'), ("&#39;", "'"), ("&nbsp;", " ")):
        text = text.replace(entity, char)
    return WHITESPACE_RE.sub(" ", text).strip()


def _parse_release(text):
    """Split a release cell into (release_id, codename, qualifier)."""
    tokens = text.split()
    release_id = ""
    for token in tokens:
        if RELEASE_ID_RE.fullmatch(token):
            release_id = token
            break
    codename = ""
    for token in tokens:
        lowered = token.lower()
        if token == release_id or lowered in _NOISE or "fips" in lowered:
            continue
        if CODENAME_RE.fullmatch(token):
            codename = token
            break
    rest = [token for token in tokens
            if token not in (release_id, codename) and token.lower() not in ("lts",)]
    return release_id, codename, " ".join(rest).strip()


def _parse_status(detail):
    """Return (kind, fixed_version, released) for a status cell's text."""
    text = detail.strip()
    lowered = text.lower()
    if not text:
        return "unknown", "", False
    if lowered.startswith("not affected") or lowered.startswith("not vulnerable"):
        return "patched", "", False
    if lowered.startswith("not in release"):
        return "not_in_release", "", False
    if lowered.startswith("ignored"):
        return "ignored", "", False
    if lowered.startswith("pending"):
        return "pending", "", False
    if lowered.startswith("vulnerable") or lowered.startswith("in progress"):
        released = FIX_RELEASED_RE.search(text)
        if released:
            return "vulnerable", released.group(1), True
        target = WORK_IN_PROGRESS_RE.search(text)
        if target:
            return "vulnerable", target.group(1), False
        return "vulnerable", "", False
    return "unknown", "", False


def parse(html, source=""):
    """Parse a tracker page. Never raises: a page with no table yields an empty CvePage."""
    text = html or ""
    match = CVE_RE.search(text)
    title = re.search(r"<title>(.*?)</title>", text, re.S)
    cve_id = ""
    if title:
        found = CVE_RE.search(_text(title.group(1)))
        cve_id = found.group(0) if found else ""
    if not cve_id and match:
        cve_id = match.group(0)

    start = text.find('<table class="cve-table')
    if start < 0:
        start = text.find("<table")
    if start < 0:
        return CvePage(cve_id=cve_id, rows=(), source=source)
    end = text.find("</table>", start)
    table = text[start:end if end >= 0 else len(text)]

    rows = []
    package = ""
    for chunk in TR_RE.findall(table):
        header = ROWSPAN_RE.search(chunk)
        if header:
            package = _text(header.group(1))
        cells = TD_RE.findall(chunk)
        if len(cells) < 2 or not package:
            continue
        release_text = _text(cells[0])
        status_cell = cells[1]
        for cell in cells:
            if "cve-td-status" in cell:
                status_cell = cell
                break
        detail = _text(status_cell)
        release_id, codename, qualifier = _parse_release(release_text)
        kind, fixed_version, released = _parse_status(detail)
        rows.append(Row(package=package, release=release_text, release_id=release_id,
                        codename=codename, qualifier=qualifier, kind=kind,
                        fixed_version=fixed_version, released=released, detail=detail))
    return CvePage(cve_id=cve_id, rows=tuple(rows), source=source)


def rows_for_release(page, release_id, codename=""):
    """All rows for one release.

    A numeric release id is authoritative: if the page has no row for ``26.04`` then the
    answer is "this release is not tracked here", not "try a different release whose codename
    happens to match". The codename fallback applies only when no release id was supplied.
    """
    if release_id:
        return tuple(row for row in page.rows if row.release_id == release_id)
    if codename:
        return tuple(row for row in page.rows if row.codename == codename)
    return ()


def pick_row(page, package, release_id, codename=""):
    """The row that applies to one package on one release, preferring the unqualified row.

    FIPS and Real-time variants share the release id but are separate kernel flavours; the
    plain row is the one a stock host runs.
    """
    candidates = [row for row in page.rows
                  if row.package == package
                  and ((release_id and row.release_id == release_id)
                       or (not release_id and codename and row.codename == codename))]
    if not candidates:
        return None
    plain = [row for row in candidates if row.is_plain()]
    return plain[0] if plain else candidates[0]
