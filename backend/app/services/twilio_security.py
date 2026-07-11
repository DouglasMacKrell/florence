"""Twilio request validation helpers."""

from urllib.parse import urljoin

from fastapi import HTTPException, Request

from app.config import Settings


async def validate_twilio_request(request: Request, settings: Settings) -> dict[str, str]:
    form = await request.form()
    payload = {key: str(value) for key, value in form.items()}
    if not settings.twilio_auth_token:
        return payload

    try:
        from twilio.request_validator import RequestValidator
    except ImportError:
        return payload

    validator = RequestValidator(settings.twilio_auth_token)
    signature = request.headers.get("X-Twilio-Signature", "")
    validation_url = _validation_url(request, settings)
    if not validator.validate(validation_url, payload, signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")
    return payload


def _validation_url(request: Request, settings: Settings) -> str:
    if settings.public_base_url:
        base = settings.public_base_url.rstrip("/")
        path = request.url.path
        query = request.url.query
        url = urljoin(f"{base}/", path.lstrip("/"))
        if query:
            return f"{url}?{query}"
        return url
    return str(request.url)
