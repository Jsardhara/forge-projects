"""The one exception type: a measurement that could not be made."""


class WsAuditError(Exception):
    """Raised when a model file cannot be parsed or hashed.

    Callers map this to exit code 2 ("could not measure") - never to 0.
    """
