# Call State Machine

The call lifecycle tracks an outbound call from initial queuing to terminal completion.

```mermaid
stateDiagram-v2
    [*] --> QUEUED
    QUEUED --> RESERVED: Borrower Assigned
    RESERVED --> INITIATED: Provider Accepts Call
    INITIATED --> RINGING: Network Telephony Ringing
    RINGING --> ANSWERED: Borrower Picks Up
    ANSWERED --> CONNECTED: Agent Bridged
    CONNECTED --> COMPLETED: Call Ended
    
    INITIATED --> FAILED: Invalid Number / Network Error
    RINGING --> FAILED: No Answer / Busy
    QUEUED --> CANCELLED: Campaign Stopped
    
    COMPLETED --> [*]
    FAILED --> [*]
    CANCELLED --> [*]