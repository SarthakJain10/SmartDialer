# Agent State Machine

The agent lifecycle controls agent availability and prevents double-allocation during call dialing and active conversations.

```mermaid
stateDiagram-v2
    [*] --> OFFLINE
    OFFLINE --> AVAILABLE: Agent Logs In
    AVAILABLE --> RESERVED: Call Allocator Reserves Agent
    RESERVED --> DIALING: Provider Initiates Dial
    DIALING --> CONNECTED: Borrower Answers Call
    DIALING --> AVAILABLE: Call Fails / Unreachable
    CONNECTED --> WRAP_UP: Call Ends
    WRAP_UP --> AVAILABLE: Wrap-Up Time Expires
    AVAILABLE --> OFFLINE: Agent Logs Out