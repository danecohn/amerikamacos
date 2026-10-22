#!/bin/sh
set -eu
SOURCE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
TARGET="$HOME/.local/opt/amerika-social"
mkdir -p "$TARGET" "$HOME/.local/share/applications" "$HOME/.local/share/icons/hicolor/512x512/apps" "$HOME/.local/bin"
# Copies files without deleting unrelated user data. No root privileges are needed.
cp -R "$SOURCE"/. "$TARGET"/
chmod +x "$TARGET/MakkSocial"
ln -sf "$TARGET/MakkSocial" "$HOME/.local/bin/MakkSocial"
ln -sf "$TARGET/MakkSocial" "$HOME/.local/bin/makk-social"
cp "$TARGET/_internal/assets/logo.png" "$HOME/.local/share/icons/hicolor/512x512/apps/amerika-social.png"
sed "s|Exec=MakkSocial|Exec=\"$TARGET/MakkSocial\"|" "$SOURCE/amerika-social.desktop" > "$HOME/.local/share/applications/amerika-social.desktop"
printf '%s\n' 'Installed Makk Social for the current user.'
