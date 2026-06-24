from asyncio import Lock
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any


@dataclass
class HookState:
    failures_before_success: int = 0
    attempts: int = 0
    successful_deliveries: int = 0
    payloads: list[dict[str, Any]] = field(default_factory=list)


class HookDeliveryFailed(Exception):
    pass


class TestHookStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._hooks: dict[str, HookState] = {}

    async def configure(self, hook_id: str, *, failures_before_success: int) -> HookState:
        async with self._lock:
            state = HookState(failures_before_success=failures_before_success)
            self._hooks[hook_id] = state
            return deepcopy(state)

    async def get(self, hook_id: str) -> HookState | None:
        async with self._lock:
            state = self._hooks.get(hook_id)
            if state is None:
                return None
            return deepcopy(state)

    async def deliver(self, hook_id: str, payload: dict[str, Any]) -> HookState:
        async with self._lock:
            state = self._hooks.setdefault(hook_id, HookState())
            state.attempts += 1
            state.payloads.append(deepcopy(payload))
            if state.attempts <= state.failures_before_success:
                raise HookDeliveryFailed(f"Configured failure for hook {hook_id} on attempt {state.attempts}")
            state.successful_deliveries += 1
            return deepcopy(state)


store = TestHookStore()
