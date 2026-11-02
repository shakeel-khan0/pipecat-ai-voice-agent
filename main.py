"""Local microphone entry point for the AI Voice Receptionist."""

import asyncio

from dotenv import load_dotenv
from loguru import logger
from pipecat.adapters.schemas.direct_function import tool_options
from pipecat.services.llm_service import FunctionCallParams
from pipecat.transports.local.audio import LocalAudioTransport, LocalAudioTransportParams

from agent.voice_session import SYSTEM_PROMPT, SpokenTextFilter, VoiceSession, load_system_prompt
from trace_recorder import terminal_trace_recorder


logger.remove()
logger.add(lambda msg: print(msg, end=""), level="WARNING")
load_dotenv()

transport = LocalAudioTransport(
    LocalAudioTransportParams(audio_in_enabled=True, audio_out_enabled=True)
)
terminal_session = VoiceSession(transport, recorder=terminal_trace_recorder)

# Preserve the existing terminal module interface used by focused regression tests.
booking_session = terminal_session.booking_session
transcription_printer = terminal_session.transcription_printer
_pending_email = ""
_pending_email_turn = 0


def _latest_caller_text():
    return transcription_printer.latest_text


def _latest_caller_turn():
    return transcription_printer.turn_id


def _caller_supported_time_preference(preference: str, caller_text: str) -> str:
    return terminal_session._caller_supported_time_preference(preference, caller_text)


def _say_email(email: str) -> str:
    return terminal_session._say_email(email)


def _email_requires_confirmation(email: str, caller_text: str, caller_turn: int) -> bool:
    global _pending_email, _pending_email_turn
    terminal_session._pending_email = _pending_email
    terminal_session._pending_email_turn = _pending_email_turn
    result = terminal_session._email_requires_confirmation(email, caller_text, caller_turn)
    _pending_email = terminal_session._pending_email
    _pending_email_turn = terminal_session._pending_email_turn
    return result


@tool_options(cancel_on_interruption=True, timeout_secs=120)
async def booking_workflow(
    params: FunctionCallParams,
    meeting_date: str = "",
    meeting_time: str = "",
    name: str = "",
    email: str = "",
    time_preference: str = "",
    business: str = "",
    industry: str = "",
    problem: str = "",
    volume: str = "",
    current_system: str = "",
    interested_services: str = "",
):
    """Compatibility wrapper for the terminal session's booking tool."""
    global _pending_email, _pending_email_turn
    terminal_session.booking_session = booking_session
    terminal_session.transcription_printer = transcription_printer
    terminal_session._pending_email = _pending_email
    terminal_session._pending_email_turn = _pending_email_turn
    try:
        return await terminal_session.booking_workflow(
            params,
            meeting_date=meeting_date,
            meeting_time=meeting_time,
            name=name,
            email=email,
            time_preference=time_preference,
            business=business,
            industry=industry,
            problem=problem,
            volume=volume,
            current_system=current_system,
            interested_services=interested_services,
        )
    finally:
        _pending_email = terminal_session._pending_email
        _pending_email_turn = terminal_session._pending_email_turn


stt = terminal_session.stt
llm = terminal_session.llm
tts = terminal_session.tts
context = terminal_session.context
user_aggregator = terminal_session.user_aggregator
assistant_aggregator = terminal_session.assistant_aggregator
rag_context = terminal_session.rag_context
memory_context = terminal_session.memory_context
memory_ingest = terminal_session.memory_ingest
retrieval_prefetch = terminal_session.retrieval_prefetch
pipeline = terminal_session.pipeline
worker = terminal_session.worker


async def main():
    await terminal_session.run()


if __name__ == "__main__":
    asyncio.run(main())
