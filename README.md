# Skill Playlists

A Claude Code plugin. Save any set of skills as a named playlist, then load all of them with one reference.

```
/playlists:play swift review LoginView before I commit
```

```
review LoginView with @@swift before I commit
```

Both load every skill in the `swift` playlist in parallel, confirm `▶ swift: 21/21 loaded`, and carry on with the request.

## Why

Claude Code has no saved group of skills. Typing `/a /b /c` stacks six at most and nothing is remembered, so people paste the same "load these 20 skills" list over and over. A playlist is that list, saved once.

## Install

```
/plugin marketplace add <path-or-repo>
/plugin install playlists@skill-playlists
```

Needs Python 3.8 or newer on PATH as `python3`, `python` or `py`. No other dependencies.

## Use

Ask in plain language and the `playlists:manage` skill runs the right command:

- "save the skills I just used as a playlist called swift"
- "make a playlist called db with supabase and supabase-postgres-best-practices"
- "suggest playlists from my history"
- "add swiftdata-pro to swift", "show swift", "rename db to data", "delete db"
- "which skills do I have for swift?" searches installed skills so you can pick exact ids

Or run the CLI yourself: `sh bin/playlists --help`.

| Reference | What it does |
|---|---|
| `/playlists:play swift` | load one playlist |
| `/playlists:play swift+db` | load several, de-duplicated |
| `/playlists:play swift:index` | override the load mode once |
| `@@swift` anywhere in a message | same as play, mid-sentence, several per message; ignored inside `code` and fenced blocks |

A playlist you just created works in the same session. Playlists are data read at play time, not generated skills, so nothing needs reloading.

## Load modes

| Mode | What reaches the model | Good for |
|---|---|---|
| `invoke` (default) | an instruction to call the Skill tool once per skill, in parallel, then report `n/n loaded` | any size; identical to loading each skill by hand |
| `inline` | the skill bodies themselves, up to 24,000 characters; the rest fall back to `invoke` and the output says which | 2 to 4 small skills, saves a round trip |
| `index` | names, descriptions and paths; Claude reads only what the request touches | very large playlists where loading everything wastes context |

A playlist does not make skills cheaper. `invoke` and `inline` cost the same context as loading each skill yourself. Only `index` loads less.

## Where playlists live

- Personal: `~/.claude/playlists/<name>.json`, available in every project.
- Project: `<repo>/.claude/playlists/<name>.json` with `--project`. Commit it to share with a team. A project playlist wins over a personal one with the same name.

```json
{
  "name": "db",
  "description": "Supabase schema and query work",
  "mode": "invoke",
  "skills": ["supabase", "supabase-postgres-best-practices"]
}
```

To share a personal playlist, send the JSON file. A playlist's name is its filename.

## Safety

Project playlists are committed and shared, so the plugin treats every playlist file as untrusted:

- Nothing you type is placed on a shell command line. `/playlists:play` injects a fixed catalog of your playlists and Claude matches the name against it.
- Only values that look like a skill id (`swiftui-pro`, `supabase:supabase`) are passed to the model. Anything else in a playlist file is dropped, and `doctor` reports how many entries were ignored. Descriptions are flattened to one short line and never included in load text.
- `inline` and `index` read only real markdown files. A project skill that is a symlink to somewhere outside the repo is never read.
- The `@@name` hook cannot block or rewrite a prompt. On any error it does nothing.

## Suggestions

`suggest` reads your local transcripts in `~/.claude/projects`, finds sets of skills you repeatedly load in the same turn, and proposes them. It skips sets an existing playlist already covers and anything you dismissed. Nothing leaves your machine.

## Limits

- Claude Code only: terminal, desktop Code tab, IDE extensions. Not claude.ai chat.
- `@@name` needs the plugin's hook. Where hooks are unavailable, use `/playlists:play`.
- Where shell injection is disabled by policy, `/playlists:play` asks Claude to run the resolver with the Bash tool instead.
- `doctor` reports skills it cannot find on disk. Built-in and claude.ai-synced skills always show as not found.

## Develop

```
python3 -m unittest discover -s tests -v
claude --plugin-dir . -p "/playlists:play <name> ..."
```

`PLAYLISTS_HOME` and `CLAUDE_CONFIG_DIR` redirect where playlists and skills are looked up, which keeps experiments away from your real `~/.claude`.
