from unittest.mock import MagicMock, patch

from sqlmodel import select

from app.tests_pre_start import init, logger


def test_init_successful_connection() -> None:
    engine_mock = MagicMock()

    session_mock = MagicMock()
    # Make session_mock work as a context manager
    session_mock.__enter__ = MagicMock(return_value=session_mock)
    session_mock.__exit__ = MagicMock(return_value=False)
    
    # Create a mock Session class that returns session_mock when called
    session_class_mock = MagicMock(return_value=session_mock)

    with (
        patch("app.tests_pre_start.Session", session_class_mock),
        patch.object(logger, "info"),
        patch.object(logger, "error"),
        patch.object(logger, "warn"),
    ):
        try:
            init(engine_mock)
            connection_successful = True
        except Exception:
            connection_successful = False

        assert (
            connection_successful
        ), "The database connection should be successful and not raise an exception."

        session_mock.exec.assert_called_once(), "The session should execute a select statement once."
        assert session_mock.exec.call_count == 1
