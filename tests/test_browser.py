from __future__ import annotations

import os
import asyncio
import unittest
from unittest.mock import patch

import browser
from pipecat.runner.types import SmallWebRTCRunnerArguments


class FakeTransport:
    def __init__(self):
        self.handlers = {}

    def event_handler(self, name):
        def register(handler):
            self.handlers[name] = handler
            return handler
        return register


class FakeSession:
    instances = []

    def __init__(self, transport, *, caller_id, public_demo_mode=False):
        self.transport = transport
        self.caller_id = caller_id
        self.public_demo_mode = public_demo_mode
        self.run_arguments = None
        self.cancel_reasons = []
        self.__class__.instances.append(self)

    async def run(self, **arguments):
        self.run_arguments = arguments
        await self.transport.handlers["on_client_disconnected"](
            self.transport, object()
        )

    async def cancel(self, reason):
        self.cancel_reasons.append(reason)


class SlowSession(FakeSession):
    async def run(self, **arguments):
        self.run_arguments = arguments
        await asyncio.Event().wait()


class BrowserEntryPointTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        FakeSession.instances.clear()
        browser._active_demo_sessions.clear()

    async def test_server_session_id_scopes_identity_and_disconnect(self):
        transport = FakeTransport()
        arguments = SmallWebRTCRunnerArguments(
            webrtc_connection=object(),
            session_id="server-generated-id",
            body={"caller_id": "untrusted-browser-id"},
        )

        with (
            patch.object(browser, "_create_transport", return_value=transport),
            patch.object(browser, "VoiceSession", FakeSession),
        ):
            await browser.bot(arguments)

        session = FakeSession.instances[0]
        self.assertEqual(session.caller_id, "browser_session:server-generated-id")
        self.assertFalse(session.public_demo_mode)
        self.assertEqual(
            session.run_arguments,
            {"handle_sigint": False, "handle_sigterm": False},
        )
        self.assertEqual(session.cancel_reasons, [
            "WebRTC client disconnected",
            "WebRTC session stopped",
        ])

    async def test_connections_create_independent_sessions(self):
        transports = [FakeTransport(), FakeTransport()]
        arguments = [
            SmallWebRTCRunnerArguments(webrtc_connection=object(), session_id="one"),
            SmallWebRTCRunnerArguments(webrtc_connection=object(), session_id="two"),
        ]

        with (
            patch.object(browser, "_create_transport", side_effect=transports),
            patch.object(browser, "VoiceSession", FakeSession),
        ):
            await browser.bot(arguments[0])
            await browser.bot(arguments[1])

        self.assertIsNot(FakeSession.instances[0], FakeSession.instances[1])
        self.assertEqual(
            [session.caller_id for session in FakeSession.instances],
            ["browser_session:one", "browser_session:two"],
        )

    async def test_demo_mode_is_explicit_and_releases_capacity(self):
        transport = FakeTransport()
        arguments = SmallWebRTCRunnerArguments(
            webrtc_connection=object(), session_id="demo-one"
        )
        environment = {
            "PUBLIC_DEMO_MODE": "true",
            "PUBLIC_DEMO_MAX_CONCURRENT_SESSIONS": "1",
            "PUBLIC_DEMO_MAX_SESSION_SECONDS": "30",
        }

        with (
            patch.dict(os.environ, environment, clear=False),
            patch.object(browser, "_create_transport", return_value=transport),
            patch.object(browser, "VoiceSession", FakeSession),
        ):
            await browser.bot(arguments)

        self.assertTrue(FakeSession.instances[0].public_demo_mode)
        self.assertEqual(browser._active_demo_sessions, set())

    async def test_demo_concurrency_limit_rejects_excess_session(self):
        browser._active_demo_sessions.add("existing")
        arguments = SmallWebRTCRunnerArguments(
            webrtc_connection=object(), session_id="excess"
        )
        environment = {
            "PUBLIC_DEMO_MODE": "true",
            "PUBLIC_DEMO_MAX_CONCURRENT_SESSIONS": "1",
            "PUBLIC_DEMO_MAX_SESSION_SECONDS": "30",
        }

        with (
            patch.dict(os.environ, environment, clear=False),
            patch.object(browser, "_create_transport") as create_transport,
        ):
            with self.assertRaisesRegex(RuntimeError, "limit reached"):
                await browser.bot(arguments)

        create_transport.assert_not_called()
        self.assertEqual(browser._active_demo_sessions, {"existing"})

    async def test_demo_duration_limit_cancels_and_releases_session(self):
        transport = FakeTransport()
        arguments = SmallWebRTCRunnerArguments(
            webrtc_connection=object(), session_id="timed"
        )
        config = browser.PublicDemoConfig(
            enabled=True, max_concurrent_sessions=1, max_session_seconds=0.01
        )

        with (
            patch.object(
                browser.PublicDemoConfig,
                "from_environment",
                return_value=config,
            ),
            patch.object(browser, "_create_transport", return_value=transport),
            patch.object(browser, "VoiceSession", SlowSession),
        ):
            await browser.bot(arguments)

        session = SlowSession.instances[0]
        self.assertIn(
            "Public demo session duration limit reached", session.cancel_reasons
        )
        self.assertEqual(browser._active_demo_sessions, set())


if __name__ == "__main__":
    unittest.main()
