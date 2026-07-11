from xml.sax.saxutils import escape


def build_stream_twiml(*, stream_url: str, parameters: dict[str, str]) -> str:
    parameter_lines = "\n".join(
        f'      <Parameter name="{escape(key)}" value="{escape(value)}" />'
        for key, value in parameters.items()
    )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="{escape(stream_url)}">
{parameter_lines}
    </Stream>
  </Connect>
</Response>
"""


def build_error_twiml(message: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Joanna">{escape(message)}</Say>
  <Hangup/>
</Response>
"""
