class EventProcessingError(Exception):
    """Base exception for ISAPI event processing failures."""


class XMLParseError(EventProcessingError):
    """Raised when the event XML cannot be parsed."""


class SnapshotSaveError(EventProcessingError):
    """Raised when a snapshot image cannot be written to disk."""
