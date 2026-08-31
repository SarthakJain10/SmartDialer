# SmartDialer Architecture Overview

## Structural Diagram
```mermaid
graph TD
    Campaign[Campaign / Simulator] -->|Requests Calls| Pacing[Predictive Pacing Engine]
    Pacing -->|Desired Dial Count| Safety[Safety Controller]
    Safety -->|Approved Calls| Allocator[Call Allocator]
    Allocator -->|Atomic Reservation| State[(In-Memory State)]
    Allocator -->|Initiate Call| Provider[TelecomProvider Interface]
    Provider -->|Async Events| EventProc[Event Processor]
    EventProc -->|Validate & Update| State