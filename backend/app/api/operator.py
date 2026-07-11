from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas import OperatorSessionResponse
from app.db.database import get_db_session
from app.services.operator_view import build_operator_session_view

router = APIRouter(prefix="/operator", tags=["operator"])
DbSession = Annotated[Session, Depends(get_db_session)]


@router.get("/sessions/{session_id}", response_model=OperatorSessionResponse)
def read_operator_session(session_id: str, db: DbSession) -> OperatorSessionResponse:
    try:
        return build_operator_session_view(db, session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
