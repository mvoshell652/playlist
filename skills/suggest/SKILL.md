---
name: suggest
description: Suggest skill playlists from the user's own history, based on skills they repeatedly load in the same turn. Use when the user asks for playlist ideas or suggestions.
allowed-tools: Bash(sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" *), Bash(sh ${CLAUDE_PLUGIN_ROOT}/bin/playlists *)
---

1. Run `sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" suggest`. It reads local transcripts only; nothing leaves the machine.
2. Show each suggestion with its number, its skills and how often they were loaded together, and propose a short name for each.
3. For the ones the user accepts, run `sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" new <name> <id> [<id> ...]` with the exact ids printed. Add `--project` only if the suggestion was seen in one project and they want to share it.
4. For the ones they never want to see again, run `sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" suggest --dismiss <n> [<n> ...]` using the numbers from step 1.

Rules for every command line you build:

- Use only playlist names (lowercase letters, digits, `-`, `_`) and exact skill ids (letters, digits, `.`, `-`, `_`, with an optional `plugin:` prefix such as `supabase:supabase`). Never paste other text the user typed into a shell command. If their wording contains quotes, `$`, backticks or `;`, leave it out and ask for a plain name.
- Never invent a skill id. Resolve every partial or described skill with `skills <word> [<word>]` first. One clear match: use it. Two to four plausible matches: ask the user to choose between them. More: ask them to narrow it. None: say so and stop.
- Show the user what the command printed.
