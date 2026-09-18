---
name: play
description: Load a saved skill playlist, a named set of skills, in one go. Use when the user says "play <name>", "load my <name> playlist/skills", or names a playlist to apply to their request.
argument-hint: "<playlist>[+<playlist>][:invoke|inline|index] [your request]"
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/bin/playlists.py *)
---

!`python3 ${CLAUDE_PLUGIN_ROOT}/bin/playlists.py play $0`

If the line above is a literal command or says shell execution is disabled, run it yourself with the Bash tool, passing the playlist name the user gave, and follow what it prints:

    python3 ${CLAUDE_PLUGIN_ROOT}/bin/playlists.py play <playlist>

If it printed a playlist error, tell the user what it said and stop; do not guess at skills.

The user's message, where the first word is the playlist reference and the rest is their request: $ARGUMENTS
