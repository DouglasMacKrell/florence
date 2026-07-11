from fastapi import APIRouter

from app.demo.walkthrough import load_demo_script

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/script")
def get_demo_script() -> dict:
    return load_demo_script()
