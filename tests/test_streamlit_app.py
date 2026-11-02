from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from medlab.config import get_settings

APP = str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> AppTest:
    monkeypatch.setenv("MEDLAB_LLM_MODE", "offline")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    get_settings.cache_clear()
    return AppTest.from_file(APP, default_timeout=60)


def test_app_renders(app: AppTest) -> None:
    app.run()
    assert not app.exception
    assert app.title[0].value == "MedLab Insight"
    assert app.button(key="submit") is not None


def test_submit_without_consent_shows_error(app: AppTest) -> None:
    app.run()
    app.number_input(key="blood_hb").set_value(105.0)
    app.button(key="submit").click().run()
    assert not app.exception
    assert any("đồng ý" in error.value for error in app.error)


def test_golden_path_offline(app: AppTest) -> None:
    app.run()
    app.number_input(key="blood_hb").set_value(105.0)
    app.number_input(key="blood_wbc").set_value(6.0)
    app.number_input(key="blood_plt").set_value(250.0)
    app.checkbox(key="consent").check()
    app.button(key="submit").click().run()
    assert not app.exception
    assert any("Kết luận" in header.value for header in app.subheader)
    assert any("offline" in info.value.lower() for info in app.info)
