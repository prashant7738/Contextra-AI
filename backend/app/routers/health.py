from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
@router.head("/health")
async def health():
    """Cheap liveness check for uptime monitors - never touches DB or LLM providers."""
    return {"status": "healthy"}
