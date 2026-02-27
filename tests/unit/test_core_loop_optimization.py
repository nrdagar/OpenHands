import asyncio
import pytest
from unittest.mock import Mock, AsyncMock

from openhands.controller.agent_controller import AgentController
from openhands.core.loop import run_agent_until_done
from openhands.core.schema import AgentState
from openhands.events import EventStream
from openhands.memory.memory import Memory
from openhands.runtime.base import Runtime


@pytest.mark.asyncio
async def test_run_agent_until_done_event_driven():
    """Test that the optimized loop responds immediately to state changes."""
    
    controller = Mock()
    controller.state = Mock()
    controller.state.agent_state = AgentState.RUNNING
    controller.status_callback = None
    
    runtime = Mock()
    runtime.status_callback = None
    
    memory = Mock()
    memory.status_callback = None
    
    state_change_callback = None
    def mock_set_state_change_callback(callback):
        nonlocal state_change_callback
        state_change_callback = callback
    
    controller.set_state_change_callback = mock_set_state_change_callback
    
    async def change_state_after_delay():
        await asyncio.sleep(0.1)  # Short delay
        controller.state.agent_state = AgentState.FINISHED
        if state_change_callback:
            state_change_callback()
    
    state_change_task = asyncio.create_task(change_state_after_delay())
    
    start_time = asyncio.get_event_loop().time()
    
    await run_agent_until_done(
        controller=controller,
        runtime=runtime,
        memory=memory,
        end_states=[AgentState.FINISHED, AgentState.ERROR, AgentState.STOPPED]
    )
    
    end_time = asyncio.get_event_loop().time()
    elapsed_time = end_time - start_time
    
    await state_change_task
    
    assert elapsed_time < 0.5, f"Loop took {elapsed_time:.3f}s, expected < 0.5s"
    
    assert state_change_callback is not None


@pytest.mark.asyncio
async def test_run_agent_until_done_timeout_fallback():
    """Test that the loop still works with timeout fallback when no callback is set."""
    
    controller = Mock()
    controller.state = Mock()
    controller.state.agent_state = AgentState.RUNNING
    controller.status_callback = None
    
    runtime = Mock()
    runtime.status_callback = None
    
    memory = Mock()
    memory.status_callback = None
    
    async def change_state_after_delay():
        await asyncio.sleep(0.1)
        controller.state.agent_state = AgentState.FINISHED
    
    state_change_task = asyncio.create_task(change_state_after_delay())
    
    await run_agent_until_done(
        controller=controller,
        runtime=runtime,
        memory=memory,
        end_states=[AgentState.FINISHED, AgentState.ERROR, AgentState.STOPPED]
    )
    
    await state_change_task
    
    assert controller.state.agent_state == AgentState.FINISHED


@pytest.mark.asyncio
async def test_run_agent_until_done_multiple_state_changes():
    """Test that the loop handles multiple rapid state changes correctly."""
    
    controller = Mock()
    controller.state = Mock()
    controller.state.agent_state = AgentState.LOADING
    controller.status_callback = None
    
    runtime = Mock()
    runtime.status_callback = None
    
    memory = Mock()
    memory.status_callback = None
    
    state_change_callback = None
    def mock_set_state_change_callback(callback):
        nonlocal state_change_callback
        state_change_callback = callback
    
    controller.set_state_change_callback = mock_set_state_change_callback
    
    async def multiple_state_changes():
        await asyncio.sleep(0.05)
        controller.state.agent_state = AgentState.RUNNING
        if state_change_callback:
            state_change_callback()
        
        await asyncio.sleep(0.05)
        controller.state.agent_state = AgentState.AWAITING_USER_INPUT
        if state_change_callback:
            state_change_callback()
        
        await asyncio.sleep(0.05)
        controller.state.agent_state = AgentState.FINISHED
        if state_change_callback:
            state_change_callback()
    
    state_change_task = asyncio.create_task(multiple_state_changes())
    
    await run_agent_until_done(
        controller=controller,
        runtime=runtime,
        memory=memory,
        end_states=[AgentState.FINISHED, AgentState.ERROR, AgentState.STOPPED]
    )
    
    await state_change_task
    
    assert controller.state.agent_state == AgentState.FINISHED
