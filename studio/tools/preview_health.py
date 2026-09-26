# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
"""Readiness checks shared by the preview supervisor and its tests."""
import json
import socket
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def exclusive_socket():
    sock = socket.socket()
    if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    return sock


def require_free_port(port):
    with exclusive_socket() as sock:
        sock.bind(('127.0.0.1', port))


def check_health(origin, public=False):
    url = origin if public else 'http://127.0.0.1:8781'
    request = Request(url + '/api/public-health', headers={'Host': urlsplit(origin).netloc})
    with urlopen(request, timeout=5) as response:
        data = json.load(response)
    if data.get('service') != 'fintra' or data.get('online') is not True:
        raise RuntimeError('Unexpected health response')


def tunnel_revoked(log_text):
    return 'Unauthorized: Tunnel not found' in log_text
