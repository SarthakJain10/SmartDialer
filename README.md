# SmartDialer Technical Prototype

A modular Python prototype of an outbound dialing system designed to balance **agent utilization** with **call safety**.

The system demonstrates two dialing strategies:

* **Progressive Dialing** — one outbound call per available agent.
* **Heuristic Predictive Pacing** — starts additional calls ahead of agent availability based on recent system behavior.

A separate, non-bypassable **Safety Controller** sits between the pacing logic and the telecom provider to prevent unsafe over-dialing.

The prototype also demonstrates explicit agent and call state machines, concurrency-safe agent reservation, provider health monitoring, asynchronous event processing, duplicate-event handling, and recovery from unreliable provider behavior.

---

## 1. The Dialing Problem

In outbound call centers, agents can spend significant time waiting for outbound calls to connect.

A traditional **Progressive Dialer** solves this safely by placing at most one outbound call for each available agent:

```text
1 Available Agent ──► 1 Outbound Call
```

This approach is predictable and safe, but agents may remain idle while calls are ringing, busy, unanswered, or failed.

A **Predictive Dialer** attempts to improve utilization by starting calls before agents become available:

```text
1 Available Agent ──► Multiple Outbound Calls
```

This can significantly improve utilization, but introduces a critical safety problem:

```text
More borrowers answer than available agents
                    │
                    ▼
          Connected calls without
             available agents
                    │
                    ▼
             Abandoned calls
```

The purpose of SmartDialer is therefore not simply to "dial more."

It is to **dial more intelligently while maintaining a hard safety boundary around agent capacity**.

---

## 2. High-Level Architecture

The system follows a strict unidirectional flow:

```text
                     ┌──────────────────────┐
                     │      Campaign       │
                     └──────────┬───────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │    Pacing Engine    │
                     │                      │
                     │ Progressive /       │
                     │ Predictive           │
                     └──────────┬───────────┘
                                │
                         Dialing Request
                                │
                                ▼
                     ┌──────────────────────┐
                     │  Safety Controller  │
                     │                      │
                     │ Capacity & Health   │
                     │ Safety Gate          │
                     └──────────┬───────────┘
                                │
                         Approved Calls
                                │
                                ▼
                     ┌──────────────────────┐
                     │    Call Allocator   │
                     │                      │
                     │ Agent Reservation   │
                     │ Borrower Assignment │
                     └──────────┬───────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │   Telecom Provider  │
                     │                      │
                     │ Mock Provider A/B    │
                     └──────────┬───────────┘
                                │
                       Asynchronous Events
                                │
                                ▼
                     ┌──────────────────────┐
                     │   Event Processor    │
                     │                      │
                     │ Deduplication        │
                     │ State Validation     │
                     │ Idempotent Handling  │
                     └──────────────────────┘
```

### Component Responsibilities

| Component                    | Responsibility                                                                                                                                           |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Progressive Dialer**       | Places calls conservatively using a 1:1 agent-to-call strategy.                                                                                          |
| **Predictive Pacing Engine** | Estimates how aggressively the system can dial using recent answer behavior and current system conditions.                                               |
| **Safety Controller**        | Acts as the mandatory safety gate. It evaluates the pacing request against available capacity and provider health before allowing calls to be allocated. |
| **Call Allocator**           | Safely reserves agents and assigns borrowers to calls.                                                                                                   |
| **Telecom Provider**         | Provides an abstract interface for initiating calls and receiving call events.                                                                           |
| **Mock Provider A**          | Fast and relatively reliable provider used for normal simulations.                                                                                       |
| **Mock Provider B**          | Unreliable provider that introduces latency, failures, duplicate events, and out-of-order events.                                                        |
| **Event Processor**          | Processes provider events, prevents duplicate processing, and applies valid call-state transitions.                                                      |
| **Provider Health Monitor**  | Tracks recent provider behavior and exposes a health status used by the Safety Controller.                                                               |
| **Worker Recovery**          | Detects and cleans up stale or stranded operations caused by worker failures.                                                                            |

---

## 3. Safety Controller

The Safety Controller is the most important architectural boundary in the system.

The pacing engine is allowed to **request** additional calls, but it does not have authority to place them directly.

For example:

```text
Predictive Pacing Engine
        │
        │ "I recommend 20 calls"
        ▼
Safety Controller
        │
        │ "Only 8 are currently safe"
        ▼
Call Allocator
        │
        ▼
Telecom Provider
```

The Safety Controller can:

* approve the requested number of calls;
* reduce the requested number;
* reject new calls;
* reduce dialing aggressiveness when provider health deteriorates;
* fall back toward progressive dialing when required.

This ensures that an error or overly aggressive prediction from the pacing engine cannot directly translate into uncontrolled outbound dialing.

---

## 4. Core System Invariants

The prototype is designed around several important invariants.

### Safety Invariant

All dialing requests must pass through the `SafetyController` before reaching the `CallAllocator`.

The predictive pacing engine cannot directly invoke the telecom provider.

### Agent Reservation Invariant

Two concurrent workers must not be able to successfully reserve the same agent.

The prototype uses an `asyncio.Lock` per agent to protect reservation operations within the process.

### Terminal Call Invariant

Calls that reach a terminal state cannot transition back into an active state.

Terminal states include:

```text
COMPLETED
FAILED
CANCELLED
```

### Event Idempotency

Telecom events contain a unique `event_id`.

If the same event is received multiple times, the event processor ignores subsequent copies rather than applying the state transition repeatedly.

### Provider Isolation

Dialer logic depends on the `TelecomProvider` abstraction rather than the implementation details of a particular provider.

This allows different provider behaviors to be simulated without changing the dialing logic.

---

## 5. State Machines

### Agent State Machine

The primary agent lifecycle is:

```text
OFFLINE
   │
   ▼
AVAILABLE
   │
   ▼
RESERVED
   │
   ▼
DIALING
   │
   ▼
CONNECTED
   │
   ▼
WRAP_UP
   │
   ▼
AVAILABLE
```

Agents may also transition to states such as `PAUSED` depending on the lifecycle and simulation behavior.

See [`docs/agent_state_machine.md`](docs/agent_state_machine.md) for the detailed transition rules.

### Call State Machine

The primary call lifecycle is:

```text
QUEUED
   │
   ▼
RESERVED
   │
   ▼
INITIATED
   │
   ▼
RINGING
   │
   ▼
ANSWERED
   │
   ▼
CONNECTED
   │
   ▼
COMPLETED
```

Calls may also transition to terminal failure states:

```text
FAILED
CANCELLED
```

The event processor validates transitions so that invalid or stale provider events cannot arbitrarily move a call back into an earlier lifecycle state.

See [`docs/call_state_machine.md`](docs/call_state_machine.md) for detailed transition rules.

---

## 6. Project Structure

```text
smart-dialer/
│
├── app/
│   ├── domain/
│   │   ├── agent.py
│   │   ├── borrower.py
│   │   ├── call.py
│   │   ├── enums.py
│   │   └── events.py
│   │
│   ├── providers/
│   │   ├── base.py
│   │   ├── provider_a.py
│   │   └── provider_b.py
│   │
│   ├── repositories/
│   │   └── csv_repository.py
│   │
│   ├── services/
│   │   ├── call_allocator.py
│   │   ├── event_processor.py
│   │   ├── predictive_pacing.py
│   │   ├── progressive_dialer.py
│   │   ├── provider_health.py
│   │   ├── safety_controller.py
│   │   └── worker_recovery.py
│   │
│   └── main.py
│
├── data/
│   ├── agents.csv
│   └── borrowers.csv
│
├── docs/
│   ├── adr.md
│   ├── agent_state_machine.md
│   ├── architecture.md
│   └── call_state_machine.md
│
├── simulation/
│   ├── load_test.py
│   ├── metrics.py
│   ├── run.py
│   └── scenarios.py
│
├── tests/
│   ├── test_agent_states.py
│   ├── test_call_states.py
│   ├── test_concurrency.py
│   ├── test_events.py
│   └── test_safety.py
│
├── .gitignore
├── pytest.ini
├── README.md
└── requirements.txt
```

---

## 7. Data Model

The prototype intentionally avoids an external database.

Initial test data is loaded from CSV files:

```text
data/
├── agents.csv
└── borrowers.csv
```

Runtime state is maintained in memory through the repository layer.

This keeps the prototype deterministic, easy to run locally, and focused on the dialing logic rather than database infrastructure.

---

## 8. Setup & Installation

### Prerequisites

* Python 3.11+ recommended
* `pip`

### Installation

Clone the repository and navigate to the project root:

```bash
cd smart-dialer
```

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate the virtual environment.

**macOS / Linux:**

```bash
source .venv/bin/activate
```

**Windows:**

```powershell
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

# 9. Running Tests

Run the complete test suite with:

```bash
pytest -v
```

The tests cover areas including:

* agent state transitions;
* call state transitions;
* concurrent agent reservation;
* duplicate and out-of-order provider events;
* safety-controller capacity limits;
* idempotent event handling.

---

# 10. Running Simulations

The simulation framework provides several ways to demonstrate the system.

## 10.1 Progressive Dialing

Runs the conservative 1:1 dialing strategy using Mock Provider A.

```bash
python -m simulation.run --mode progressive --provider A --agents 15 --borrowers 30 --duration 5
```

This provides a baseline for comparison with predictive dialing.

---

## 10.2 Predictive Dialing

Runs the heuristic predictive pacing strategy with the Safety Controller enabled.

```bash
python -m simulation.run --mode predictive --provider A --agents 15 --borrowers 30 --duration 5
```

The predictive engine can request additional calls, but all requests still pass through the Safety Controller.

---

## 10.3 Progressive vs. Predictive Comparison

Runs progressive and predictive modes using comparable simulation conditions to demonstrate differences in:

* agent utilization;
* completed calls;
* dialing activity;
* safety behavior.

```bash
python -m simulation.run --mode compare
```

The comparison is intended to demonstrate the trade-off between conservative dialing and predictive utilization.

---

## 10.4 Unreliable Telecom Provider

Mock Provider B introduces less predictable external behavior, including:

* increased latency;
* occasional failures;
* duplicate events;
* out-of-order events.

Run:

```bash
python -m simulation.run --mode predictive --provider B --agents 15 --borrowers 30 --duration 5
```

This demonstrates that the dialer does not assume telecom providers always deliver events cleanly or in order.

---

## 10.5 Concurrency Load Test

Stress-tests agent reservation under concurrent worker contention.

```bash
python -m simulation.load_test
```

The important invariant demonstrated by this test is:

```text
N concurrent workers
        │
        ▼
Same available agent
        │
        ▼
At most ONE successful reservation
```

---

# 11. FastAPI Server

The prototype also exposes a small REST API for inspecting runtime state and triggering simulations.

Start the server with:

```bash
uvicorn app.main:app --reload
```

Available endpoints include:

| Method | Endpoint          | Description                                    |
| ------ | ----------------- | ---------------------------------------------- |
| `GET`  | `/health`         | Returns system health information.             |
| `GET`  | `/agents`         | Returns the current in-memory state of agents. |
| `GET`  | `/calls`          | Returns the current call records.              |
| `POST` | `/simulation/run` | Triggers a simulation run.                     |

The API is primarily provided as an operational/demo interface. The core dialing behavior is implemented independently of FastAPI.

---

# 12. Mock Telecom Providers

The application uses a provider abstraction so that dialing logic does not depend on a specific telecom implementation.

### Mock Provider A

Designed to represent a relatively healthy provider:

* low latency;
* high reliability;
* low failure rate;
* predictable event delivery.

### Mock Provider B

Designed to represent an unreliable provider:

* higher latency;
* occasional failures;
* duplicate events;
* out-of-order events.

This allows the same dialer implementation to be tested under different provider conditions.

---

# 13. Provider Health & Fallback

Provider behavior is monitored by the `ProviderHealthMonitor`.

The resulting health status is used by the Safety Controller to adjust dialing behavior.

Conceptually:

```text
Healthy
   │
   ▼
Normal predictive dialing

Degraded
   │
   ▼
Reduced dialing aggressiveness

Critical
   │
   ▼
Conservative / progressive behavior

Unavailable
   │
   ▼
Reject new dialing
```

This prevents a deteriorating telecom provider from being treated as if it were operating normally.

---

# 14. Handling Asynchronous Provider Events

Telecom events are treated as unreliable external input.

The provider may send events such as:

```text
ANSWERED
ANSWERED
COMPLETED
```

or:

```text
COMPLETED
ANSWERED
RINGING
```

The `EventProcessor` therefore:

1. identifies duplicate events using `event_id`;
2. validates the current call state;
3. applies only valid state transitions;
4. ignores stale or duplicate events;
5. keeps the call lifecycle in a consistent state.

This prevents external event ordering from becoming an assumption inside the core application.

---

# 15. Worker Failure & Recovery

Workers may fail while processing calls.

For example:

```text
Worker
   │
   ▼
Call = ANSWERED
   │
   X
Worker crashes
```

The `WorkerRecovery` service is responsible for detecting stale operations and cleaning up stranded state so that agents or calls do not remain permanently stuck.

This is implemented as a simplified recovery mechanism suitable for the prototype.

---

# 16. Prototype vs. Production

This project intentionally focuses on demonstrating the core dialing and safety architecture rather than building a production telephony platform.

| Area                    | Prototype                                  | Production                                                    |
| ----------------------- | ------------------------------------------ | ------------------------------------------------------------- |
| **Data Persistence**    | CSV bootstrap + in-memory runtime state    | PostgreSQL or another transactional database                  |
| **Concurrency**         | `asyncio.Lock` per agent within a process  | Distributed locking / transactional reservation across nodes  |
| **Messaging**           | In-memory asynchronous tasks and callbacks | Kafka, RabbitMQ, SQS, or another durable message broker       |
| **Telecom Integration** | Mock Provider A and Mock Provider B        | Production telephony provider APIs and webhooks               |
| **Recovery**            | Simplified stale-operation recovery        | Durable leases, heartbeats, retries, and distributed recovery |
| **Observability**       | Simulation metrics and logging             | Centralized metrics, tracing, alerting, and dashboards        |
| **Deployment**          | Local Python process                       | Horizontally scalable distributed services                    |

The prototype deliberately avoids production infrastructure so that the core design decisions remain easy to understand and evaluate.

---

# 17. Key Design Decisions

The main architectural decisions are documented in [`docs/adr.md`](docs/adr.md).

The most important decisions are:

1. **Separate pacing from safety.**
   Predictive logic can recommend more calls but cannot bypass the Safety Controller.

2. **Use explicit state machines.**
   Agent and call lifecycles are represented explicitly to make invalid transitions detectable.

3. **Isolate telecom providers behind an interface.**
   Provider-specific behavior should not leak into the dialing logic.

4. **Treat provider events as unreliable.**
   Duplicate and out-of-order events are expected rather than treated as exceptional assumptions.

5. **Use concurrency-safe reservation.**
   Agent allocation must remain safe even when multiple workers attempt to reserve agents simultaneously.

6. **Use simulation to validate behavior.**
   Progressive and predictive modes can be compared under controlled conditions, while unreliable providers and concurrency tests exercise failure scenarios.

---

## 18. What This Prototype Demonstrates

The prototype focuses on one central principle:

> **Predictive dialing can improve utilization, but prediction must never be allowed to override safety.**

The system therefore separates the responsibilities:

```text
Pacing Engine
    │
    │ "What should we dial?"
    ▼
Safety Controller
    │
    │ "What are we actually allowed to dial?"
    ▼
Call Allocator
    │
    │ "Which agents can safely be reserved?"
    ▼
Telecom Provider
    │
    │ "What actually happened?"
    ▼
Event Processor
    │
    ▼
Consistent System State
```

This separation allows the predictive strategy to be improved independently while keeping the safety boundary intact.
