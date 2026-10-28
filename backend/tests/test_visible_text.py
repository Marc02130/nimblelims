"""Whitespace-only strings are blank for reason checks."""
from app.core.visible_text import has_visible_text


def test_has_visible_text_treats_tab_newline_and_spaces_as_blank():
    assert has_visible_text(None) is False
    assert has_visible_text("") is False
    assert has_visible_text("   ") is False
    assert has_visible_text("\t") is False
    assert has_visible_text("\n") is False
    assert has_visible_text("\r") is False
    assert has_visible_text("\r\n") is False
    assert has_visible_text(" \t\n ") is False
    assert has_visible_text("ok") is True
    assert has_visible_text("  misdated  ") is True
    assert has_visible_text("\tok\n") is True
