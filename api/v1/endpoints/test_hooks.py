from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.test_hook.store import HookDeliveryFailed, store
from core.auth import verify_api_key
from core.base.schema import IGetResponseBase, IPostResponseBase


class HookConfigRequest(BaseModel):
    failures_before_success: int = Field(ge=0)


class HookStateResponse(BaseModel):
    failures_before_success: int
    attempts: int
    successful_deliveries: int
    last_payload: dict[str, Any] | None


router = APIRouter(prefix="/test-hooks", tags=["test-hooks"])


def _to_response(state) -> HookStateResponse:
    return HookStateResponse(
        failures_before_success=state.failures_before_success,
        attempts=state.attempts,
        successful_deliveries=state.successful_deliveries,
        last_payload=state.payloads[-1] if state.payloads else None,
    )


@router.put(
    "/{hook_id}/config",
    response_model=IPostResponseBase[HookStateResponse],
)
async def configure_test_hook(
    hook_id: str,
    body: HookConfigRequest,
    _: str = Depends(verify_api_key),
):
    state = await store.configure(
        hook_id,
        failures_before_success=body.failures_before_success,
    )
    return IPostResponseBase[HookStateResponse](data=_to_response(state))


@router.get(
    "/{hook_id}",
    response_model=IGetResponseBase[HookStateResponse],
)
async def get_test_hook(
    hook_id: str,
    _: str = Depends(verify_api_key),
):
    state = await store.get(hook_id)
    if state is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test hook not found")
    return IGetResponseBase[HookStateResponse](data=_to_response(state))


@router.post("/{hook_id}/deliver")
async def deliver_test_hook(hook_id: str, payload: dict[str, Any]):
    try:
        await store.deliver(hook_id, payload)
    except HookDeliveryFailed as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return {"ok": True}
