from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from agent.demo_security import _client_id, demo_start_rate_limiter, install_demo_security


TOKEN = "a" * 32


def test_app() -> FastAPI:
    app = FastAPI()
    install_demo_security(app)

    @app.post("/start")
    async def start():
        return {"ok": True}

    @app.post("/api/offer")
    async def offer():
        return {"ok": True}

    return app


class DemoSecurityTests(unittest.TestCase):
    def setUp(self):
        demo_start_rate_limiter.clear()
        self.client = TestClient(test_app())

    def environment(self, **values):
        environment = {
            "PUBLIC_DEMO_MODE": "true",
            "PUBLIC_DEMO_ACCESS_TOKEN": TOKEN,
            "PUBLIC_DEMO_START_RATE_LIMIT": "2",
            "PUBLIC_DEMO_START_RATE_WINDOW_SECONDS": "60",
            "PUBLIC_DEMO_TRUSTED_PROXY_IPS": "",
        }
        environment.update(values)
        return patch.dict("os.environ", environment, clear=False)

    def test_demo_mode_requires_valid_bearer_on_start_and_offer(self):
        with self.environment():
            self.assertEqual(self.client.post("/start").status_code, 401)
            self.assertEqual(
                self.client.post(
                    "/api/offer", headers={"Authorization": "Bearer wrong"}
                ).status_code,
                401,
            )
            headers = {"Authorization": f"Bearer {TOKEN}"}
            self.assertEqual(self.client.post("/start", headers=headers).status_code, 200)
            self.assertEqual(
                self.client.post("/api/offer", headers=headers).status_code, 200
            )

    def test_missing_server_token_fails_closed(self):
        with self.environment(PUBLIC_DEMO_ACCESS_TOKEN=""):
            response = self.client.post("/start")
        self.assertEqual(response.status_code, 503)

    def test_start_rate_limit_ignores_untrusted_forwarding_headers(self):
        headers = {"Authorization": f"Bearer {TOKEN}"}
        with self.environment():
            first = self.client.post(
                "/start",
                headers={
                    **headers,
                    "X-Forwarded-For": "198.51.100.1",
                    "CF-Connecting-IP": "198.51.100.1",
                },
            )
            second = self.client.post(
                "/start",
                headers={
                    **headers,
                    "X-Forwarded-For": "198.51.100.2",
                    "CF-Connecting-IP": "198.51.100.2",
                },
            )
            limited = self.client.post(
                "/start",
                headers={
                    **headers,
                    "X-Forwarded-For": "198.51.100.3",
                    "CF-Connecting-IP": "198.51.100.3",
                },
            )
        self.assertEqual((first.status_code, second.status_code), (200, 200))
        self.assertEqual(limited.status_code, 429)

    def test_only_explicitly_trusted_peer_can_supply_client_identity(self):
        scope = {
            "type": "http",
            "method": "POST",
            "scheme": "http",
            "server": ("backend", 7860),
            "path": "/start",
            "query_string": b"",
            "headers": [(b"cf-connecting-ip", b"198.51.100.7")],
            "client": ("127.0.0.1", 12345),
        }
        request = Request(scope)

        with self.environment(PUBLIC_DEMO_TRUSTED_PROXY_IPS=""):
            self.assertEqual(_client_id(request), "127.0.0.1")
        with self.environment(PUBLIC_DEMO_TRUSTED_PROXY_IPS="127.0.0.1"):
            self.assertEqual(_client_id(request), "198.51.100.7")

    def test_authenticated_reconnect_reuses_gateway_contract(self):
        headers = {"Authorization": f"Bearer {TOKEN}"}
        with self.environment():
            for _ in range(2):
                self.assertEqual(
                    self.client.post("/start", headers=headers).status_code, 200
                )
                self.assertEqual(
                    self.client.post("/api/offer", headers=headers).status_code, 200
                )
            self.assertEqual(
                self.client.post("/start", headers=headers).status_code, 429
            )

    def test_normal_mode_preserves_unauthenticated_runner_behavior(self):
        with patch.dict("os.environ", {"PUBLIC_DEMO_MODE": "false"}, clear=False):
            self.assertEqual(self.client.post("/start").status_code, 200)


if __name__ == "__main__":
    unittest.main()
