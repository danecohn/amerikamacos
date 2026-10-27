"""VigilTech look for the native Qt client: tokens, stylesheet, palette and the frosted sidebar.

The tokens mirror the --vt-* variables of the VigilTech design system (assets/vigiltech/tokens.json).
Every foreground/background pair the stylesheet uses is listed in PAIRS, and tests/test_vigiltech.py
checks them for WCAG contrast in both themes, so a change to a colour cannot silently break legibility.
GPL-3.0-only.
"""
import os
import sys
from pathlib import Path
from string import Template
from PySide6.QtCore import Qt, QRectF, QSettings
from PySide6.QtGui import QColor, QPalette, QPainter, QPixmap, QGuiApplication
from PySide6.QtWidgets import QWidget

FONT_FAMILY = 'Vigil Sans'
# Unchanged Qt organisation/application name of this app: the stored appearance choice sits beside the existing settings.
SETTINGS_IDS = ('AltStack Social', 'AltStack Social')

LIGHT = dict(
    bg='#f6f1f4', surface='#fffbfd', surface2='#faf4f7', glass='#f3ebf0',
    label='#17101a', label2='#6b5d68',
    sep='#ddd0d8', edge='#8a7a86', hover='#efe4ea', press='#e9dce4',
    tint='#d6004a', tint_hover='#a8003a', tint_text='#a8003a', on_tint='#ffffff', focus='#d6004a',
    sel_bg='#ffd6e4', sel_fg='#7a002b', chip_bg='#ffe3ec', chip_fg='#a8003a',
    disabled_bg='#ebe2e7', disabled_fg='#5f515c', danger='#b3001b',
    select_bg='#ffc2d6', select_fg='#17101a',
    hero_a='#fff7fa', hero_b='#ffd6e4', hero_eyebrow='#a8003a',
    icon='#6b5d68', icon_active='#a8003a', veil='255,251,253', wallpaper='wallpaper-dawn.png',
    chevron='chevron-light.svg',
)
DARK = dict(
    bg='#120a14', surface='#1e1422', surface2='#181019', glass='#1a1020',
    label='#f7eef2', label2='#b7a5b1',
    sep='#3a2a40', edge='#8f7d8b', hover='#2a1c2f', press='#35243b',
    tint='#d6004a', tint_hover='#a8003a', tint_text='#ff7aa6', on_tint='#ffffff', focus='#ff7aa6',
    sel_bg='#4a1236', sel_fg='#ffd6e4', chip_bg='#3d1030', chip_fg='#ffb3cc',
    disabled_bg='#261a2a', disabled_fg='#a898a3', danger='#ff7a8e',
    select_bg='#7a002b', select_fg='#ffffff',
    hero_a='#34102a', hero_b='#1e1422', hero_eyebrow='#ff7aa6',
    icon='#b7a5b1', icon_active='#ff7aa6', veil='26,16,32', wallpaper='wallpaper-night.png',
    chevron='chevron-dark.svg',
)
THEMES = {'light': LIGHT, 'dark': DARK}

# (description, foreground, background, minimum ratio). Text needs 4.5; borders, rings and icons need 3.
PAIRS = []
for _bg in ('bg', 'surface', 'surface2', 'glass', 'hover', 'disabled_bg'):
    PAIRS.append((f'label on {_bg}', 'label', _bg, 4.5))
for _bg in ('bg', 'surface', 'surface2', 'glass', 'hover'):
    PAIRS.append((f'secondary text on {_bg}', 'label2', _bg, 4.5))
for _bg in ('bg', 'surface', 'surface2', 'glass', 'hover', 'chip_bg', 'sel_bg'):
    PAIRS.append((f'accent text on {_bg}', 'tint_text' if _bg not in ('chip_bg', 'sel_bg') else ('chip_fg' if _bg == 'chip_bg' else 'sel_fg'), _bg, 4.5))
PAIRS += [
    ('label on pressed', 'label', 'press', 4.5),
    ('primary button', 'on_tint', 'tint', 4.5), ('primary button hover', 'on_tint', 'tint_hover', 4.5),
    ('disabled control', 'disabled_fg', 'disabled_bg', 4.5), ('disabled text on surface', 'disabled_fg', 'surface', 4.5),
    ('selected text', 'select_fg', 'select_bg', 4.5),
    ('hero text start', 'label', 'hero_a', 4.5), ('hero text end', 'label', 'hero_b', 4.5),
    ('hero eyebrow start', 'hero_eyebrow', 'hero_a', 4.5), ('hero eyebrow end', 'hero_eyebrow', 'hero_b', 4.5),
    ('error text on surface', 'danger', 'surface', 4.5), ('error text on bg', 'danger', 'bg', 4.5),
    ('focus ring on surface', 'focus', 'surface', 3.0), ('focus ring on bg', 'focus', 'bg', 3.0),
    ('input border on surface', 'edge', 'surface', 3.0), ('input border on bg', 'edge', 'bg', 3.0),
    ('icon on bg', 'icon', 'bg', 3.0), ('icon on surface', 'icon', 'surface', 3.0), ('icon on glass', 'icon', 'glass', 3.0),
    ('active icon on selected nav', 'sel_fg', 'sel_bg', 3.0), ('active icon on surface', 'icon_active', 'surface', 3.0),
    ('focus ring on primary', 'label', 'tint', 3.0),
]


def _lin(c):
    c /= 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(color):
    c = QColor(color)
    return 0.2126 * _lin(c.red()) + 0.7152 * _lin(c.green()) + 0.0722 * _lin(c.blue())


def contrast(a, b):
    x, y = sorted((luminance(a), luminance(b)), reverse=True)
    return (x + 0.05) / (y + 0.05)


def asset_dir():
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent)) / 'assets' / 'vigiltech'


_current = 'light'


def current():
    return _current


def set_theme(name):
    global _current
    _current = name if name in THEMES else 'light'
    return _current


def tone(key):
    """A token of the active theme, for the few places that paint with code instead of the stylesheet."""
    return THEMES[_current][key]


def settings():
    return QSettings(*SETTINGS_IDS)


def preference():
    value = os.environ.get('VIGILTECH_APPEARANCE') or QSettings(*SETTINGS_IDS).value('appearance', 'system')
    return value if value in ('light', 'dark') else 'system'


def resolve(choice=None):
    choice = choice or preference()
    if choice in THEMES:
        return choice
    hints = QGuiApplication.styleHints()
    return 'dark' if hints is not None and hints.colorScheme() == Qt.ColorScheme.Dark else 'light'


def palette(name):
    t = THEMES[name]
    p = QPalette()
    for role, key in [(QPalette.ColorRole.Window, 'bg'), (QPalette.ColorRole.WindowText, 'label'), (QPalette.ColorRole.Base, 'surface'),
                      (QPalette.ColorRole.AlternateBase, 'surface2'), (QPalette.ColorRole.Text, 'label'), (QPalette.ColorRole.Button, 'surface'),
                      (QPalette.ColorRole.ButtonText, 'label'), (QPalette.ColorRole.ToolTipBase, 'surface'), (QPalette.ColorRole.ToolTipText, 'label'),
                      (QPalette.ColorRole.Highlight, 'select_bg'), (QPalette.ColorRole.HighlightedText, 'select_fg'),
                      (QPalette.ColorRole.PlaceholderText, 'label2'), (QPalette.ColorRole.Link, 'tint_text'), (QPalette.ColorRole.LinkVisited, 'tint_text')]:
        p.setColor(role, QColor(t[key]))
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText):
        p.setColor(QPalette.ColorGroup.Disabled, role, QColor(t['disabled_fg']))
    return p


STYLE = Template('''
QWidget {background:transparent;color:$label;font-size:14px;}
QMainWindow,QWidget#appShell {background:$bg;}
QDialog,QMessageBox,QInputDialog {background:$surface;color:$label;}
QLabel {background:transparent;}
QLabel#heading {font-size:25px;font-weight:700;}
QLabel#muted {color:$label2;font-size:12px;}
QLabel#eyebrow {color:$label2;font-size:10px;font-weight:600;letter-spacing:1px;}
QLabel#postText {font-size:15px;}
QLabel:disabled {color:$disabled_fg;}

QWidget#hero {background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 $hero_a,stop:1 $hero_b);border:1px solid $sep;border-radius:16px;}
QWidget#hero QLabel {color:$label;}
QWidget#hero QLabel#heroTitle {font-size:34px;font-weight:700;}
QWidget#hero QLabel#eyebrow {color:$hero_eyebrow;font-size:10px;}
QWidget#card,QWidget#composeCard,QWidget#sectionCard {background:$surface;border:1px solid $sep;border-radius:14px;}
QWidget#card QLabel,QWidget#composeCard QLabel,QWidget#sectionCard QLabel {background:transparent;}
QWidget#threadChrome {background:$glass;color:$label;border-bottom:1px solid $sep;}

QPushButton {background:$surface;color:$label;border:1px solid $sep;border-radius:8px;padding:8px 14px;text-align:left;font-weight:500;}
QPushButton:hover {background:$hover;color:$label;}
QPushButton:pressed {background:$press;color:$label;}
QPushButton:focus {border:2px solid $focus;padding:7px 13px;}
QPushButton:disabled {background:$disabled_bg;color:$disabled_fg;border-color:$disabled_bg;}
QPushButton#primary {background:$tint;color:$on_tint;border:1px solid $tint_hover;font-weight:600;}
QPushButton#primary:hover,QPushButton#primary:pressed {background:$tint_hover;color:$on_tint;}
QPushButton#primary:focus {border:2px solid $label;padding:7px 13px;}
QPushButton#primary:disabled {background:$disabled_bg;color:$disabled_fg;border-color:$disabled_bg;}

QPushButton#nav {background:transparent;border:1px solid transparent;border-radius:9px;padding:9px 12px;color:$label;}
QPushButton#nav:hover {background:$hover;color:$label;}
QPushButton#nav:pressed {background:$press;color:$label;}
QPushButton#nav[selected="true"] {background:$sel_bg;border-color:$sel_bg;color:$sel_fg;font-weight:700;}
QPushButton#nav:focus {border:2px solid $focus;padding:8px 11px;}
QPushButton#disclosureHeader {background:transparent;border:0;border-radius:10px;padding:16px;color:$label;font-weight:600;text-align:left;}
QPushButton#disclosureHeader:hover {background:$hover;color:$label;}
QPushButton#disclosureHeader:focus {border:2px solid $focus;padding:14px;}
QPushButton#authorName {background:transparent;border:0;padding:0;color:$label;font-weight:700;}
QPushButton#authorName:hover,QPushButton#authorName:focus {background:transparent;color:$tint_text;}
QPushButton#postAction {background:transparent;border:1px solid transparent;padding:6px 10px;color:$label2;font-size:12px;font-weight:500;}
QPushButton#postAction:hover {background:$hover;color:$label;}
QPushButton#postAction:pressed {background:$press;color:$label;}
QPushButton#postAction[active="true"] {color:$tint_text;}
QPushButton#postAction:focus {border:2px solid $focus;padding:5px 9px;}
QPushButton#postAction:disabled {background:transparent;color:$disabled_fg;border-color:transparent;}
QPushButton#textLink {background:transparent;border:0;padding:0;color:$label2;font-size:12px;}
QPushButton#textLink:hover,QPushButton#textLink:focus {background:transparent;color:$tint_text;}
QPushButton#chip {background:$chip_bg;border:1px solid $chip_bg;border-radius:12px;padding:3px 10px;color:$chip_fg;font-size:11px;font-weight:600;}
QPushButton#chip:hover {background:$sel_bg;color:$sel_fg;}
QPushButton#composePrompt {background:$surface2;border:1px solid $sep;border-radius:19px;color:$label2;font-size:14px;padding:9px 16px;}
QPushButton#composePrompt:hover {background:$hover;color:$label;}
QPushButton#feedTab {background:transparent;border:0;border-bottom:2px solid transparent;border-radius:0;padding:12px 16px;color:$label2;font-weight:500;}
QPushButton#feedTab:hover {background:$hover;color:$label;}
QPushButton#feedTab[selected="true"] {border-bottom:2px solid $tint_text;color:$label;font-weight:700;}
QPushButton#feedTab:focus {border:2px solid $focus;padding:10px 14px;}

QLineEdit,QTextEdit,QPlainTextEdit,QComboBox,QSpinBox {background:$surface;color:$label;border:1px solid $edge;border-radius:8px;padding:8px 10px;selection-background-color:$select_bg;selection-color:$select_fg;placeholder-text-color:$label2;}
QLineEdit:focus,QTextEdit:focus,QPlainTextEdit:focus,QComboBox:focus,QSpinBox:focus {border:2px solid $focus;padding:7px 9px;}
QLineEdit:disabled,QTextEdit:disabled,QPlainTextEdit:disabled,QComboBox:disabled {background:$disabled_bg;color:$disabled_fg;border-color:$disabled_bg;}
QLineEdit:read-only {background:$surface2;}
QComboBox::drop-down {border:0;width:26px;}
QComboBox::down-arrow {image:url("$chevron");width:12px;height:12px;}
QComboBox QAbstractItemView,QAbstractItemView {background:$surface;color:$label;border:1px solid $sep;selection-background-color:$sel_bg;selection-color:$sel_fg;outline:0;}
QTextBrowser {background:transparent;color:$label;selection-background-color:$select_bg;selection-color:$select_fg;}

QCheckBox {spacing:9px;padding:5px;color:$label;}
QCheckBox:disabled {color:$disabled_fg;}
QCheckBox::indicator {width:18px;height:18px;background:$surface;border:1px solid $edge;border-radius:5px;}
QCheckBox::indicator:hover {border-color:$tint_text;}
QCheckBox::indicator:checked {background:$tint;border-color:$tint_hover;image:url("$check");}
QCheckBox::indicator:disabled {background:$disabled_bg;border-color:$disabled_bg;}
QCheckBox:focus {color:$label;}
QGroupBox {background:$surface;border:1px solid $sep;border-radius:12px;margin-top:22px;padding:18px;font-weight:600;color:$label;}
QGroupBox::title {subcontrol-origin:margin;left:14px;padding:0 6px;color:$label;}

QScrollArea {border:0;background:transparent;}
QScrollBar:vertical {background:transparent;width:10px;margin:2px;}
QScrollBar::handle:vertical {background:$edge;border-radius:4px;min-height:40px;}
QScrollBar::handle:vertical:hover {background:$label2;}
QScrollBar:horizontal {background:transparent;height:10px;margin:2px;}
QScrollBar::handle:horizontal {background:$edge;border-radius:4px;min-width:40px;}
QScrollBar::add-line,QScrollBar::sub-line {height:0;width:0;}
QScrollBar::add-page,QScrollBar::sub-page {background:transparent;}
QSlider::groove:horizontal {height:4px;background:$edge;border-radius:2px;}
QSlider::sub-page:horizontal {background:$tint;border-radius:2px;}
QSlider::handle:horizontal {width:16px;height:16px;margin:-6px 0;border-radius:8px;background:$tint;border:2px solid $surface;}

QMenuBar {background:$glass;color:$label;border-bottom:1px solid $sep;padding:2px 6px;}
QMenuBar::item {background:transparent;color:$label;padding:5px 10px;border-radius:6px;}
QMenuBar::item:selected {background:$sel_bg;color:$sel_fg;}
QMenu {background:$surface;color:$label;border:1px solid $sep;border-radius:10px;padding:6px;}
QMenu::item {padding:8px 22px;border-radius:6px;color:$label;background:transparent;}
QMenu::item:selected {background:$sel_bg;color:$sel_fg;}
QMenu::item:disabled {color:$disabled_fg;background:transparent;}
QMenu::separator {height:1px;background:$sep;margin:5px 8px;}
QStatusBar {background:$glass;color:$label;border-top:1px solid $sep;}
QToolTip {background:$surface;color:$label;border:1px solid $edge;padding:4px 6px;}
QMainWindow::separator {background:$sep;width:1px;height:1px;}
''')


def stylesheet(name):
    t = dict(THEMES[name])
    base = asset_dir()
    t['check'] = (base / 'check.svg').as_posix()
    t['chevron'] = (base / t['chevron']).as_posix()
    return STYLE.substitute(t)


def apply(app, window=None, choice=None):
    """Set palette and stylesheet for the resolved theme; returns its name."""
    name = set_theme(resolve(choice))
    app.setPalette(palette(name))
    if window is not None:
        window.setStyleSheet(stylesheet(name))
    else:
        app.setStyleSheet(stylesheet(name))
    return name


class GlassPanel(QWidget):
    """The sidebar: a frosted bar over the wallpaper. A near-opaque veil keeps text on a solid colour."""
    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._cache = {}

    def _wallpaper(self):
        name = current()
        if name not in self._cache:
            self._cache[name] = QPixmap(str(asset_dir() / THEMES[name]['wallpaper']))
        return self._cache[name]

    def paintEvent(self, event):
        t = THEMES[current()]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.fillRect(self.rect(), QColor(t['glass']))
        wall = self._wallpaper()
        if not wall.isNull():
            scale = max(self.width() / wall.width(), self.height() / wall.height())
            w, h = wall.width() * scale, wall.height() * scale
            p.drawPixmap(QRectF(self.width() - w, self.height() - h, w, h), wall, QRectF(wall.rect()))
        r, g, b = (int(v) for v in t['veil'].split(','))
        p.fillRect(self.rect(), QColor(r, g, b, 214))
        p.setPen(QColor(t['sep']))
        p.drawLine(self.width() - 1, 0, self.width() - 1, self.height())
        p.end()
