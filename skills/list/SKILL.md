---
name: list
description: Show the user's skill playlists, or the skills inside one. Use when the user asks what playlists they have, what is in a playlist, or whether a playlist's skills are still installed.
argument-hint: "[playlist]"
allowed-tools: Bash(sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" *), Bash(sh ${CLAUDE_PLUGIN_ROOT}/bin/playlists *)
---

The user's input: $ARGUMENTS

- No playlist named: run `sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" list`.
- A playlist named: run `sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" show <playlist>`.
- They ask whether anything is broken, renamed or missing: run `sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" doctor`.
- They want to rename one, change its description, make it load only what a request needs (`--mode pick`), or let Claude load it unasked (`--auto 'when ...'`): use `rename <old> <new>` or `set <playlist> ...`; `sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" set --help` lists the options.

Remind them that a playlist plays from the / menu: type `/playlist:` and pick one.

Rules for every command line you build:

- Use only playlist names (lowercase letters, digits, `-`, `_`) and exact skill ids (letters, digits, `.`, `-`, `_`, with an optional `plugin:` prefix such as `supabase:supabase`). Never paste other text the user typed into a shell command. If their wording contains quotes, `$`, backticks or `;`, leave it out and ask for a plain name.
- Never invent a skill id. Resolve every partial or described skill with `skills <word> [<word>]` first. One clear match: use it. Two to four plausible matches: ask the user to choose between them. More: ask them to narrow it. None: say so and stop.
- Show the user what the command printed.
