---
name: add
description: Add one or more skills to an existing skill playlist. Use when the user wants to add, put or include a skill in a playlist.
argument-hint: "<playlist> <skill> [skill ...]"
allowed-tools: Bash(sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" *), Bash(sh ${CLAUDE_PLUGIN_ROOT}/bin/playlists *)
---

Add skills to a playlist. The user's input: $ARGUMENTS

The first word is the playlist. The rest are skills, which may be partial names ("swiftdata") or a description ("the two supabase ones"). If no playlist is named, run `list` and ask which one.

1. Resolve each skill to an exact id (see the rules).
2. Run:

       sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" add <playlist> <id> [<id> ...]

   To add everything loaded in this conversation instead: `add <playlist> --session ${CLAUDE_SESSION_ID}`.
3. Report the new skill count. The change is live in this session.

Rules for every command line you build:

- Use only playlist names (lowercase letters, digits, `-`, `_`) and exact skill ids (letters, digits, `.`, `-`, `_`, with an optional `plugin:` prefix such as `supabase:supabase`). Never paste other text the user typed into a shell command. If their wording contains quotes, `$`, backticks or `;`, leave it out and ask for a plain name.
- Never invent a skill id. Resolve every partial or described skill with `skills <word> [<word>]` first. One clear match: use it. Two to four plausible matches: ask the user to choose between them. More: ask them to narrow it. None: say so and stop.
- Show the user what the command printed.
