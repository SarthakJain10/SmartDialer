import pytest
from app.domain.agent import Agent
from app.domain.enums import AgentState


def test_agent_valid_state_transitions():
    agent = Agent(id="A1", name="Agent 1", status=AgentState.OFFLINE)

    agent.transition_to(AgentState.AVAILABLE)
    assert agent.status == AgentState.AVAILABLE

    agent.transition_to(AgentState.RESERVED)
    assert agent.status == AgentState.RESERVED

    agent.transition_to(AgentState.DIALING)
    assert agent.status == AgentState.DIALING

    agent.transition_to(AgentState.CONNECTED)
    assert agent.status == AgentState.CONNECTED

    agent.transition_to(AgentState.WRAP_UP)
    assert agent.status == AgentState.WRAP_UP

    agent.transition_to(AgentState.AVAILABLE)
    assert agent.status == AgentState.AVAILABLE


def test_agent_invalid_state_transition():
    agent = Agent(id="A1", name="Agent 1", status=AgentState.AVAILABLE)
    with pytest.raises(ValueError):
        agent.transition_to(AgentState.CONNECTED)