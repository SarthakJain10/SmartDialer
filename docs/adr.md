# Architectural Decision Records (ADRs)

## ADR-001: Separation of Predictive Pacing and Safety Control
* **Context**: Predictive dialing algorithms adjust call volume based on historical metrics, but buggy or over-aggressive heuristics can cause massive over-dialing and illegal call abandon rates.
* **Decision**: Isolate the `PredictivePacingEngine` from the `SafetyController`. The pacing engine only outputs requested call counts; it has no access to the telecom provider. The `SafetyController` acts as a non-bypassable gatekeeper that evaluates real-time agent availability and provider health before approving dial requests.
* **Consequences**: Guarantees system safety invariants regardless of pacing algorithm logic or anomalies.

## ADR-002: In-Memory Repository with CSV Bootstrapping
* **Context**: The prototype requires fast runtime state access and zero external database dependencies for simulation testing.
* **Decision**: Implement `InMemoryRepository` using native Python dictionaries, populated at startup via `agents.csv` and `borrowers.csv`.
* **Consequences**: Enables millisecond execution for simulations and unit tests. Production systems would replace this layer with a transactional relational database (e.g., PostgreSQL).

## ADR-003: Per-Agent In-Memory Async Mutex for Concurrency
* **Context**: Multiple async workers running predictive or progressive dialing loops could attempt to reserve the same available agent concurrently.
* **Decision**: Attach an `asyncio.Lock` instance directly to each `Agent` domain model. Call allocation must acquire this lock before changing status to `RESERVED`.
* **Consequences**: Prevents race conditions and duplicate agent assignments in single-process async execution without heavy database locks.

## ADR-004: Idempotency and Out-of-Order Event Resiliency
* **Context**: Telecom providers deliver events asynchronously via webhooks, often sending duplicate webhooks or out-of-order state updates over unstable networks.
* **Decision**: The `EventProcessor` maintains a set of processed `event_id` keys and enforces state machine transition guards. Duplicate events are silently ignored, and events targeting terminal calls are rejected.
* **Consequences**: Prevents corrupted call states and duplicate agent releases.