"""Build on the destination OS. No signing credentials are stored in source."""
import json
import os
import platform
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

root=Path(__file__).resolve().parent
os.chdir(root)
target=json.loads((root/'platform.json').read_text())['platform']
expected={'windows':'win32','macOS':'darwin','Linux':'linux'}[target]
if not sys.platform.startswith(expected):raise SystemExit(f'Build this project on {target}. Cross-compilation is not supported.')
separator=';' if sys.platform=='win32' else ':'
args=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed','--onedir','--name','MakkSocial','--add-data',f'assets{separator}assets','--add-data',f'LICENSE{separator}.','--add-data',f'THIRD-PARTY-NOTICES.md{separator}.','--hidden-import','keyring.backends.Windows' if sys.platform=='win32' else 'keyring.backends.macOS' if sys.platform=='darwin' else 'keyring.backends.SecretService','--collect-submodules','pillow_heif','--exclude-module','PySide6.QtWebEngineCore','--exclude-module','PySide6.QtWebEngineWidgets']
if sys.platform=='win32':args += ['--icon','assets/logo.ico']
if sys.platform=='darwin':args += ['--icon','assets/logo.icns','--osx-bundle-identifier','social.amerika.macos']
args += ['main.py'];subprocess.run(args,check=True)
release=root/'release';release.mkdir(exist_ok=True)
arch={'aarch64':'arm64','arm64':'arm64','x86_64':'x64','amd64':'x64'}.get(platform.machine().lower())
if not arch:raise SystemExit('Unsupported build architecture: '+platform.machine())
if sys.platform=='darwin':
    app=root/'dist/MakkSocial.app'
    import plistlib
    info=app/'Contents/Info.plist';data=plistlib.loads(info.read_bytes());data.update(CFBundleName='Vigil Social',CFBundleDisplayName='Vigil Social',NSHumanReadableCopyright='Copyright © VigilTech. GPL-3.0-only.',LSApplicationCategoryType='public.app-category.social-networking',CFBundleShortVersionString='1.0.0',CFBundleVersion='1',NSLocationWhenInUseUsageDescription='Optionally verify US presence or display approximate Dating distance.',NSHighResolutionCapable=True);info.write_bytes(plistlib.dumps(data))
    # Ad-hoc signing allows local testing. Public distribution still requires Developer ID signing and notarization.
    subprocess.run(['codesign','--force','--deep','--sign','-',str(app)],check=True)
    subprocess.run(['hdiutil','create','-volname','Vigil Social','-srcfolder',str(app),'-ov','-format','UDZO',str(release/'MakkSocial-macOS.dmg')],check=True)
elif sys.platform=='win32':shutil.make_archive(str(release/f'MakkSocial-Windows-{arch}'),'zip',root/'dist','MakkSocial')
else:
    out=root/'dist/MakkSocial';shutil.copy2(root/'packaging/amerika-social.desktop',out);shutil.copy2(root/'packaging/install-linux.sh',out);(out/'install-linux.sh').chmod(0o755)
    with tarfile.open(release/f'MakkSocial-Linux-{arch}.tar.gz','w:gz') as archive:archive.add(out,arcname='MakkSocial')
print('Packaged native app:',release)
