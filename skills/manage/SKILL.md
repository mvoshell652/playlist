---
name: manage
description: Create, edit, list, share and suggest skill playlists, which are named sets of Claude Code skills loaded together with /playlists:play. Use when the user wants to save the skills they just used as a playlist, make or change a playlist, see their playlists, find skill ids, get playlist suggestions from their history, or check a playlist for missing skills.
argument-hint: "[new|add|remove|list|show|skills|rename|delete|suggest|doctor] ..."
allowed-tools: Bash(sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" *), Bash(sh ${CLAUDE_PLUGIN_ROOT}/bin/playlists *)
---

Manage skill playlists by running the bundled CLI with the Bash tool. Run one command per step and show the user what it printed.

    sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" <command>

| The user wants to | Command |
|---|---|
| see their playlists | `list` |
| see one playlist and whether its skills are installed | `show <name>` |
| find the exact id of an installed skill | `skills <word> [<word> ...]` |
| make a playlist from named skills | `new <name> <skill> [<skill> ...] [-d "description"] [--project]` |
| save the skills loaded in this conversation | `save-session <name> --session ${CLAUDE_SESSION_ID} [--last N] [--project]` |
| add or drop skills | `add <name> <skill> ...` or `remove <name> <skill> ...` |
| change the description or default load mode | `set <name> [-d "..."] [--mode invoke\|inline\|index]` |
| rename a playlist | `rename <name> <new-name>` |
| delete a playlist | `delete <name>`, after the user confirms |
| get suggestions from their history | `suggest`, then `new` for the ones they accept, or `suggest --dismiss <n> ...` |
| find renamed or uninstalled skills | `doctor` |

Rules:

- Build each command only from playlist names and skill ids. Names are lowercase letters, digits, `-` and `_`. Skill ids are letters, digits, `.`, `-`, `_`, with an optional `plugin:` prefix such as `supabase:supabase`. If the user's wording contains anything else, such as quotes, `$`, backticks or `;`, do not put it on the command line; ask them for a plain name instead.
- Put a description in single quotes and drop any single quote it contains.
- Never invent a skill id. When unsure, run `skills <word>` and pick from what it prints.
- Propose a short name when the user gives none.
- `--project` saves into this repo's `.claude/playlists/`, which can be committed and shared with a team. Without it the playlist is personal and works in every project. To share a personal playlist, send its JSON file; `show` prints the path.
- Modes: `invoke` (default) loads each skill through the Skill tool. `inline` pastes the skill bodies directly, which suits 2 to 4 small skills. `index` lists names and descriptions so only the relevant ones get read, which suits very large playlists.
- A new playlist works immediately: `/playlists:play <name>`, or `@@<name>` anywhere in a message.

The user's request: $ARGUMENTS
