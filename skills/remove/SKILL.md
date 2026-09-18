---
name: remove
description: Remove one or more skills from a skill playlist. Use when the user wants to drop, take out or remove a skill from a playlist. To delete a whole playlist use playlists:delete.
argument-hint: "<playlist> <skill> [skill ...]"
allowed-tools: Bash(sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" *), Bash(sh ${CLAUDE_PLUGIN_ROOT}/bin/playlists *)
---

Remove skills from a playlist. The user's input: $ARGUMENTS

The first word is the playlist; the rest are skills, possibly partial names. If no playlist is named, run `list` and ask which one.

1. Run `sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" show <playlist>` and match what the user said against the skills it lists. If a name is ambiguous, ask which.
2. Run:

       sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" remove <playlist> <id> [<id> ...]

3. Report the new skill count. The change is live in this session. The skills themselves stay installed.

Rules for every command line you build:

- Use only playlist names (lowercase letters, digits, `-`, `_`) and exact skill ids (letters, digits, `.`, `-`, `_`, with an optional `plugin:` prefix such as `supabase:supabase`). Never paste other text the user typed into a shell command. If their wording contains quotes, `$`, backticks or `;`, leave it out and ask for a plain name.
- Never invent a skill id. Resolve every partial or described skill with `skills <word> [<word>]` first. One clear match: use it. Two to four plausible matches: ask the user to choose between them. More: ask them to narrow it. None: say so and stop.
- Show the user what the command printed.
