"""SmallWebRTC entry point for browser voice sessions."""

import asyncio
import atexit
import ctypes
import sys
from threading import Lock
from uuid import uuid4

from pipecat.runner.types import SmallWebRTCRunnerArguments

from agent.voice_session import VoiceSession
from agent.demo_config import PublicDemoConfig
from agent.demo_security import install_demo_security
from bounded_webrtc_audio import install_bounded_webrtc_audio


# Pipecat 1.10 documents importing its app to add supported middleware/routes
# before main() registers the runner endpoints.
from pipecat.runner.run import app as runner_app

install_demo_security(runner_app)


_active_demo_sessions: set[str] = set()
_active_demo_sessions_lock = Lock()


def _selector_loop_factory(*, use_subprocess: bool = False):
    """Keep SmallWebRTC's 10 ms audio pacing on Windows' selector loop."""
    return asyncio.SelectorEventLoop


def _reserve_demo_session(session_id: str, limit: int) -> bool:
    with _active_demo_sessions_lock:
        if len(_active_demo_sessions) >= limit:
            return False
        _active_demo_sessions.add(session_id)
        return True


def _release_demo_session(session_id: str) -> None:
    with _active_demo_sessions_lock:
        _active_demo_sessions.discard(session_id)


def _configure_windows_audio_timing():
    """Provide the timer precision required by SmallWebRTC's 10 ms audio track."""
    if sys.platform != "win32":
        return

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    # Uvicorn 0.36+ supplies its own loop factory to asyncio.run(), overriding
    # the policy above with ProactorEventLoop on Windows unless explicitly set.
    from uvicorn.config import LOOP_FACTORIES

    LOOP_FACTORIES["auto"] = "__main__:_selector_loop_factory"
    winmm = ctypes.WinDLL("winmm")
    if winmm.timeBeginPeriod(1) == 0:
        atexit.register(winmm.timeEndPeriod, 1)


def _create_transport(webrtc_connection):
    install_bounded_webrtc_audio()
    # Imported lazily so terminal and offline workflows do not require WebRTC extras.
    from pipecat.transports.base_transport import TransportParams
    from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport

    return SmallWebRTCTransport(
        webrtc_connection=webrtc_connection,
        params=TransportParams(audio_in_enabled=True, audio_out_enabled=True),
    )


async def bot(runner_args: SmallWebRTCRunnerArguments):
    """Run one isolated VoiceSession for one runner-managed WebRTC connection."""
    if not isinstance(runner_args, SmallWebRTCRunnerArguments):
        raise TypeError("browser.py requires SmallWebRTCRunnerArguments")
    if runner_args.cli_args is not None and sys.platform == "win32" and not isinstance(
        asyncio.get_running_loop(), asyncio.SelectorEventLoop
    ):
        raise RuntimeError("SmallWebRTC requires SelectorEventLoop on Windows")

    # The runner creates this ID server-side. Never derive persistent memory
    # identity from untrusted request_data supplied by a browser.
    session_id = runner_args.session_id or str(uuid4())
    caller_id = f"browser_session:{session_id}"
    demo_config = PublicDemoConfig.from_environment()
    reserved = False
    if demo_config.enabled:
        reserved = _reserve_demo_session(
            session_id, demo_config.max_concurrent_sessions
        )
        if not reserved:
            raise RuntimeError("Public demo concurrent-session limit reached")
    try:
        transport = _create_transport(runner_args.webrtc_connection)
        session = VoiceSession(
            transport,
            caller_id=caller_id,
            public_demo_mode=demo_config.enabled,
        )

        @transport.event_handler("on_client_disconnected")
        async def on_client_disconnected(_transport, _connection):
            await session.cancel("WebRTC client disconnected")

        run_session = session.run(
            handle_sigint=runner_args.handle_sigint,
            handle_sigterm=runner_args.handle_sigterm,
        )
        if demo_config.enabled:
            try:
                await asyncio.wait_for(
                    run_session, timeout=demo_config.max_session_seconds
                )
            except asyncio.TimeoutError:
                await session.cancel("Public demo session duration limit reached")
        else:
            await run_session
    finally:
        if "session" in locals():
            await session.cancel("WebRTC session stopped")
        if reserved:
            _release_demo_session(session_id)


if __name__ == "__main__":
    from pipecat.runner.run import main

    _configure_windows_audio_timing()
    main()
