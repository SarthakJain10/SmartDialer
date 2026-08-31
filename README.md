FILE: `README.md`

# SmartDialer Technical Prototype

A modular Python implementation of an outbound dialing system designed to solve the trade-off between **agent idle time** and **abandoned call risk**. This prototype demonstrates Progressive Dialing, Heuristic Predictive Pacing, an isolated Safety Controller, and asynchronous, idempotent event handling.

---

## The Dialing Problem

In outbound call centers (e.g., collections or sales), dialing one contact per available agent (**Progressive Dialing**) is safe but results in low agent utilization while waiting for calls to connect. Dialing multiple contacts per agent (**Predictive Dialing**) maximizes utilization, but over-dialing can lead to **abandoned calls** if more borrowers answer than there are available agents.

```
Progressive: 1 Available Agent  ──► 1 Outbound Call   (Safe, but lower utilization)
Predictive:  1 Available Agent  ──► N Outbound Calls  (High utilization, needs safety limits)

```

---

## Architectural Flow & Safety Gatekeeper

To eliminate the risk of runaway predictive algorithms placing unauthorized calls, the system enforces a non-bypassable unidirectional flow. The Pacing Engine **never** calls the telecom provider directly.

```

| Component | Primary Responsibility |
| --- | --- |
| **Predictive Pacing Engine** | Calculates target call volume based on rolling answer rates and active ringing calls. |
| **Safety Controller** | Acts as the final gatekeeper. Clamps requested dials to actual available capacity and forces fallback to 1:1 dialing if provider health drops. |
| **Call Allocator** | Atomically reserves agents and pairs them with prioritized borrowers. |
| **Telecom Provider** | Abstracted protocol (`MockProviderA`, `MockProviderB`) simulating network latency, failures, duplicates, and out-of-order events. |
| **Event Processor** | Deduplicates incoming telecom events and executes valid state machine transitions. |

---

## Core System Invariants

* **Safety Invariant:** Pacing requests can never bypass the `SafetyController`. Dials are strictly capped by available agent capacity.
* **Reservation Invariant:** Concurrent workers cannot reserve the same agent simultaneously. Enforced via `asyncio.Lock` per agent.
* **Terminal Call Invariant:** Calls in a terminal state (`COMPLETED`, `FAILED`, `CANCELLED`) can never transition back to an active state.
* **Event Idempotency:** Duplicate provider events (tracked via unique `event_id`) are safely ignored without altering system state.

---

## State Machines

### Agent State Transitions

`OFFLINE` ➔ `AVAILABLE` ➔ `RESERVED` ➔ `DIALING` ➔ `CONNECTED` ➔ `WRAP_UP` ➔ `AVAILABLE`

### Call State Transitions

`QUEUED` ➔ `RESERVED` ➔ `INITIATED` ➔ `RINGING` ➔ `ANSWERED` ➔ `CONNECTED` ➔ `COMPLETED` *(Terminal)*

---

## Setup & Installation

### Prerequisites

* Python 3.11+ (or Python 3.9+)

### Installation

```bash
# 1. Clone the repository and navigate to root
cd "smart dialer"

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install required dependencies
pip install -r requirements.txt

```

---

## Running Scenarios & Simulations

### 1. Run Automated Unit Tests

Verifies state machine transitions, safety clamps, idempotency, and concurrent reservation locks.

```bash
pytest -v

```

### 2. Run Progressive Dialer Mode

Executes 1-to-1 dialing against healthy Provider A.

```bash
python -m simulation.run --mode progressive --provider A --agents 15 --borrowers 30 --duration 5

```

### 3. Run Predictive Pacing Mode

Executes heuristic predictive pacing with safety controller limits enabled.

```bash
python -m simulation.run --mode predictive --provider A --agents 15 --borrowers 30 --duration 5

```

### 4. Run Side-by-Side Comparison Mode

Runs progressive and predictive modes using identical random seeds to directly compare agent utilization and total completed calls.

```bash
python -m simulation.run --mode compare

```

### 5. Run Unreliable Provider Mode (Duplicates & Out-of-Order Events)

Tests resilience against `MockProviderB`, which introduces network latency, duplicate events, and out-of-order event delivery.

```bash
python -m simulation.run --mode predictive --provider B --agents 15 --borrowers 30 --duration 5

```

### 6. Run Concurrency Load Test

Stress-tests agent reservation locks under multi-worker contention.

```bash
python -m simulation.load_test

```

### 7. Launch FastAPI REST Server

Exposes live state endpoints and on-demand simulation triggers.

```bash
uvicorn app.main:app --reload

```

Available Endpoints:

* `GET  /health` – System health check.
* `GET  /agents` – Current state of all agents in memory.
* `GET  /calls` – Active and historical calls log.
* `POST /simulation/run` – Trigger custom simulation run.

---

## Prototype vs. Production Trade-offs

| Domain | Prototype Implementation (Current) | Production Requirement |
| --- | --- | --- |
| **Data Persistence** | Initial bootstrap via `CSV` files; runtime state held in-memory via `InMemoryRepository`. | Relational DB (PostgreSQL) with transactional migrations. |
| **Concurrency Lock** | `asyncio.Lock` per agent inside a single process. | Distributed locking (e.g., Redis Redlock) across multi-worker nodes. |
| **Messaging & Events** | In-memory `asyncio` task queues and direct callbacks. | Message Broker / Event Stream (Kafka, RabbitMQ, or AWS SQS). |
| **Telecom Integration** | Simulated mock implementations (`MockProviderA`, `MockProviderB`). | Production Webhooks & Telephony APIs (Twilio, Plivo, Bandwidth). |