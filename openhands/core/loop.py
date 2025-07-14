import asyncio

from openhands.controller import AgentController
from openhands.core.logger import openhands_logger as logger
from openhands.core.schema import AgentState
from openhands.memory.memory import Memory
from openhands.runtime.base import Runtime


async def run_agent_until_done(
    controller: AgentController,
    runtime: Runtime,
    memory: Memory,
    end_states: list[AgentState],
) -> None:
    """
    run_agent_until_done takes a controller and a runtime, and will run
    the agent until it reaches a terminal state.
    Note that runtime must be connected before being passed in here.
    """
    state_change_event = asyncio.Event()

    def status_callback(msg_type: str, msg_id: str, msg: str) -> None:
        if msg_type == 'error':
            logger.error(msg)
            if controller:
                controller.state.last_error = msg
                asyncio.create_task(controller.set_agent_state_to(AgentState.ERROR))
        else:
            logger.info(msg)

    def state_change_callback() -> None:
        state_change_event.set()

    if hasattr(runtime, 'status_callback') and runtime.status_callback:
        raise ValueError(
            'Runtime status_callback was set, but run_agent_until_done will override it'
        )
    if hasattr(controller, 'status_callback') and controller.status_callback:
        raise ValueError(
            'Controller status_callback was set, but run_agent_until_done will override it'
        )

    runtime.status_callback = status_callback
    controller.status_callback = status_callback
    memory.status_callback = status_callback

    if hasattr(controller, 'set_state_change_callback'):
        controller.set_state_change_callback(state_change_callback)

    while controller.state.agent_state not in end_states:
        try:
            await asyncio.wait_for(state_change_event.wait(), timeout=1.0)
            state_change_event.clear()
        except asyncio.TimeoutError:
            pass
