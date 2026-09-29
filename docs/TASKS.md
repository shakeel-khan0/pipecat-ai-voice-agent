# Project Roadmap

## 1. Current Status

The core Agentix AI Voice Receptionist workflow is implemented. Real-time voice interaction, grounded company Q&A, selective persistent caller memory, lead qualification, Calendar booking, Sheets capture, failure safeguards, and automated regression coverage are present in the current repository.

The project is in final validation and public-release preparation. The documented offline suite is passing and the VoiceMem sidecar health boundary has been verified. The public Git repository has been initialized, created on GitHub, and pushed. A fresh Qdrant rebuild and RAG evaluation, final live integration preflight, and privacy-safe demo media remain outstanding. This status describes a production-oriented portfolio and local demonstration project, not a production deployment.

See [Product Requirements](PRD.md), [Architecture](architecture.md), and [Development Rules](RULES.md) for product scope, system design, and change constraints.

## 2. Completed — Core Product

- [x] Real-time local voice interaction through microphone and speaker
- [x] Deepgram speech-to-text and text-to-speech integration
- [x] Silero VAD and caller interruption/barge-in behavior
- [x] Conversational discovery and lead-context collection
- [x] Deterministic company-knowledge and caller-memory routing
- [x] Hybrid dense and sparse company retrieval through Qdrant
- [x] Closed-world company grounding
- [x] Protection against unsupported service and capability claims
- [x] Custom-quote pricing guardrail without invented numeric pricing
- [x] Selective persistent caller memory through the VoiceMem sidecar
- [x] Caller-specific memory isolation and temporary recall context
- [x] Non-blocking, deduplicated, fail-open memory ingestion
- [x] Real Google Calendar availability checks
- [x] Morning, afternoon, and evening preference handling using real returned slots
- [x] Up to three user-facing options within the selected daypart
- [x] 30-minute appointment duration and 30-minute start interval
- [x] Final availability re-check before Calendar event creation
- [x] Calendar event creation with verified confirmation behavior
- [x] Structured Google Sheets lead capture using known conversation fields
- [x] Duplicate-write and uncertain-write protections
- [x] Fail-open conversation behavior for optional RAG and VoiceMem failures
- [x] Sanitized tracing and automated offline regression coverage

## 3. Completed — Engineering Hardening

- [x] Canonical public company knowledge separated from caller memory and workflow state
- [x] Internal pricing research excluded from customer-facing RAG and public documentation
- [x] Direct runtime dependencies declared with pinned compatible versions
- [x] Python 3.11 compatibility documented
- [x] Environment example aligned with current runtime configuration
- [x] Credentials, tokens, traces, caches, local databases, memory storage, and internal notes covered by ignore rules
- [x] Public test fixtures use reserved example domains
- [x] VoiceMem integration pinned to the verified compatible fork revision
- [x] VoiceMem sidecar health endpoint and focused sidecar tests verified
- [x] Qdrant runtime/client versions pinned in setup and dependencies
- [x] Optional Docker Compose orchestration for Qdrant, VoiceMem, and one-shot VoiceMem model initialization
- [x] Apache License 2.0 included
- [x] Public README, PRD, architecture document, and engineering rulebook prepared
- [x] Regression coverage added for grounding, memory filtering, timeouts, caller isolation, booking duration, daypart selection, slot re-checking, lead mapping, and duplicate writes
- [x] Documented offline regression suite passes without live external writes

## 4. Final Validation / Release Preparation

- [ ] Start the pinned Qdrant service and rebuild `agentix_rag_knowledge` from the current canonical knowledge base
- [ ] Run and record a fresh RAG evaluation against the rebuilt collection
- [ ] Live-test representative supported and unsupported capability questions after the rebuild
- [ ] Live-test the custom-quote pricing response and confirm that no numeric pricing is generated
- [ ] Live-test evening availability, including the distinction between the 7:00 PM suggestion cap and a valid 7:30 PM raw start
- [ ] Verify a new eligible VoiceMem write, restart the voice agent, and confirm same-caller recall and different-caller isolation
- [ ] Run one controlled Calendar and Sheets smoke booking with the final configuration and verify the resulting event and complete lead row
- [ ] Re-check README and public documentation claims against the final RAG evaluation and live preflight results
- [ ] Replace the current outdated or privacy-unsafe demo video and thumbnail with reviewed, source-accurate media
- [ ] Perform a final public-file, ignore-rule, credential, secret, trace, and staged-content review

## 5. Public Release Checklist

- [x] Core product behavior has focused automated regression coverage
- [x] Current public documentation describes the implemented system and its limitations
- [x] Repository license is present
- [ ] Fresh RAG evaluation is complete and consistent with public claims
- [ ] Final live voice, memory, Calendar, and Sheets preflight is complete
- [ ] Privacy-safe, current demo media is ready for publication
- [ ] No secrets, credentials, private artifacts, internal notes, or sensitive caller data are staged
- [x] The intended public Git repository is initialized with a reviewed first commit
- [x] The approved repository is created and pushed to GitHub

## 6. Optional Future Enhancements

The following are optional, non-MVP directions rather than commitments:

- [ ] Production SIP or telephony transport
- [ ] Stronger caller identity derived from a trusted telephony source
- [ ] Durable booking and workflow checkpoint persistence
- [ ] Authenticated service boundaries for non-local deployment
- [ ] Production monitoring, alerting, and capacity planning
- [ ] Continuous integration for the offline validation suite
- [ ] Administrative or operational dashboard
- [ ] Additional model or provider options with equivalent grounding safeguards

## 7. Out of Scope

- Native Android or iOS application development
- A full CRM or customer-data platform
- A generalized enterprise contact-center platform
- Fixed public pricing, discount, or quotation engine
- Autonomous medical, legal, financial, or other high-risk decisions
- Multi-tenant identity and authorization
- Unattended production deployment in the current repository
