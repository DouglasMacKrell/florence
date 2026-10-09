def telephony_pipeline_available() -> bool:
    try:
        import pipecat  # noqa: F401
        import twilio  # noqa: F401
    except ImportError:
        return False
    return True
