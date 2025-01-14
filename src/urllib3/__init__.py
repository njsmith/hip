"""
urllib3 - Thread-safe connection pooling and re-using.
"""
from __future__ import absolute_import
import warnings

from .connectionpool import HTTPConnectionPool, HTTPSConnectionPool, connection_from_url

from . import exceptions
from .filepost import encode_multipart_formdata
from .poolmanager import PoolManager, ProxyManager, proxy_from_url
from .response import HTTPResponse
from .util.request import make_headers
from .util.url import get_host
from .util.timeout import Timeout
from .util.retry import Retry


# Set default logging handler to avoid "No handler found" warnings.
import logging
from logging import NullHandler

__author__ = "Andrey Petrov (andrey.petrov@shazow.net)"
__license__ = "MIT"
__version__ = "2.0.dev0+unasync.proof.of.concept.dont.use"

__all__ = [
    "HTTPConnectionPool",
    "HTTPSConnectionPool",
    "PoolManager",
    "ProxyManager",
    "HTTPResponse",
    "Retry",
    "Timeout",
    "add_stderr_logger",
    "connection_from_url",
    "disable_warnings",
    "encode_multipart_formdata",
    "get_host",
    "make_headers",
    "proxy_from_url",
]

# For now we only support async on 3.6, because we use async generators
import sys

if sys.version_info >= (3, 6):
    from urllib3._async.connectionpool import (  # NOQA
        HTTPConnectionPool as AsyncHTTPConnectionPool,
        HTTPSConnectionPool as AsyncHTTPSConnectionPool,
    )
    from urllib3._async.poolmanager import (  # NOQA
        PoolManager as AsyncPoolManager,
        ProxyManager as AsyncProxyManager,
    )
    from urllib3._async.response import HTTPResponse as AsyncHTTPResponse  # NOQA

    __all__.extend(
        (
            "AsyncHTTPConnectionPool",
            "AsyncHTTPSConnectionPool",
            "AsyncPoolManager",
            "AsyncProxyManager",
            "AsyncHTTPResponse",
        )
    )


logging.getLogger(__name__).addHandler(NullHandler())


def add_stderr_logger(level=logging.DEBUG):
    """
    Helper for quickly adding a StreamHandler to the logger. Useful for
    debugging.

    Returns the handler after adding it.
    """
    # This method needs to be in this __init__.py to get the __name__ correct
    # even if urllib3 is vendored within another package.
    logger = logging.getLogger(__name__)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.debug("Added a stderr logging handler to logger: %s", __name__)
    return handler


# ... Clean up.
del NullHandler


# All warning filters *must* be appended unless you're really certain that they
# shouldn't be: otherwise, it's very hard for users to use most Python
# mechanisms to silence them.
# SecurityWarning's always go off by default.
warnings.simplefilter("always", exceptions.SecurityWarning, append=True)
# SubjectAltNameWarning's should go off once per host
warnings.simplefilter("default", exceptions.SubjectAltNameWarning, append=True)
# InsecurePlatformWarning's don't vary between requests, so we keep it default.
warnings.simplefilter("default", exceptions.InsecurePlatformWarning, append=True)
# SNIMissingWarnings should go off only once.
warnings.simplefilter("default", exceptions.SNIMissingWarning, append=True)


def disable_warnings(category=exceptions.HTTPWarning):
    """
    Helper for quickly disabling all urllib3 warnings.
    """
    warnings.simplefilter("ignore", category)
