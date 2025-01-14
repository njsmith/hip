#!/usr/bin/env python

"""
Dummy server used for unit testing.
"""
from __future__ import print_function

import logging
import os
import random
import string
import sys
import threading
import socket
import warnings
import ssl
from datetime import datetime

from urllib3.exceptions import HTTPWarning

import tornado.httpserver
import tornado.ioloop
import tornado.netutil
import tornado.web


log = logging.getLogger(__name__)

CERTS_PATH = os.path.join(os.path.dirname(__file__), "certs")
DEFAULT_CERTS = {
    "certfile": os.path.join(CERTS_PATH, "server.crt"),
    "keyfile": os.path.join(CERTS_PATH, "server.key"),
    "cert_reqs": ssl.CERT_OPTIONAL,
    "ca_certs": os.path.join(CERTS_PATH, "cacert.pem"),
}
DEFAULT_CLIENT_CERTS = {
    "certfile": os.path.join(CERTS_PATH, "client_intermediate.pem"),
    "keyfile": os.path.join(CERTS_PATH, "client_intermediate.key"),
}
DEFAULT_CLIENT_NO_INTERMEDIATE_CERTS = {
    "certfile": os.path.join(CERTS_PATH, "client_no_intermediate.pem"),
    "keyfile": os.path.join(CERTS_PATH, "client_intermediate.key"),
}
PASSWORD_KEYFILE = os.path.join(CERTS_PATH, "server_password.key")
PASSWORD_CLIENT_KEYFILE = os.path.join(CERTS_PATH, "client_password.key")
NO_SAN_CERTS = {
    "certfile": os.path.join(CERTS_PATH, "server.no_san.crt"),
    "keyfile": DEFAULT_CERTS["keyfile"],
}
IP_SAN_CERTS = {
    "certfile": os.path.join(CERTS_PATH, "server.ip_san.crt"),
    "keyfile": DEFAULT_CERTS["keyfile"],
}
IPV6_ADDR_CERTS = {
    "certfile": os.path.join(CERTS_PATH, "server.ipv6addr.crt"),
    "keyfile": os.path.join(CERTS_PATH, "server.ipv6addr.key"),
}
IPV6_SAN_CERTS = {
    "certfile": os.path.join(CERTS_PATH, "server.ipv6_san.crt"),
    "keyfile": DEFAULT_CERTS["keyfile"],
}
DEFAULT_CA = os.path.join(CERTS_PATH, "cacert.pem")
DEFAULT_CA_BAD = os.path.join(CERTS_PATH, "client_bad.pem")
NO_SAN_CA = os.path.join(CERTS_PATH, "cacert.no_san.pem")
DEFAULT_CA_DIR = os.path.join(CERTS_PATH, "ca_path_test")
IPV6_ADDR_CA = os.path.join(CERTS_PATH, "server.ipv6addr.crt")
IPV6_SAN_CA = os.path.join(CERTS_PATH, "server.ipv6_san.crt")
COMBINED_CERT_AND_KEY = os.path.join(CERTS_PATH, "server.combined.pem")


def _has_ipv6(host):
    """ Returns True if the system can bind an IPv6 address. """
    sock = None
    has_ipv6 = False

    if socket.has_ipv6:
        # has_ipv6 returns true if cPython was compiled with IPv6 support.
        # It does not tell us if the system has IPv6 support enabled. To
        # determine that we must bind to an IPv6 address.
        # https://github.com/urllib3/urllib3/pull/611
        # https://bugs.python.org/issue658327
        try:
            sock = socket.socket(socket.AF_INET6)
            sock.bind((host, 0))
            has_ipv6 = True
        except Exception:
            pass

    if sock:
        sock.close()
    return has_ipv6


# Some systems may have IPv6 support but DNS may not be configured
# properly. We can not count that localhost will resolve to ::1 on all
# systems. See https://github.com/urllib3/urllib3/pull/611 and
# https://bugs.python.org/issue18792
HAS_IPV6_AND_DNS = _has_ipv6("localhost")
HAS_IPV6 = _has_ipv6("::1")


# Different types of servers we have:


class NoIPv6Warning(HTTPWarning):
    "IPv6 is not available"
    pass


class SocketServerThread(threading.Thread):
    """
    :param socket_handler: Callable which receives a socket argument for one
        request.
    :param ready_event: Event which gets set when the socket handler is
        ready to receive requests.
    """

    USE_IPV6 = HAS_IPV6_AND_DNS

    def __init__(self, socket_handler, host="localhost", port=8081, ready_event=None):
        threading.Thread.__init__(self)
        self.daemon = True

        self.socket_handler = socket_handler
        self.host = host
        self.ready_event = ready_event

    def _start_server(self):
        if self.USE_IPV6:
            sock = socket.socket(socket.AF_INET6)
        else:
            warnings.warn("No IPv6 support. Falling back to IPv4.", NoIPv6Warning)
            sock = socket.socket(socket.AF_INET)
        if sys.platform != "win32":
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, 0))
        self.port = sock.getsockname()[1]

        # Once listen() returns, the server socket is ready
        sock.listen(1)

        if self.ready_event:
            self.ready_event.set()

        self.socket_handler(sock)
        sock.close()

    def run(self):
        self.server = self._start_server()


def run_tornado_app(app, io_loop, certs, scheme, host):
    assert io_loop == tornado.ioloop.IOLoop.current()

    # We can't use fromtimestamp(0) because of CPython issue 29097, so we'll
    # just construct the datetime object directly.
    app.last_req = datetime(1970, 1, 1)

    if scheme == "https":
        http_server = tornado.httpserver.HTTPServer(app, ssl_options=certs)
    else:
        http_server = tornado.httpserver.HTTPServer(app)

    sockets = tornado.netutil.bind_sockets(None, address=host)
    port = sockets[0].getsockname()[1]
    http_server.add_sockets(sockets)
    return http_server, port


def run_loop_in_thread(io_loop):
    t = threading.Thread(target=io_loop.start)
    t.start()
    return t


def get_unreachable_address():
    while True:
        host = "".join(random.choice(string.ascii_lowercase) for _ in range(60))
        sockaddr = (host, 54321)

        # check if we are really "lucky" and hit an actual server
        try:
            s = socket.create_connection(sockaddr)
        except socket.error:
            return sockaddr
        else:
            s.close()


if __name__ == "__main__":
    # For debugging dummyserver itself - python -m dummyserver.server
    from .testcase import TestingApp

    host = "127.0.0.1"

    io_loop = tornado.ioloop.IOLoop.current()
    app = tornado.web.Application([(r".*", TestingApp)])
    server, port = run_tornado_app(app, io_loop, None, "http", host)
    server_thread = run_loop_in_thread(io_loop)

    print("Listening on http://{host}:{port}".format(host=host, port=port))
