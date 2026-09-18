---
name: delete
description: Delete an entire skill playlist. Use when the user wants to delete or get rid of a playlist. The skills inside it stay installed.
argument-hint: "<playlist>"
disable-model-invocation: true
allowed-tools: Bash(sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" *), Bash(sh ${CLAUDE_PLUGIN_ROOT}/bin/playlists *)
---

Delete a playlist. The user's input: $ARGUMENTS

1. Run `sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" show <playlist>` so the user sees what is about to go. If they named none, run `list` and ask which one.
2. Ask them to confirm, stating the name and skill count. Do nothing without a clear yes.
3. Run `sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" delete <playlist>` and show what it printed. Make clear that only the playlist is gone, not the skills in it.

Rules for every command line you build:

- Use only playlist names (lowercase letters, digits, `-`, `_`) and exact skill ids (letters, digits, `.`, `-`, `_`, with an optional `plugin:` prefix such as `supabase:supabase`). Never paste other text the user typed into a shell command. If their wording contains quotes, `$`, backticks or `;`, leave it out and ask for a plain name.
- Never invent a skill id. Resolve every partial or described skill with `skills <word> [<word>]` first. One clear match: use it. Two to four plausible matches: ask the user to choose between them. More: ask them to narrow it. None: say so and stop.
- Show the user what the command printed.
