# 제작자: 신민철 | 이메일: min.developer.acc@gmail.com
import io
import socket
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import preview_health

class PreviewHealthTests(unittest.TestCase):
    def test_existing_listener_is_not_treated_as_new_app(self):
        with preview_health.exclusive_socket() as listener:
            listener.bind(('127.0.0.1',0))
            listener.listen(1)
            with self.assertRaises(OSError):
                preview_health.require_free_port(listener.getsockname()[1])

    def test_local_probe_checks_public_host(self):
        with patch.object(preview_health,'urlopen',return_value=io.BytesIO(b'{"service":"fintra","online":true}')) as request:
            preview_health.check_health('https://new.trycloudflare.com')
            sent=request.call_args.args[0]
            self.assertEqual(sent.get_header('Host'),'new.trycloudflare.com')
            self.assertEqual(sent.full_url,'http://127.0.0.1:8781/api/public-health')

    def test_external_probe_uses_actual_tunnel(self):
        with patch.object(preview_health,'urlopen',return_value=io.BytesIO(b'{"service":"fintra","online":true}')) as request:
            preview_health.check_health('https://new.trycloudflare.com',public=True)
            self.assertEqual(request.call_args.args[0].full_url,'https://new.trycloudflare.com/api/public-health')

    def test_wrong_service_or_offline_fails_readiness(self):
        for body in [b'{"online":true}',b'{"service":"fintra","online":false}']:
            with patch.object(preview_health,'urlopen',return_value=io.BytesIO(body)),self.assertRaises(RuntimeError):
                preview_health.check_health('https://new.trycloudflare.com')

    def test_revoked_tunnel_is_distinct_from_transient_reconnect(self):
        self.assertTrue(preview_health.tunnel_revoked('Register tunnel error: Unauthorized: Tunnel not found'))
        self.assertFalse(preview_health.tunnel_revoked('Retrying connection in 1s'))
