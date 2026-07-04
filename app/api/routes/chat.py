from fastapi import APIRouter, Depends, Request, Response

from app.dependencies import generate_request_id, get_primary_proxy_service
from app.proxy.primary_proxy_service import PrimaryProxyService

router = APIRouter()


@router.post("/v1/chat")
async def chat(
    request: Request,
    request_id: str = Depends(generate_request_id),
    service: PrimaryProxyService = Depends(get_primary_proxy_service),
) -> Response:
    body = await request.body()
    headers = dict(request.headers)

    result = await service.handle_chat(
        request_id=request_id,
        body=body,
        headers=headers,
    )

    media_type = result.headers.get("content-type", "application/json")
    return Response(
        content=result.body,
        status_code=result.status_code,
        media_type=media_type,
        headers={"X-Request-ID": request_id},
    )
