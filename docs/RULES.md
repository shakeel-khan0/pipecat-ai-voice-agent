# Development Rules

These rules apply to human contributors and AI coding assistants working on the Agentix AI Voice Receptionist. They protect the repository's grounded knowledge, caller-memory isolation, booking correctness, external integrations, and public-safety boundaries.

## 1. General Engineering Principles

- Prefer the smallest correct change that fully addresses the verified requirement.
- Inspect the current implementation before editing. Current source code and tests are the implementation source of truth.
- Identify the root cause before changing behavior; do not mask symptoms with broad fallbacks or arbitrary constants.
- Preserve working behavior unless the task explicitly authorizes changing it.
- Do not refactor unrelated code while fixing a narrow issue.
- Keep deterministic safeguards around routing, booking, persistence, and external actions.
- Update the relevant documentation when an intentional behavior change makes an existing claim inaccurate.
- Do not invent requirements, product capabilities, data, integrations, benchmarks, or deployment guarantees.
- When requirements are ambiguous and different interpretations would materially change behavior, stop and request clarification.

## 2. Change-Scope Rules

Before changing code:

1. Identify the exact requested issue and its observable failure.
2. Identify the modules that directly own that behavior.
3. Locate the tests that currently protect the affected path.
4. Determine the smallest safe modification and its regression risk.

Do not:

- rename, move, or reorganize modules without a functional need;
- perform unrelated cleanup or modernization;
- upgrade dependencies as part of an unrelated bug fix;
- redesign architecture during a narrowly scoped change;
- alter working RAG, VoiceMem, booking, Calendar, Sheets, audio, or prompt behavior unless required by the task;
- replace a targeted fix with a new parallel implementation of the same responsibility.

If the requested result requires a broad architectural change, a new authority boundary, or meaningful unrelated behavior changes, stop and explain the impact before implementation.

## 3. Architecture Boundaries

| Boundary | Authoritative responsibility |
|---|---|
| RAG | Public Agentix company facts, services, and documented capabilities |
| VoiceMem | Selected persistent caller facts and preferences |
| Booking session and LangGraph | Transactional appointment fields and workflow progress |
| Groq LLM | Conversation, reasoning, and tool selection—not external-system truth |
| Google Calendar | Real appointment availability and event-creation outcome |
| Google Sheets | Structured lead-row persistence outcome |

- Do not move responsibility between these layers casually.
- Do not use RAG as caller memory.
- Do not use VoiceMem as booking state or as evidence of company capabilities.
- Do not treat conversation history as proof of Calendar or Sheets success.
- Do not let the LLM fabricate external-system results.
- Current caller statements take precedence over stale caller memory.
- Verified Calendar and Sheets results take precedence over model-generated language about external actions.
- Docker Compose is an infrastructure-only convenience for Qdrant and VoiceMem; the main Pipecat application remains host-run unless an explicitly scoped future task changes that boundary.
- Keep the manual Qdrant and VoiceMem workflow functional, and do not make application code depend on Docker Compose.
- Preserve the host-facing Qdrant and VoiceMem service endpoints unless a change is explicitly authorized.

## 4. Company-Knowledge Grounding Rules

- The canonical public Agentix knowledge base is the authority for company facts and offerings.
- Company facts must not be supplied from the base model's general knowledge.
- A documented capability may receive a positive answer.
- An undocumented specific capability must receive a direct negative answer.
- Do not infer a narrower platform, variant, service, or use case from an adjacent broad capability.
- Do not add related integrations, alternatives, referrals, or company-focus claims to an unsupported-service answer.
- Do not invent clients, case studies, outcomes, certifications, partnerships, guarantees, pricing, discounts, or capabilities.
- Do not generate numeric pricing unless it is explicitly approved in the canonical public knowledge source.
- Pricing questions must follow the current custom-quote policy.
- Internal pricing research must remain outside customer-facing RAG and public product claims.
- Retrieval context must remain temporary and must not be permanently added to conversation history.
- Any change to company knowledge, retrieval routing, selection, scoring, or grounding requires focused RAG tests and a fresh RAG evaluation after rebuilding the relevant collection.

## 5. Booking Rules

- Never fabricate appointment availability or hardcode fake demo slots.
- Query real Google Calendar availability before offering a slot.
- Preserve the current 30-minute appointment duration and 30-minute slot interval unless an explicit task changes them.
- Preserve the current Calendar evaluation boundary of 10:00 AM–8:00 PM.
- Preserve the user-facing daypart windows:
  - Morning: 10:00 AM–12:30 PM
  - Afternoon: 2:00 PM–4:00 PM
  - Evening: 5:00 PM–7:00 PM
- Offer at most three useful daypart options and only from Calendar-returned availability.
- Raw valid Calendar starts may extend through 7:30 PM, but evening suggestions remain capped at 7:00 PM.
- Re-check the selected slot immediately before event creation.
- Do not claim that a meeting is confirmed before Calendar confirms event creation.
- Save the lead only through the current workflow and preserve the existing field mapping.
- Do not fabricate missing lead values.
- Preserve duplicate-write protection, serialized session execution, and exactly-once behavior where currently implemented.
- Do not automatically retry an external write when its outcome may be uncertain.
- Preserve the distinction between a confirmed Calendar event and an incomplete Sheets write.

## 6. Memory Rules

- Consider only finalized caller transcripts for memory ingestion.
- Persist only the approved durable categories: caller name, business or company, industry or business type, meeting-time preference, and interested service or core automation need.
- Do not silently broaden memory eligibility.
- Do not persist email addresses, phone numbers, credentials, secrets, lead metrics, current tools or workflows, generic pain points, booking transactions, system prompts, RAG context, tool output, or assistant-generated content.
- Preserve caller isolation through the configured caller identity.
- Keep retrieved memory temporary and subordinate to the caller's current explicit statement.
- Keep memory writes deduplicated, serialized, non-blocking, and fail-open.
- VoiceMem failure must not stop the core conversation or booking workflow.
- Do not build a second fact-extraction system; eligible content must continue through VoiceMem's established extraction path.
- Do not change VoiceMem models, storage, retrieval behavior, sidecar endpoints, or dependency environment during unrelated work.
- Preserve the separation between the main voice-agent environment and the VoiceMem environment.

## 7. Error-Handling Rules

- Fail explicitly for critical external actions and return an accurate user-facing outcome.
- Fail open only where the architecture intentionally allows it, such as RAG and VoiceMem availability.
- Never report availability, event creation, lead persistence, or any other external action as successful without confirmation.
- Preserve useful fallback behavior without converting an error into fabricated success.
- Log actionable operation and error types without exposing caller content, credentials, tokens, IDs, or request payloads unnecessarily.
- Do not introduce blanket exception handling that silently suppresses programming errors.
- Distinguish connection failures, operation timeouts, invalid responses, and confirmed provider failures when their recovery semantics differ.
- Do not aggressively retry non-idempotent or uncertain Calendar and Sheets writes.
- Keep the live voice path usable when an optional subsystem fails.

## 8. Dependency Rules

- Use existing libraries and standard-library functionality before adding a dependency.
- A new direct dependency requires a clear runtime or testing need and must be declared explicitly.
- Preserve pinned versions where the repository relies on them for reproducibility.
- Do not broadly upgrade unrelated packages during a bug fix.
- Preserve Python 3.11 compatibility unless an explicit task changes the supported runtime.
- Run `pip check` after dependency changes.
- Run relevant offline tests after any dependency change.
- Keep VoiceMem isolated from the main environment because its dependency stack and runtime are intentionally separate.
- Do not substitute an unverified VoiceMem revision for the pinned compatible fork revision.

## 9. Coding Standards

- Write readable, focused Python consistent with the surrounding module.
- Keep functions small enough to express one clear responsibility.
- Use type hints where they improve an existing public boundary or match surrounding code.
- Prefer descriptive names over abbreviations or comments that compensate for unclear code.
- Avoid unnecessary abstraction, parallel frameworks, and speculative extension points.
- Prefer deterministic logic for critical routing, filtering, validation, and workflow decisions.
- Never hardcode secrets, credentials, private IDs, caller data, fake business facts, or fake slots.
- Do not add machine-specific absolute paths.
- Comments and docstrings should explain why a non-obvious safeguard exists, not restate obvious code.
- Remove or correct stale comments when the behavior they describe changes.
- Do not impose a new formatter, linter, or style tool unless the repository explicitly adopts it.

## 10. Testing Rules

- Add or update focused tests for every behavior change and bug fix.
- Where practical, add a regression case that reproduces the verified failure before the fix.
- Run the focused test module after each targeted change.
- Run the full documented offline suite after significant or cross-cutting changes.
- Mock Calendar and Sheets operations in automated tests; normal test runs must not perform destructive or state-changing live writes.
- Keep live Calendar diagnostics separate from the offline suite.
- Run RAG evaluation after changing canonical knowledge, indexing, retrieval routing, selection, or scoring.
- Perform live provider preflight only after offline tests pass and only when explicitly appropriate for the task.
- Test failure paths as well as successful paths, especially timeouts, malformed responses, duplicate calls, and partial external success.
- Preserve reserved example domains such as `example.com`, `example.org`, and `example.net` in public test fixtures.
- Do not hardcode a test count in this rulebook; the suite evolves.

## 11. Security and Privacy Rules

- Never commit `.env` files, API keys, OAuth credentials, OAuth tokens, private keys, or certificates.
- Never expose spreadsheet identifiers, account identifiers, event identifiers, or caller identifiers unnecessarily.
- Never commit private traces, caller recordings, sensitive transcripts, local databases, or caller-memory storage.
- Keep internal pricing research and local implementation notes ignored and out of public documentation.
- Use synthetic data and reserved domains in tests and examples.
- Keep VoiceMem bound to a trusted local boundary unless authentication is intentionally designed and reviewed.
- Treat trace redaction as a safeguard, not permission to publish traces without manual review.
- Review and sanitize demo images, audio, and video before tracking or publishing them.
- If a secret was ever committed, removing the file is insufficient; remove it from history and rotate the credential.
- Inspect `.gitignore` and staged files before every public release.

## 12. Documentation Rules

- `README.md` is the product overview, setup guide, and repository entry point.
- `docs/PRD.md` defines what the product must do and why.
- `docs/architecture.md` explains how current system components work together.
- `docs/RULES.md` defines engineering and change-control rules.
- [`docs/TASKS.md`](TASKS.md) contains roadmap and status information rather than current-system truth.
- Internal implementation history and working notes must remain local-only.
- Do not create competing sources of truth for the same behavior.
- Update the authoritative document when an intentional code change makes it stale.
- Do not duplicate low-level implementation details across every public document.
- Public documentation must not include secrets, internal pricing material, private caller data, machine-specific paths, or unverified claims.
- Treat current source and tests as authoritative when historical notes conflict with implemented behavior.

## 13. Git / Repository Rules

- Use Git Bash/Linux-style commands in public documentation so commands remain consistent across supported setup instructions.
- Keep commits scoped, reviewable, and meaningful.
- Inspect the working tree and staged diff before committing.
- Verify that credentials, secrets, traces, local databases, memory stores, caches, internal notes, and unreviewed media are not staged.
- Do not rewrite unrelated history during normal feature or bug-fix work.
- Do not commit generated caches, virtual environments, runtime storage, or provider tokens.
- Do not initialize, commit, push, tag, or modify remotes unless the task explicitly requests it.
- Preserve unrelated user changes in a dirty working tree.

## 14. AI Coding Assistant Checklist

Before every modification, answer:

1. What exactly was requested?
2. Which files actually need to change?
3. What working behavior must remain untouched?
4. Is there an existing test for this path?
5. Am I introducing an unsupported assumption or invented value?
6. Does this affect RAG, VoiceMem, booking, Calendar, Sheets, audio, prompts, or another external action boundary?
7. Have I added focused regression coverage where behavior changed?
8. Did the full relevant offline suite pass?
9. Did I touch anything outside the authorized scope?
10. Do the public documents now conflict with the current code?

If any answer exposes unclear scope, unverified behavior, privacy risk, or architectural impact, stop and resolve it before proceeding.
