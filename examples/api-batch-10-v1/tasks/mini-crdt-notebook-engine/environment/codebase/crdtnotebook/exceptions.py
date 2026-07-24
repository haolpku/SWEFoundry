class CrdtNotebookError(Exception):
    """Base exception for the offline CRDT notebook benchmark package."""


class NotebookParseError(CrdtNotebookError, ValueError):
    """Raised when operation JSON cannot be decoded or normalized."""


class NotebookValidationError(CrdtNotebookError, ValueError):
    """Raised when a notebook operation violates an immutable field contract."""
