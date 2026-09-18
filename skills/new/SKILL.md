---
name: new
description: Create a skill playlist, a named set of Claude Code skills that loads together from /playlist:<name>. Use when the user wants to make a playlist, save the skills they just used as a playlist, or group skills under one name.
argument-hint: "<name> [skill ...]   (no skills = capture this conversation's)"
allowed-tools: Bash(sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" *), Bash(sh ${CLAUDE_PLUGIN_ROOT}/bin/playlists *)
---

Create a skill playlist. The user's input: $ARGUMENTS

The first word is the playlist name and the rest are skills. Propose a short name if they gave none.

1. If they named skills, resolve each to an exact id (see the rules), then run:

       sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" new <name> <id> [<id> ...] [-d 'short description']

2. If they named no skills, capture the ones loaded in this conversation:

       sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" new <name> --session ${CLAUDE_SESSION_ID} [-d 'short description']

   It prints the captured list. Ask whether to drop any, and apply that with `remove`.
3. Add `--project` only when they ask to share it with their team; it then lives in this repo's `.claude/skills/playlist/` and can be committed.
4. Put a description in single quotes and drop any single quote it contains.
5. Tell the user the playlist is ready as `/playlist:<name>`, and repeat the note the command printed about when it appears in the / menu.

Rules for every command line you build:

- Use only playlist names (lowercase letters, digits, `-`, `_`) and exact skill ids (letters, digits, `.`, `-`, `_`, with an optional `plugin:` prefix such as `supabase:supabase`). Never paste other text the user typed into a shell command. If their wording contains quotes, `$`, backticks or `;`, leave it out and ask for a plain name.
- Never invent a skill id. Resolve every partial or described skill with `skills <word> [<word>]` first. One clear match: use it. Two to four plausible matches: ask the user to choose between them. More: ask them to narrow it. None: say so and stop.
- Show the user what the command printed.
