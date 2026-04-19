class KickbaseError(Exception):
    """Base error for the KICKBASE API client."""


class KickbaseApiError(KickbaseError):
    """Raised for KICKBASE request and response errors."""


class KickbaseConfigurationError(KickbaseError):
    """Raised when required local configuration is missing."""