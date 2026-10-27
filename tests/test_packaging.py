"""Packaging metadata carries the VigilTech name, icon, copyright and licence (checked without building)."""
import plistlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_script_names_the_bundle_and_dmg_vigil_social():
    build = (ROOT / 'build.py').read_text()
    assert "CFBundleName='Vigil Social'" in build and "CFBundleDisplayName='Vigil Social'" in build
    assert "'-volname','Vigil Social'" in build
    assert 'Copyright © VigilTech. GPL-3.0-only.' in build
    assert "'--icon','assets/logo.icns'" in build
    assert 'Makk Social' not in build


def test_app_icon_is_a_valid_icns_of_the_social_kit():
    data = (ROOT / 'assets/logo.icns').read_bytes()
    assert data[:4] == b'icns' and len(data) > 100000
    assert (ROOT / 'assets/logo.png').read_bytes()[:8] == b'\x89PNG\r\n\x1a\n'


def test_licence_and_notices_name_vigiltech():
    assert 'GPL-3.0-only' in (ROOT / 'pyproject.toml').read_text()
    assert 'VigilTech' in (ROOT / 'THIRD-PARTY-NOTICES.md').read_text()
