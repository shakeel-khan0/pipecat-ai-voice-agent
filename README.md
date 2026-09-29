# Agentix AI Voice Receptionist

Turn incoming conversations into answered questions, qualified leads, and booked appointments without losing caller context.

Built for appointment-based businesses, this receptionist speaks naturally with callers, explains services consistently, understands what each caller needs, coordinates an available meeting, and preserves useful context for future conversations.

## Demo

**Public demo media is pending a privacy-safe, current re-recording.**

## The problem

Appointment-based teams lose opportunities when calls go unanswered or customers receive inconsistent information. Staff spend time repeating service details, coordinating schedules, and copying lead information by hand. When a caller returns, earlier context is often missing, forcing the conversation to start over.

The result is slower follow-up, more administrative work, and a less consistent customer experience.

## What it does

- Handles natural, interruptible voice conversations.
- Answers company and service questions from verified business information.
- Understands the caller's business needs and service interests.
- Remembers selected details such as the caller's name, business, industry, meeting-time preference, and service interest.
- Uses remembered context when the same caller returns.
- Checks real appointment availability and offers up to three valid times matching a morning, afternoon, or evening preference.
- Re-checks the selected time before confirming and booking the appointment.
- Captures known lead details and confirmed meeting information in a structured business record.

## How it works

```text
Caller
  -> voice conversation
  -> verified business knowledge and/or caller memory when relevant
  -> appointment availability
  -> slot selection and final re-check
  -> Calendar booking
  -> Sheets lead capture
  -> persistent recall for a returning caller
```

## Quick start

### Prerequisites

- Python 3.11
- A working microphone and speaker; headphones are recommended
- Groq and Deepgram API keys
- Docker with Docker Compose for the optional supporting-infrastructure workflow
- Google Calendar and Sheets APIs enabled with desktop OAuth credentials
- The pinned Agentix-compatible VoiceMem fork described below

### 1. Create the voice-agent environment

```bash
# Windows Git Bash
py -3.11 -m venv .venv
source .venv/Scripts/activate

# Linux (use instead of the two commands above)
# python3.11 -m venv .venv
# source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:

```dotenv
GROQ_API_KEY=...
DEEPGRAM_API_KEY=...
GOOGLE_SHEET_ID=...
```

The current Google integration reads desktop OAuth credentials from `credentials.json`; it does not construct them from environment variables. Put `credentials.json` in the repository root. If the OAuth consent screen is in testing mode, add the signing-in Google account as a test user. The first authorization creates `token.json`. Both files are ignored and must never be published.

### 2. Start supporting infrastructure and build the index

Docker Compose is the preferred convenience option for starting the local supporting infrastructure. It starts only Qdrant, the VoiceMem HTTP sidecar, and a one-shot VoiceMem model initializer; the Pipecat voice agent still runs on the host.

```bash
docker compose up -d
docker compose ps
```

Qdrant remains available at `127.0.0.1:6333`, and VoiceMem remains available at `127.0.0.1:8765`. Named volumes preserve Qdrant data, caller memory, and VoiceMem models. The initializer downloads missing models on the first required startup and skips the download after successful initialization.

To stop the supporting services without deleting their named volumes:

```bash
docker compose down
```

The existing manual workflow remains supported. To start Qdrant manually instead of through Compose:

```bash
docker run -d --name agentix-qdrant -p 6333:6333 \
  -v agentix-qdrant-data:/qdrant/storage qdrant/qdrant:v1.19.1
```

After Qdrant is available through either workflow, build and evaluate the index:

```bash
python -m rag.index
python -m rag.evaluate
```

For an existing container, use `docker start agentix-qdrant`. The first index build downloads and caches the configured parsing and embedding models.

### 3. Start the VoiceMem sidecar

Skip this manual fallback when VoiceMem is already running through Docker Compose. Manual and Docker VoiceMem cannot run simultaneously because both bind `127.0.0.1:8765`.

For the manual workflow, VoiceMem uses a separate environment because its dependency stack is intentionally isolated. In a **separate terminal**, clone the `main` branch of the Agentix-compatible fork and check out the verified immutable revision:

```bash
git clone --branch main https://github.com/shakeel-khan0/VoiceMem.git
cd VoiceMem
git checkout de20ffd49bdaeec0217103c8f5315a6073f9590f

# Windows Git Bash
py -3.11 -m venv .vmvenv
source .vmvenv/Scripts/activate

# Linux (use instead of the two commands above)
# python3.11 -m venv .vmvenv
# source .vmvenv/bin/activate

pip install -e .
bash scripts/download_models.sh models

export GROQ_API_KEY="..."
export TEST_CALLER_ID="demo_001"
python -m uvicorn service.app:app --host 127.0.0.1 --port 8765
```

The sidecar requires `GROQ_API_KEY` and a downloaded local model bundle because it starts in offline model mode. `TEST_CALLER_ID` selects the warm initial caller. Optional `VOICEMEM_MODELS_DIR` and `VOICEMEM_SIDECAR_MEMORY_ROOT` values can point to existing model and private storage directories. By default, caller memory is stored below `service/data/` in hashed caller namespaces.

This project is verified against fork commit [`de20ffd49bdaeec0217103c8f5315a6073f9590f`](https://github.com/shakeel-khan0/VoiceMem/tree/de20ffd49bdaeec0217103c8f5315a6073f9590f). Do not substitute an unverified upstream revision.

Check its health:

```bash
curl http://127.0.0.1:8765/health
```

### 4. Configure Google and run

Create a `Sheet1` tab with these columns in A:K:

```text
Timestamp | Name | Email | Business | Industry | Problem | Volume |
Current System | Interested Services | Meeting Date | Meeting Time
```

Then start the agent:

```bash
export TEST_CALLER_ID="demo_001"
python main.py
```

Use a different stable caller ID when testing caller isolation.

## Architecture

The voice pipeline composes temporary company knowledge and caller memory immediately before the main model turn. Booking is delegated to a stateful workflow that treats Calendar as the availability authority and Sheets as the lead sink. The Pipecat application runs on the host, while Qdrant and the VoiceMem sidecar can run through the optional Compose infrastructure or the existing manual workflow.

For more detail, see the [Product Requirements](docs/PRD.md), [Architecture](docs/architecture.md), [Development Rules](docs/RULES.md), and [Project Roadmap](docs/TASKS.md).

## Tech stack

| Responsibility | Technology |
|---|---|
| Voice pipeline | Pipecat 1.10, Deepgram Flux STT, Silero VAD, Deepgram Aura TTS |
| Main reasoning | Groq `openai/gpt-oss-120b` |
| Business knowledge | Qdrant hybrid dense/sparse retrieval, FastEmbed, Docling |
| Caller memory | VoiceMem sidecar with local E5 embeddings and Groq extraction |
| Booking state | LangGraph with in-memory checkpoints |
| Business systems | Google Calendar and Google Sheets APIs |

## Testing and reliability

The release-validation offline suite provides automated regression coverage for retrieval routing and failure matrices, temporary context boundaries, VoiceMem filtering and adapter behavior, booking interruption/resume, duplicate-write protection, daypart selection, final slot re-checks, Sheets mapping, and trace redaction.

The pinned VoiceMem revision includes focused sidecar tests for health, persistence, dynamic caller creation, and caller isolation. A fresh local RAG evaluation remains pending after rebuilding the Qdrant collection from the current knowledge base.

Run the offline suite without live Groq, Deepgram, Calendar, or Sheets calls:

```bash
python -m unittest \
  tests.test_booking_conversation_e2e \
  tests.test_booking_session \
  tests.test_booking_workflow \
  tests.test_google_sheets \
  tests.test_memory_adapter \
  tests.test_rag_integration \
  tests.test_retrieval_orchestration \
  tests.test_trace_recorder -v
```

`tests/test_calendar.py` is a live Google Calendar diagnostic and is intentionally excluded from the offline suite.

From the pinned VoiceMem checkout, run its focused offline suite with:

```bash
python -m unittest service.test_app -v
```

## Security and privacy

- Secrets, OAuth files, runtime traces, local databases, and caller-memory storage are ignored.
- The VoiceMem service is designed for loopback access and hashes caller IDs into separate storage directories.
- Retrieved company and caller context is copied into one temporary model request; it is not appended permanently to conversation history.
- Contact fields and transactional booking details are excluded from VoiceMem writes.
- Tracing redacts common credentials, IDs, names, emails, and phone numbers. Real caller traces still require manual privacy review before publication because business context may remain.

If a credential was ever committed, `.gitignore` is not enough: remove it from history and rotate it before publishing.

## Current scope and limitations

- One local microphone/speaker caller session per process; no telephony transport.
- Caller identity is supplied manually through `TEST_CALLER_ID`.
- LangGraph booking checkpoints are in memory and do not survive a process restart.
- Qdrant and VoiceMem are local supporting services that can be started through Docker Compose or through the existing manual workflow; the Pipecat application remains host-run.
- Calendar uses the primary calendar, `Asia/Karachi`, 30-minute appointments, and a 10:00 AM-8:00 PM availability-evaluation boundary.
- Raw valid Calendar start times may extend to 7:30 PM; user-facing evening suggestions remain capped at 7:00 PM.
- Main-agent and VoiceMem Groq traffic share the configured key and may encounter provider rate limits.
- External provider behavior, audio hardware, and real barge-in require a live preflight; most automated tests use mocks.

## License

Licensed under the [Apache License 2.0](LICENSE).
