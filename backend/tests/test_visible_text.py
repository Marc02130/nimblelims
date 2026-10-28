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
    assert has_visible_text("\u00a0") is False
    for code in range(0x2000, 0x200B):
        assert has_visible_text(chr(code)) is False, hex(code)
    assert has_visible_text("\u3000") is False
    assert has_visible_text("\u200b") is True
    assert has_visible_text("\ufeff") is True
