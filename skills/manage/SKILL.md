---
name: manage
description: Create, edit, list, share and suggest skill playlists, named sets of skills loaded together with /playlists:play. Use when the user wants to save the skills they just used as a playlist, make or change a playlist, see their playlists, get playlist suggestions from their history, or check a playlist for missing skills.
argument-hint: "[new|add|remove|list|show|delete|suggest|doctor] ..."
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/bin/playlists.py *)
---

Manage skill playlists by running the bundled CLI with the Bash tool. Run exactly one command per step and show the user its output.

    python3 ${CLAUDE_PLUGIN_ROOT}/bin/playlists.py <command>

| The user wants to | Command |
|---|---|
| see their playlists | `list` |
| see one playlist and whether its skills are installed | `show <name>` |
| make a playlist from named skills | `new <name> <skill> [<skill> ...] [-d "description"] [--project]` |
| save the skills loaded in this conversation | `save-session <name> --session ${CLAUDE_SESSION_ID} [--last N] [--project]` |
| add or drop skills | `add <name> <skill> ...` or `remove <name> <skill> ...` |
| change the description or default load mode | `set <name> [-d "..."] [--mode invoke\|inline\|index]` |
| delete a playlist | `delete <name>` (confirm with the user first) |
| get suggestions from their history | `suggest`, then `new` for the ones they accept, or `suggest --dismiss <n> ...` |
| find renamed or uninstalled skills | `doctor` |

Rules:

- Skill ids are exact. Plugin skills keep their prefix, such as `supabase:supabase`. Never invent an id; when unsure, run `show` or ask.
- Names are lowercase letters, digits, `-` and `_`. Propose a short one when the user gives none.
- `--project` saves into this repo's `.claude/playlists/`, which can be committed and shared with a team. Without it the playlist is personal and works in every project.
- Modes: `invoke` (default) loads each skill through the Skill tool. `inline` pastes the skill bodies directly, which suits 2 to 4 small skills. `index` lists names and descriptions so only the relevant ones get read, which suits very large playlists.
- A new playlist works immediately: `/playlists:play <name>`, or `@@<name>` anywhere in a message.

The user's request: $ARGUMENTS
