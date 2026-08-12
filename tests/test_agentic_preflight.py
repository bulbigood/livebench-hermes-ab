from pathlib import Path

import pytest

from livebench_hermes_ab.agentic_preflight import PaidSmokeBlocked, load_paid_smoke_preflight


def test_paid_smoke_preflight_fails_closed() -> None:
    with pytest.raises(PaidSmokeBlocked) as error:
        load_paid_smoke_preflight(Path("config/agentic-paid-smoke-preflight.yaml"))
    message = str(error.value)
    assert "disabled" in message
    assert "gated identity unconfirmed" in message
    assert "operator approval missing" in message
    assert "provider/model unset" in message
