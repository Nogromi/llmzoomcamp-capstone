from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).parents[1] / "src/dlmm_position_lab/app.py"


def test_streamlit_app_renders_and_analyzes_fixture_prices() -> None:
    app = AppTest.from_file(APP_PATH, default_timeout=10).run()

    assert not app.exception
    assert [tab.label for tab in app.tabs] == ["Documentation chat", "Range lab"]

    app.button[0].click().run()

    assert not app.exception
    assert [(metric.label, metric.value) for metric in app.metric] == [
        ("Current price", "99"),
        ("Inside range", "No"),
        ("Range width", "10"),
        ("Inside observations", "60.0%"),
        ("Range exits", "2"),
        ("Observed min / max", "99 / 111"),
    ]
