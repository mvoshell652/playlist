#!/bin/sh
# Installs or updates the playlist tool in your Claude Code skills directory.
# Your playlists (skills/<name>/) are never touched.
set -e
src=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
dest="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/playlist"
mkdir -p "$dest/.claude-plugin" "$dest/bin" "$dest/skills"
cp "$src/.claude-plugin/plugin.json" "$dest/.claude-plugin/plugin.json"
cp "$src/SKILL.md" "$dest/SKILL.md"
cp "$src/bin/playlist" "$src/bin/playlist.py" "$dest/bin/"
chmod +x "$dest/bin/playlist" "$dest/bin/playlist.py"
sh "$dest/bin/playlist" sync
echo "Installed to $dest. Start a new Claude Code session and type /playlist."
