"""Custom domain exceptions for the MeetPoint engine."""


class MeetPointException(Exception):
    """Base exception for all MeetPoint errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ParticipantCoordinateError(MeetPointException):
    """Raised when participant coordinates are invalid or out of range."""
    pass


class GeographicSpreadError(ParticipantCoordinateError):
    """Raised when participants are too geographically dispersed for metropolitan network optimization."""
    pass


class InvalidBoundingBoxError(MeetPointException):
    """Raised when bounding box parameters are invalid."""
    pass


class ParticipantSnappingError(MeetPointException):
    """Raised when participant cannot be snapped to the road network."""
    pass


class NetworkAcquisitionError(MeetPointException):
    """Raised when the road network cannot be downloaded, parsed, or loaded."""
    pass


class DisconnectedNetworkError(MeetPointException):
    """Raised when participants cannot reach any common candidate meeting point."""
    pass
