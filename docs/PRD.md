# Product Requirements Document

## 1. Product Overview

The Agentix AI Voice Receptionist is an appointment-focused conversational assistant for businesses. It handles natural voice conversations, answers questions from verified company information, gathers useful lead context, checks real appointment availability, books meetings, and preserves selected caller details for future conversations.

The current product is a local portfolio and demonstration implementation. It is designed to show how a reliable receptionist experience can connect conversation, company knowledge, caller continuity, scheduling, and structured lead capture without treating the language model as the authority for external actions.

Implementation details are documented in [Architecture](architecture.md).

## 2. Problem Statement

Appointment-driven teams commonly face several connected problems:

- inbound calls may be missed or answered inconsistently;
- staff repeatedly explain the same services and capabilities;
- lead needs must be gathered manually during each conversation;
- scheduling requires back-and-forth availability checks;
- caller information and meeting details can become fragmented across systems;
- returning callers may need to repeat durable business context;
- conversational AI may invent company capabilities or imply that an external action succeeded when it did not.

The product addresses these problems through interruptible voice interaction, verified company answers, selective caller memory, deterministic appointment handling, and confirmed Calendar and Sheets operations.

## 3. Product Goals

The current implementation must:

1. Conduct clear, natural voice conversations through a local microphone and speaker.
2. Answer company and service questions from canonical Agentix knowledge rather than unsupported model assumptions.
3. Understand and retain relevant caller-provided business context during a conversation.
4. Persist only selected durable caller facts for future sessions.
5. Check real Calendar availability and offer only available appointment times.
6. Complete bookings with a final availability check before event creation.
7. Save known lead and meeting information in a consistent structured record.
8. Confirm external actions only when the relevant integration reports success.
9. Keep the core conversation usable when optional retrieval or memory services fail.
10. Maintain automated regression coverage for grounding, memory, booking, lead capture, and failure handling.

## 4. Non-Goals

The current project is not:

- a general-purpose call-center or contact-center platform;
- a production telephony, SIP, or PBX deployment;
- a native Android or iOS application or a general mobile-development service;
- a CRM replacement or customer-data management platform;
- a multi-tenant identity and access system;
- an autonomous system for medical, legal, financial, or other high-risk decisions;
- a source of fixed public pricing, discounts, performance guarantees, or unsupported company claims;
- a guarantee of availability when external providers or required local services are offline.

## 5. Target Users

### Primary business users

- Appointment-driven service businesses that need consistent reception and scheduling.
- Lead-driven small and medium businesses that want initial needs captured conversationally.
- Teams that want callers to receive verified service information before booking a consultation.
- Businesses that benefit from limited continuity when an identified caller returns.

### Repository and demonstration users

- Recruiters and technical reviewers evaluating an applied conversational-AI system.
- Engineers studying grounded retrieval, persistent caller memory, workflow-controlled booking, and failure-aware integrations.
- Contributors running and validating the project in a controlled local environment.

## 6. Core User Journeys

### A. General company inquiry

The caller asks what Agentix Labs AI does. The system retrieves relevant canonical company knowledge when needed and responds concisely without exposing retrieval internals.

### B. Service or capability question

The caller asks whether the company offers a specific capability. The system checks selected company knowledge. It may answer positively only when the capability is explicitly documented or clearly equivalent; otherwise, it gives a direct negative response without suggesting adjacent capabilities as substitutes.

### C. Returning caller with persisted memory

An identified caller asks about previously supplied durable context. When VoiceMem is available, the system retrieves only that caller's memory and uses it temporarily for the current response. A different caller identity must not receive that context.

### D. Lead qualification

The system asks focused conversational questions to understand the caller's purpose and may capture information the caller provides, such as business, industry, problem, volume, current system, or interested service. It does not fabricate missing fields or assign an unsupported lead score.

### E. Appointment booking

The caller provides a date and either a specific time or daypart preference. The system checks Calendar, offers real matching slots, collects required identity details, confirms uncertain email input, re-checks the selected time, creates the event, and saves the known lead fields to Sheets.

### F. Pricing question

The caller asks about price. The system explains that pricing is custom and depends on discovery and scope. It does not provide invented numeric prices, ranges, discounts, or commercial terms.

### G. Non-critical dependency failure

If RAG or VoiceMem is unavailable, the voice pipeline remains active and avoids presenting unavailable context as verified. Booking integrations report failures without inventing availability, event creation, or lead persistence.

## 7. MVP Scope

The implemented MVP includes:

- real-time local voice interaction;
- Deepgram speech recognition and speech synthesis;
- Silero VAD and caller interruption support;
- conversational reasoning through Groq;
- deterministic routing for company knowledge and caller memory;
- Qdrant hybrid retrieval over canonical company knowledge;
- closed-world grounding for company facts and capabilities;
- selective, caller-specific persistent memory through VoiceMem;
- non-blocking and deduplicated memory ingestion;
- conversational collection of caller and business context;
- real Google Calendar availability checks and event creation;
- morning, afternoon, and evening slot filtering;
- final slot re-check before booking;
- 30-minute appointments;
- structured Google Sheets lead capture;
- exact workflow-controlled booking responses;
- fail-open handling for RAG and VoiceMem;
- sanitized runtime tracing and automated offline regression tests.

## 8. Functional Requirements

| ID | Requirement | Expected behavior |
|---|---|---|
| FR-CONV-01 | Voice conversation | The system must accept local caller audio, process finalized speech, and return spoken responses. |
| FR-CONV-02 | Interruption handling | The caller must be able to interrupt normal spoken output without causing completed booking operations to be replayed. |
| FR-CONV-03 | Conversational context | The system must retain relevant context within the active process and prioritize the caller's latest explicit statement. |
| FR-KNOW-01 | Canonical grounding | Company facts and capability claims must be grounded in the canonical Agentix knowledge base. |
| FR-KNOW-02 | Retrieval routing | Company-knowledge questions must route to RAG while greetings, simple booking fields, and unrelated small talk may skip retrieval. |
| FR-KNOW-03 | Supported capabilities | The system may answer positively only when selected knowledge explicitly documents the requested capability or a clear equivalent. |
| FR-KNOW-04 | Unsupported capabilities | An undocumented capability must receive a direct negative answer without inferred variants, integrations, alternatives, or adjacent-service claims. |
| FR-KNOW-05 | Temporary context | Retrieved knowledge must apply only to the current model request and must not be permanently appended to conversation history. |
| FR-MEM-01 | Eligible memory | Only finalized caller statements containing approved durable identity, business, industry, meeting-preference, or service-interest information may be queued for persistence. |
| FR-MEM-02 | Excluded memory | Contact details, transactional booking data, metrics, workflows, generic pain points, greetings, questions, assistant content, and internal context must not be persisted. |
| FR-MEM-03 | Caller isolation | Persistent memory retrieval and storage must remain separated by caller identity. |
| FR-MEM-04 | Non-blocking writes | Memory ingestion must not block the live conversational response path and must avoid duplicate ingestion. |
| FR-LEAD-01 | Lead context | The system must preserve caller-provided lead fields during the active booking conversation and must not fabricate missing values. |
| FR-BOOK-01 | Date handling | The system must request and validate a meeting date that is not in the past. |
| FR-BOOK-02 | Availability authority | The system must query Google Calendar before presenting available appointment slots. |
| FR-BOOK-03 | Daypart suggestions | When a daypart is selected, the system must offer up to three real Calendar-returned slots within the configured user-facing window. |
| FR-BOOK-04 | Appointment duration | Created appointments must be 30 minutes long. |
| FR-BOOK-05 | Final re-check | The selected time must be checked again immediately before event creation. |
| FR-BOOK-06 | Booking confirmation | The system must confirm a meeting only after Calendar event creation succeeds. |
| FR-BOOK-07 | Contact confirmation | Newly supplied or uncertain email input must be confirmed by the caller on a later turn before final booking. |
| FR-LEAD-02 | Sheets mapping | Known lead and meeting fields must be appended in the expected 11-column Sheets order; unknown fields remain empty. |
| FR-LEAD-03 | Write verification | A Sheets write must not be reported as successful unless the API confirms the complete row. |
| FR-REL-01 | RAG failure | RAG failure must not crash the voice pipeline or authorize unsupported company claims. |
| FR-REL-02 | Memory failure | VoiceMem failure must not stop the core conversation or booking workflow. |
| FR-REL-03 | External-action truthfulness | The system must not claim availability, booking, or lead persistence without the corresponding verified tool result. |

## 9. Knowledge and Grounding Requirements

The canonical Agentix knowledge base is the authority for public company facts, services, and capabilities.

- A documented capability may receive a positive answer.
- An undocumented specific capability must receive a direct negative answer.
- Broad service categories must not be expanded into narrower platforms or variants without explicit evidence.
- Caller memory must never be treated as evidence of an Agentix capability.
- General model knowledge must not fill gaps in company information.
- Numeric prices, discounts, packages, guarantees, and commercial terms must not be invented.
- Pricing questions must follow the custom-quote policy: scope depends on the workflow, integrations, usage, deployment requirements, and support needs.

## 10. Booking Requirements

- Relative and explicit dates are resolved in the configured `Asia/Karachi` timezone.
- The caller may request a specific time or select morning, afternoon, or evening.
- Calendar evaluates availability between 10:00 AM and 8:00 PM.
- Appointments are 30 minutes long with 30-minute candidate start intervals.
- Raw valid starts may extend through 7:30 PM when free.
- User-facing daypart windows are:
  - Morning: 10:00 AM–12:30 PM
  - Afternoon: 2:00 PM–4:00 PM
  - Evening: 5:00 PM–7:00 PM
- No more than three useful daypart options are presented, and every option must come from Calendar.
- If no slot exists in the requested daypart, the system must not substitute a slot from another window without caller input.
- The selected slot must be re-checked before the Calendar event is created.
- The booking is confirmed only after successful Calendar event creation.
- Known lead and meeting information is sent to Google Sheets as part of the successful booking flow.
- If the Calendar event succeeds but Sheets persistence fails, the meeting remains confirmed while lead-save completion is reported accurately.

## 11. Memory Requirements

- Memory must be caller-specific and persist across voice-agent process restarts when the VoiceMem sidecar and its storage are available.
- Only selected durable caller facts may be considered for persistence.
- VoiceMem's normal extraction remains responsible for producing its Left Brain and Right Brain memory representations.
- Retrieved memory must be temporary context for an appropriate caller-history turn.
- A caller's current explicit statement must take priority over stale remembered information.
- Caller memory must not replace active booking state, Calendar availability, tool results, or canonical company knowledge.
- Memory writes must be asynchronous, deduplicated, serialized, and fail-open.
- A connection or retrieval failure may disable memory for the current voice-agent process; the conversation must continue without it.
- The current caller identity is manually supplied for controlled local testing and is not a production telephony identity.

## 12. Non-Functional Requirements

- **Correctness:** Verified company knowledge and external tool results take precedence over plausible model-generated answers.
- **Continuity:** Failure of optional retrieval or memory services must not terminate the voice conversation.
- **Responsiveness:** Background memory ingestion must not block the primary response path.
- **Separation of concerns:** Company knowledge, caller memory, booking state, conversation history, and external systems must remain distinct authority domains.
- **Idempotence:** Duplicate caller frames or repeated workflow calls must not create duplicate memory writes, Calendar events, or Sheets rows.
- **Testability:** Core routing, grounding, memory, booking, lead mapping, failure, and privacy behavior must remain covered by offline tests.
- **Security:** Secrets and OAuth artifacts must not be stored in source control.
- **Privacy:** Caller-memory writes must exclude contact data and transactional booking details, and traces must redact common sensitive identifiers.
- **External-action clarity:** User-facing responses must distinguish verified success, incomplete persistence, and failure.
- **Public safety:** Repository documentation and tracked artifacts must not expose private credentials, internal pricing research, or unreviewed caller data.
- **Deployment flexibility:** Docker Compose may start the Qdrant and VoiceMem supporting infrastructure, while the Pipecat application remains host-run and the existing manual service-startup workflow remains supported.

## 13. Success Criteria

The MVP is successful when:

- supported company questions are answered from verified knowledge;
- unsupported specific services are rejected without hallucinated alternatives;
- normal conversation remains usable when RAG or VoiceMem is unavailable;
- an identified returning caller can recall eligible persisted context without cross-caller leakage;
- a caller receives only real Calendar-returned availability;
- a selected slot is re-checked and a 30-minute event is created successfully;
- Calendar confirmation is not spoken before event creation succeeds;
- known lead fields reach the expected Sheets columns without fabricated values;
- incomplete Sheets writes are not reported as successful;
- duplicate or interrupted booking interactions do not create repeated external writes;
- the documented offline regression suite passes.

These criteria measure implemented behavior. They do not assert conversion, revenue, cost, or response-time improvements.

## 14. Current Constraints

- Audio uses a local microphone and speaker, with one caller session per voice-agent process.
- Caller identity is manually supplied for testing.
- Qdrant and VoiceMem are separate local supporting services that can be started through Docker Compose or manually; the Pipecat application runs on the host.
- Groq, Deepgram, Google Calendar, and Google Sheets are external provider dependencies.
- The main agent and VoiceMem extraction can share the configured Groq quota.
- Booking checkpoints and active conversation state are held in process and do not survive restart.
- Google Calendar uses the primary calendar and the configured local timezone.
- Public fixed pricing is not defined; pricing requires discovery and scope confirmation.
- Production telephony, multi-tenant identity, durable workflow persistence, and unattended production deployment are not included.

## 15. Future Considerations

Possible post-MVP directions include production telephony or SIP transport, stronger caller identity, durable workflow checkpoints, authenticated service boundaries, production monitoring, and an optional administrative interface. These are not implemented capabilities of the current repository.
