"""libmonzo exceptions"""

class MonzoAPIError(Exception):
    """Base exception for an API error."""
    pass

class MonzoBadRequestError(MonzoAPIError):
    """The request had missing arguments or was malformed."""
    pass

class MonzoUnauthorizedError(MonzoAPIError):
    """An unauthenticated call was made."""
    pass

class MonzoForbiddenError(MonzoAPIError):
    """The request was authenticated, but the user doens't have permission."""
    pass

class MonzoNotFoundError(MonzoAPIError):
    """The resource was not found."""
    pass

class MonzoMethodNotAllowedError(MonzoAPIError):
    """An incorrect HTTP verb was used."""
    pass

class MonzoNotAcceptableError(MonzoAPIError):
    """The accept headers did not allow this response."""
    pass

class MonzoTooManyRequestsError(MonzoAPIError):
    """Too many requests have been issued."""
    pass

class MonzoInternalServerError(MonzoAPIError):
    """Something went wrong on the server side."""
    pass

class MonzoGatewayTimeoutError(MonzoAPIError):
    """Something timed out on the server side."""
    pass
