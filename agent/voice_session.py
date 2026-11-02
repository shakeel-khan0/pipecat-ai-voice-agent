"""Session-scoped construction for the AI voice receptionist pipeline."""

import os
import re
from datetime import datetime
from pathlib import Path
from time import perf_counter
from uuid import uuid4
from zoneinfo import ZoneInfo

from pipecat.adapters.schemas.direct_function import tool_options
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import (
    Frame,
    FunctionCallResultProperties,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
    TextFrame,
    TranscriptionFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.services.deepgram.flux.stt import DeepgramFluxSTTService
from pipecat.services.deepgram.tts import DeepgramTTSService
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.llm_service import FunctionCallParams
from pipecat.turns.user_mute import FunctionCallUserMuteStrategy
from pipecat.utils.text.base_text_filter import BaseTextFilter
from pipecat.workers.runner import WorkerRunner

from agent.booking_session import BookingSession
from memory.caller_identity import resolve_caller_id
from memory.integration import VoiceMemContextProcessor, VoiceMemIngestProcessor
from memory.orchestration import RetrievalPrefetchProcessor
from rag.integration import RAGContextProcessor
from trace_recorder import (
    PROJECT_ROOT,
    TraceMetricsObserver,
    TraceRecorder,
    use_trace_recorder,
)


_DAY_PARTS = ("morning", "afternoon", "evening")


def load_system_prompt():
    with open(
        Path(__file__).resolve().parent.parent / "prompts" / "receptionist.md",
        "r",
        encoding="utf-8",
    ) as file:
        return file.read()


SYSTEM_PROMPT = load_system_prompt() + (
    "\nCurrent local date: "
    + datetime.now(ZoneInfo("Asia/Karachi")).strftime("%Y-%m-%d")
    + ". Resolve relative dates in Asia/Karachi timezone.\n"
)


class SpokenTextFilter(BaseTextFilter):
    async def filter(self, text: str) -> str:
        return text.translate(str.maketrans("", "", '"“”*`'))


class LLMPrintProcessor(FrameProcessor):
    def __init__(self, recorder: TraceRecorder):
        super().__init__()
        self._recorder = recorder

    async def process_frame(self, frame: Frame, direction):
        await super().process_frame(frame, direction)
        if isinstance(frame, LLMFullResponseStartFrame):
            self._recorder.start_assistant_response()
        if isinstance(frame, TextFrame):
            self._recorder.assistant_text(frame.text)
            print(frame.text, end="", flush=True)
        if isinstance(frame, LLMFullResponseEndFrame):
            self._recorder.end_assistant_response()
            print()
        await self.push_frame(frame, direction)


class TranscriptionPrinter(FrameProcessor):
    def __init__(self, recorder: TraceRecorder):
        super().__init__()
        self._recorder = recorder
        self.latest_text = ""
        self.turn_id = 0

    async def process_frame(self, frame: Frame, direction):
        await super().process_frame(frame, direction)
        if isinstance(frame, TranscriptionFrame):
            self.latest_text = frame.text
            self.turn_id += 1
            self._recorder.user_turn(frame.text)
            print(f"You: {frame.text}")
        await self.push_frame(frame, direction)


class VoiceSession:
    """Own all mutable runtime state for one caller conversation."""

    def __init__(
        self,
        transport,
        *,
        caller_id: str | None = None,
        recorder: TraceRecorder | None = None,
        booking_session: BookingSession | None = None,
        public_demo_mode: bool = False,
    ):
        self.transport = transport
        self.caller_id = caller_id or resolve_caller_id()
        self.recorder = recorder or TraceRecorder(
            PROJECT_ROOT / "traces" / f"session-{uuid4()}.json"
        )
        self.public_demo_mode = public_demo_mode
        self.booking_session = booking_session or BookingSession(
            public_demo_mode=public_demo_mode
        )
        self._pending_email = ""
        self._pending_email_turn = 0
        self.runner = None
        self._cancel_requested = False

        self.stt = DeepgramFluxSTTService(
            api_key=os.getenv("DEEPGRAM_API_KEY"),
            settings=DeepgramFluxSTTService.Settings(
                model="flux-general-en",
                min_confidence=0.3,
                eot_threshold=0.8,
                keyterm=["Agentix Labs AI", "PongVerse", "LangGraph", "DeepSORT"],
            ),
        )
        self.llm = GroqLLMService(
            api_key=os.getenv("GROQ_API_KEY"),
            settings=GroqLLMService.Settings(
                model="openai/gpt-oss-120b",
                temperature=0.3,
                system_instruction=SYSTEM_PROMPT,
                extra={"extra_body": {"reasoning_format": "hidden"}},
            ),
        )
        self.tts = DeepgramTTSService(
            api_key=os.getenv("DEEPGRAM_API_KEY"),
            settings=DeepgramTTSService.Settings(voice="aura-2-thalia-en"),
            text_filters=[SpokenTextFilter()],
        )

        self.transcription_printer = TranscriptionPrinter(self.recorder)
        self.booking_workflow = self._create_booking_workflow()
        self.context = LLMContext(tools=[self.booking_workflow])
        self.user_aggregator, self.assistant_aggregator = LLMContextAggregatorPair(
            self.context,
            user_params=LLMUserAggregatorParams(
                vad_analyzer=SileroVADAnalyzer(),
                user_mute_strategies=[FunctionCallUserMuteStrategy()],
            ),
        )
        self.rag_context = RAGContextProcessor()
        self.memory_context = VoiceMemContextProcessor(caller_id=self.caller_id)
        self.memory_ingest = VoiceMemIngestProcessor(
            caller_id=self.caller_id,
            enabled=not public_demo_mode,
        )
        self.retrieval_prefetch = RetrievalPrefetchProcessor(
            self.rag_context, self.memory_context
        )
        self.llm_print_processor = LLMPrintProcessor(self.recorder)

        self.pipeline = Pipeline([
            self.transport.input(),
            self.stt,
            self.transcription_printer,
            self.memory_ingest,
            self.user_aggregator,
            self.retrieval_prefetch,
            self.rag_context,
            self.memory_context,
            self.llm,
            self.llm_print_processor,
            self.tts,
            self.transport.output(),
            self.assistant_aggregator,
        ])
        self.worker = PipelineWorker(
            self.pipeline,
            params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
            observers=[TraceMetricsObserver(self.recorder)],
        )

    @staticmethod
    def _caller_supported_time_preference(preference: str, caller_text: str) -> str:
        stated_parts = [part for part in _DAY_PARTS if part in preference.lower()]
        if stated_parts and not any(part in caller_text.lower() for part in stated_parts):
            return ""
        return preference

    @staticmethod
    def _say_email(email: str) -> str:
        return email.replace("@", " at ").replace(".", " dot ")

    def _email_requires_confirmation(
        self, email: str, caller_text: str, caller_turn: int
    ) -> bool:
        normalized_email = email.strip().lower()
        affirmative = bool(re.search(
            r"\b(?:yes|correct|right|confirmed|that's right|that is right)\b",
            caller_text,
            re.IGNORECASE,
        ))
        if (
            self._pending_email == normalized_email
            and caller_turn > self._pending_email_turn
            and affirmative
        ):
            self._pending_email = ""
            self._pending_email_turn = 0
            return False
        self._pending_email = normalized_email
        self._pending_email_turn = caller_turn
        return True

    def _create_booking_workflow(self):
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
            """Start or continue the caller's booking workflow; also get its current status.

            Args:
                meeting_date: Caller-provided date in YYYY-MM-DD, otherwise empty.
                meeting_time: Caller-selected time in HH:MM AM/PM, otherwise empty.
                name: Caller-provided name, otherwise empty.
                email: Caller-provided email address, otherwise empty. On the first
                    email turn, call this tool immediately so it can ask for
                    confirmation. After the caller confirms on their next turn,
                    pass the same email again.
                time_preference: Caller preference such as morning, afternoon,
                    evening, after 3 PM, before lunch, or around 5 PM; otherwise empty.
                business: Business or company already provided by the caller.
                industry: Industry or business type already provided by the caller.
                problem: Business problem already provided by the caller.
                volume: Business or call volume already provided by the caller.
                current_system: Current workflow, tool, or system already provided.
                interested_services: Interested service or automation need already
                    provided by the caller.
            """
            started = perf_counter()
            self.recorder.record(
                "tool_call",
                tool="booking_workflow",
                arguments={
                    "meeting_date": meeting_date,
                    "meeting_time": meeting_time,
                    "name": name,
                    "email": email,
                    "time_preference": time_preference,
                    "business": business,
                    "industry": industry,
                    "problem": problem,
                    "volume": volume,
                    "current_system": current_system,
                    "interested_services": interested_services,
                },
                timeout_seconds=120,
                application_retries=0,
            )
            caller_text = self.transcription_printer.latest_text
            caller_turn = self.transcription_printer.turn_id
            time_preference = self._caller_supported_time_preference(
                time_preference, caller_text
            )
            confirm_email = bool(
                not self.public_demo_mode
                and email
                and caller_turn > 0
                and self._email_requires_confirmation(email, caller_text, caller_turn)
            )
            result = await self.booking_session.advance(
                meeting_date=meeting_date,
                meeting_time=meeting_time,
                name=name,
                email="" if confirm_email else email,
                time_preference=time_preference,
                business=business,
                industry=industry,
                problem=problem,
                volume=volume,
                current_system=current_system,
                interested_service=interested_services,
            )
            if confirm_email:
                result = dict(result)
                result["spoken_response"] = (
                    f"I heard {self._say_email(email)}. Is that correct?"
                )
            self.recorder.record(
                "tool_result",
                tool="booking_workflow",
                duration_ms=round((perf_counter() - started) * 1000, 3),
                result={
                    "status": result.get("status"),
                    "booking_confirmed": result.get("booking_confirmed"),
                    "lead_saved": result.get("lead_saved"),
                    "spoken_response": result.get("spoken_response"),
                    "offered_slots": result.get("offered_slots"),
                },
                error_type=(
                    None if result.get("status") != "error" else "BookingWorkflowError"
                ),
            )
            if result.get("status") == "completed":
                self.recorder.finalize_after_speech()

            async def emit_spoken_response():
                await params.llm.push_frame(LLMFullResponseStartFrame())
                await params.llm.push_frame(LLMTextFrame(result["spoken_response"]))
                await params.llm.push_frame(LLMFullResponseEndFrame())

            await params.result_callback(
                result,
                properties=FunctionCallResultProperties(
                    run_llm=False,
                    on_context_updated=emit_spoken_response,
                ),
            )

        return booking_workflow

    async def cancel(self, reason: str = "Session cancelled"):
        self._cancel_requested = True
        if self.runner is not None:
            await self.runner.cancel(reason)

    async def run(self, *, handle_sigint: bool = True, handle_sigterm: bool = False):
        self.runner = WorkerRunner(
            handle_sigint=handle_sigint,
            handle_sigterm=handle_sigterm,
        )
        with use_trace_recorder(self.recorder):
            await self.runner.add_workers(self.worker)
            if self._cancel_requested:
                await self.runner.cancel("Session cancelled before startup")
            await self.runner.run()
