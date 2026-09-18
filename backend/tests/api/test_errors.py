"""A lost database connection must read as transient (503), not as a server bug (500)."""
import json

from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as SATimeoutError

from app import main


def _body(response) -> dict:
    return json.loads(response.body)


def _dbapi_error(invalidated: bool) -> OperationalError:
    exc = OperationalError("select 1", {}, Exception("connection was closed in the middle of operation"))
    exc.connection_invalidated = invalidated
    return exc


async def test_dropped_connection_is_503():
    res = await main.db_error(None, _dbapi_error(invalidated=True))
    assert res.status_code == 503
    assert _body(res)["error"]["code"] == "DB_UNAVAILABLE"


async def test_other_db_errors_stay_500():
    """A syntax error or constraint violation is our bug, not something to retry."""
    res = await main.db_error(None, _dbapi_error(invalidated=False))
    assert res.status_code == 500
    assert _body(res)["error"]["code"] == "INTERNAL_ERROR"


async def test_pool_exhaustion_is_503():
    res = await main.db_busy(None, SATimeoutError("QueuePool limit reached"))
    assert res.status_code == 503
    assert _body(res)["error"]["code"] == "DB_UNAVAILABLE"
