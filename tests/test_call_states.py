from app.domain.call import Call
from app.domain.enums import CallState


def test_terminal_state_invariant():
    call = Call(id="C1", borrower_id="B1", agent_id="A1", status=CallState.INITIATED)
    call.transition_to(CallState.RINGING)
    call.transition_to(CallState.COMPLETED)

    assert call.is_terminal() is True
    # Invariant check: Cannot transition back out of terminal state
    success = call.transition_to(CallState.ANSWERED)
    assert success is False
    assert call.status == CallState.COMPLETED