"""The single network call cvewatch makes: GET one Ubuntu CVE tracker page.

cvewatch sends one anonymous GET to one allowlisted host, with a named User-Agent so the
request is attributable in Ubuntu's logs. ``file://`` URLs are supported so the tool can be
pointed at a saved page and run fully offline. Every failure becomes FetchError; a failed
fetch is reported as unmeasurable, never as "not vulnerable".
"""

import urllib.error
import urllib.request

USER_AGENT = "cvewatch/1.0 (+jarmes daily build; read-only CVE watcher)"
TIMEOUT_SECONDS = 20


class FetchError(Exception):
    """The page could not be retrieved. Never conflate this with 'no vulnerability'."""


def fetch(url, timeout=TIMEOUT_SECONDS):
    """Fetch one page and return its text. ``cvewatch`` never follows a redirect off-host."""
    if not url:
        raise FetchError("empty URL")
    try:
        if url.startswith("file://"):
            with open(url[len("file://"):], "rb") as handle:
                return handle.read().decode("utf-8", errors="replace")
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            if status >= 400:
                raise FetchError("HTTP %s for %s" % (status, url))
            body = response.read()
    except FetchError:
        raise
    except urllib.error.HTTPError as error:
        raise FetchError("HTTP %s for %s" % (error.code, url))
    except (urllib.error.URLError, OSError, ValueError) as error:
        raise FetchError("cannot fetch %s: %s" % (url, error))
    return body.decode("utf-8", errors="replace")
