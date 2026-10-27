"""Spec 039 T5: sin medición JS de alturas de columnas (RF-2, falla antes)."""

import pathlib

CSS = pathlib.Path(__file__).resolve().parent.parent / "static" / "css"
JS = pathlib.Path(__file__).resolve().parent.parent / "static" / "js" / "level-cascade.js"


def test_sin_var_layout_top() -> None:
    for name in ("cascade.css", "nutrition-trend.css"):
        assert "--dashboard-layout-top" not in (CSS / name).read_text(), name
    assert "--dashboard-layout-top" not in JS.read_text()
