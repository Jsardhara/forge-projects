"""The only module that touches the network. Read-only, keyless, no cookies, no auth."""
import json
import urllib.error
import urllib.request

from .models import Fetch

USER_AGENT = "exitpath/0.2 (+read-only; public status signals only)"


class HttpFetcher:
    """GET a public status document / POST a public JSON-RPC call. Nothing else."""

    def __init__(self, timeout: float = 12.0, user_agent: str = USER_AGENT):
        self.timeout = timeout
        self.user_agent = user_agent

    def _open(self, request):
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return Fetch(response.status, response.read(), None)
        except urllib.error.HTTPError as exc:
            body = b""
            try:
                body = exc.read()
            except Exception:  # noqa: BLE001 - body of an error is optional
                pass
            return Fetch(int(exc.code), body, None)
        except Exception as exc:  # noqa: BLE001 - surfaced as a reason, never swallowed
            return Fetch(0, b"", "%s: %s" % (type(exc).__name__, exc))

    def get(self, url):
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent,
                                                       "Accept": "application/json"})
        return self._open(request)

    def post_json(self, url, payload):
        """Returns (status, body) for the chain layer; raises nothing on HTTP errors."""
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"User-Agent": self.user_agent, "Content-Type": "application/json",
                     "Accept": "application/json"},
            method="POST",
        )
        result = self._open(request)
        if result.error:
            raise OSError(result.error)
        return result.status, result.body
