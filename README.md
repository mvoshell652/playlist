# Skill Playlists

A Claude Code plugin. Group any of your installed skills under one name, then load them all from the slash menu.

Type `/playlist:` and pick one:

```
/playlist:swift review LoginView before I commit
```

Claude says `Loading 20 skills from playlist "swift"`, loads every skill in parallel, confirms `▶ swift · 20/20 skills loaded`, and carries on with your request.

## Why

Claude Code has no saved group of skills. Typing `/a /b /c` stacks six at most and nothing is remembered, so people paste the same "load these 20 skills" list over and over. A playlist is that list, saved once and one tab away.

## Install

```
/plugin marketplace add <path-or-repo>
/plugin install playlists@skill-playlists
```

Needs Python 3.8 or newer on PATH as `python3`, `python` or `py`. No other dependencies.

## Manage playlists

Every command autocompletes from `/playlists:` and also works in plain language ("add swiftdata-pro to swift").

| Command | What it does |
|---|---|
| `/playlists:new <name> [skill ...]` | Create a playlist. With no skills it captures the ones loaded in this conversation. |
| `/playlists:add <playlist> <skill ...>` | Add skills. Partial names work; Claude finds the exact id and asks when several match. |
| `/playlists:remove <playlist> <skill ...>` | Take skills out. |
| `/playlists:delete <playlist>` | Delete a whole playlist, after confirming. The skills stay installed. |
| `/playlists:list [playlist]` | See your playlists, or what is inside one. |
| `/playlists:suggest` | Propose playlists from skills you repeatedly load together. Reads local transcripts only. |

Adding or removing a skill takes effect in the current session. A new, renamed or deleted playlist appears in the `/` menu from your next session.

## How it works

Claude Code namespaces a plugin's skills by the plugin's name. This plugin keeps a second, local plugin named `playlist` in your skills directory and writes each playlist into it as a real skill, so `/playlist:` lists them like any other command:

```
~/.claude/skills/playlist/
  .claude-plugin/plugin.json
  skills/swift/playlist.json     the playlist
  skills/swift/SKILL.md          generated from it
```

```json
{
  "name": "swift",
  "description": "Full Swift and SwiftUI pass",
  "mode": "all",
  "auto_when": "",
  "skills": ["swiftui-pro", "swift-concurrency", "supabase:supabase"]
}
```

The generated `SKILL.md` is static text that tells Claude which skills to load. Playing a playlist runs no command and needs no permission.

- `mode: all` loads every skill. `mode: pick` lists each skill with its description and lets Claude load only what the request needs, which suits very large playlists.
- A playlist only plays when you call it. `set <playlist> --auto 'working on Swift code'` lets Claude load it on its own when that applies.
- A playlist does not make skills cheaper. Loading 20 skills costs the same context either way; `pick` is the only mode that loads less.

### Share with a team

`/playlists:new <name> --project` writes the playlist to `<repo>/.claude/skills/playlist/`. Commit it, and everyone who opens the repo gets `/playlist:<name>` without installing this plugin. Claude Code loads project plugins only after the workspace trust prompt, and only from the folder the session starts in.

### Safety

Project playlists are committed and shared, so every `playlist.json` is treated as untrusted. Only entries shaped like a skill id reach a generated skill; everything else is dropped and `doctor` reports the count. Names come from the folder, descriptions are flattened to one short line, and nothing you type is placed on a shell command line.

## Develop

```
python3 -m unittest discover -s tests -v
sh bin/playlists --help
```

`PLAYLISTS_HOME` and `CLAUDE_CONFIG_DIR` redirect where playlists and skills are looked up, which keeps experiments away from your real `~/.claude`.
