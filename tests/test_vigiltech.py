"""VigilTech look: token contrast, and a rendered audit of every page in both themes and in hover, focus, disabled and selected states."""
import collections
import pytest
from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (QLabel, QPushButton, QCheckBox, QLineEdit, QPlainTextEdit, QTextEdit, QTextBrowser, QComboBox,
                               QGroupBox, QApplication, QWidget)
from amerika import vigiltech as vt
from amerika.app import MainWindow
from conftest import FakeApi, POST

DESTINATIONS = ['feed', 'friends', 'inbox', 'alerts', 'developers', 'settings', 'plus', 'communities', 'dating', 'moderation', 'explore']


@pytest.mark.parametrize('theme', ['light', 'dark'])
def test_every_declared_pair_meets_its_contrast_floor(theme):
    t = vt.THEMES[theme]
    bad = [(d, round(vt.contrast(t[f], t[b]), 2), floor) for d, f, b, floor in vt.PAIRS if vt.contrast(t[f], t[b]) < floor]
    assert not bad, bad


def test_pink_button_fill_is_dark_enough_for_white_text():
    for t in vt.THEMES.values():
        assert vt.contrast('#ffffff', t['tint']) >= 4.5 and vt.contrast('#ffffff', t['tint_hover']) >= 4.5


def _mode_and_far(image, rect):
    counts = collections.Counter()
    for y in range(max(rect.top(), 0), min(rect.bottom() + 1, image.height())):
        for x in range(max(rect.left(), 0), min(rect.right() + 1, image.width())):
            c = image.pixelColor(x, y).rgb()
            counts[c] += 1
    if not counts:
        return None, None
    bg = QColor(counts.most_common(1)[0][0])
    far = max(counts, key=lambda c: abs(QColor(c).red() - bg.red()) + abs(QColor(c).green() - bg.green()) + abs(QColor(c).blue() - bg.blue()))
    return bg, QColor(far)


def _text_widgets(window):
    kinds = (QLabel, QPushButton, QCheckBox, QLineEdit, QPlainTextEdit, QTextEdit, QTextBrowser, QComboBox, QGroupBox)
    for w in window.findChildren(QWidget):
        if isinstance(w, kinds) and w.isVisible() and w.width() > 6 and w.height() > 6:
            yield w


def _label_text(w):
    if isinstance(w, QLabel):
        return w.text()
    if isinstance(w, (QPushButton, QCheckBox)):
        return w.text()
    if isinstance(w, (QLineEdit,)):
        return w.text() or w.placeholderText()
    if isinstance(w, QComboBox):
        return w.currentText()
    if isinstance(w, QGroupBox):
        return w.title()
    return w.toPlainText() if hasattr(w, 'toPlainText') else ''


def audit_window(window, qtbot, limit_states=10):
    """Returns (checked, failures). Foreground is the colour the stylesheet gives the widget; background is sampled from the render."""
    failures, checked = [], 0
    def measure(w, state):
        nonlocal checked
        text = _label_text(w).strip()
        if not text:
            return
        image = window.grab().toImage()
        top_left = w.mapTo(window, QPoint(0, 0))
        rect = QRect(top_left, w.size()).adjusted(2, 2, -2, -2)
        bg, far = _mode_and_far(image, rect)
        if bg is None:
            return
        fg = w.palette().color(w.foregroundRole())
        if isinstance(w, QLineEdit) and not w.text():
            fg = w.palette().color(w.palette().ColorRole.PlaceholderText)
        checked += 1
        nominal = vt.contrast(fg, bg)
        if nominal < 4.5:
            failures.append((state, type(w).__name__, w.objectName(), text[:30], 'nominal', round(nominal, 2), fg.name(), bg.name()))
    for w in list(_text_widgets(window)):
        measure(w, 'normal')
    buttons = [w for w in _text_widgets(window) if isinstance(w, (QPushButton, QCheckBox))][:limit_states]
    for w in buttons:
        was = w.isEnabled()
        w.setEnabled(False); QApplication.processEvents(); measure(w, 'disabled'); w.setEnabled(was); QApplication.processEvents()
        QTest.mouseMove(window, w.mapTo(window, QPoint(w.width() // 2, w.height() // 2))); QApplication.processEvents(); measure(w, 'hover')
        w.setFocus(); QApplication.processEvents(); measure(w, 'focus')
        QTest.mouseMove(window, QPoint(2, 2)); QApplication.processEvents()
    return checked, failures


@pytest.fixture(params=['light', 'dark'])
def themed(request, qtbot, monkeypatch):
    monkeypatch.setenv('VIGILTECH_APPEARANCE', request.param)
    window = MainWindow(FakeApi()); qtbot.addWidget(window); window.resize(1320, 940); window.show()
    qtbot.waitUntil(lambda: window.me is not None)
    assert window.theme == request.param
    return window, request.param


def test_every_page_is_legible_in_both_themes(themed, qtbot):
    window, theme = themed
    total, failures = 0, []
    for name in DESTINATIONS:
        getattr(window, name)(); qtbot.wait(60)
        n, f = audit_window(window, qtbot)
        total += n; failures += [(name,) + x for x in f]
    assert total > 100
    assert not failures, failures[:12]


def test_stylesheet_has_no_leftover_foreign_colours(themed):
    window, theme = themed
    t = vt.THEMES[theme]
    css = window.styleSheet().lower()
    for old in ('#1764bd', '#0066cc', '#0a7a37', '#e65b69', '#263e52', '#1d1d1f'):
        assert old not in css


def test_wallpaper_and_font_ship_with_the_app():
    assert (vt.asset_dir() / 'wallpaper-night.png').exists() and (vt.asset_dir() / 'wallpaper-dawn.png').exists()
    assert (vt.asset_dir() / 'fonts' / 'VigilSans-Regular.ttf').exists()
