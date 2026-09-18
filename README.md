# Playlist

Skill playlists for Claude Code. Group any of your installed skills under one name, then load them all from the slash menu.

Type `/playlist` and the menu shows the tool, then every playlist you have. Hover over one to see what is in it:

<img src="docs/menu.png" width="760" alt="Claude Code's slash menu after typing /playlist. It lists playlist, playlist:db, playlist:swift and four more. The hover text for playlist:swift reads: Full Swift and SwiftUI pass. 20 skills, followed by every skill grouped under SWIFTUI and SWIFT.">

Pick one and add your request:

```
/playlist:swift review LoginView before I commit
```

Claude says how many skills it is loading, loads every one in parallel, confirms `▶ swift · 20/20 skills loaded`, and carries on with your request:

<img src="docs/loading.png" width="460" alt="Claude Code replying: Loading 20 skills from playlist swift, with the first skill running.">

## Why

Claude Code has no saved group of skills. Typing `/a /b /c` stacks six at most and nothing is remembered, so people paste the same "load these 20 skills" list over and over. A playlist is that list, saved once and one tab away.

## Install

```
d=$(mktemp -d) && git clone --depth 1 https://github.com/mvoshell652/playlist "$d" && sh "$d/install.sh"
```

Then start a new Claude Code session and type `/playlist`.

The script copies the tool into `~/.claude/skills/playlist/`. It needs Python 3.8 or newer on PATH as `python3`, `python` or `py`, and nothing else. It works in the terminal, the desktop app and the IDE extensions, because they share that folder.

**Update:** run the same line again. Your playlists are never touched.

**Uninstall:** delete the folder. This also deletes your playlists, so copy `skills/` out first if you want to keep them.

```
rm -rf ~/.claude/skills/playlist
```

### Why this is not a `/plugin install`

Claude Code copies a marketplace plugin into a versioned cache folder and replaces that folder on every update. Your playlists live inside the tool's folder, because that is what makes them show up as `/playlist:<name>`, so a marketplace update would delete them. A marketplace plugin also cannot register a bare command: installed that way, `/playlist` itself disappears and only `/playlist:<name>` remains.

A plugin that sits in your skills directory is loaded in place, keeps its files, and gets both the bare command and the namespaced ones. That is a documented Claude Code feature ([skills-directory plugins](https://code.claude.com/docs/en/plugins-reference#skills-directory-plugins)), and it is the only layout that does everything this tool needs.

## Create and edit playlists

Run `/playlist` with nothing after it. It walks you through a short menu using Claude's own question panel, so you pick instead of type:

1. **What do you want to do?** Create a playlist, edit one, delete one, or see your playlists.
2. **What should we call it?** A few suggested names, or type your own.
3. **Which skills do you want in it?** You never search one word at a time:
   - **Type them all on one line.** Names, partial names or a description: `nuxt vue pinia shadcn vitest a11y`, or "everything for a Nuxt app with Pinia and testing". Claude resolves every word in one pass.
   - **Suggest for this project.** Claude reads the project's dependency files and proposes the installed skills that fit the stack.
   - **From this conversation**, or **from your history** of skills you often load together.
4. **Review one list.** Claude shows what it gathered, marks the places where it chose between similar skills so you can swap them, and asks only about genuine toss-ups. Create it, add more, or remove some.

Editing offers add skills, remove skills, rename and change description. Deleting always asks first, and never touches the skills themselves.

If you already know what you want, say it and the menu skips ahead:

```
/playlist new nuxt-app with nuxt vue pinia shadcn vitest a11y
/playlist add swiftdata to swift
/playlist delete review
```

Adding or removing a skill takes effect in the current session. When you create a playlist, the menu ends by offering to **play it now**, which loads its skills into the conversation straight away. To see a new or renamed playlist in the `/` menu without waiting for your next session, type `/reload-plugins`; Claude Code reserves that command for you, so the tool cannot run it on your behalf.

## Options

### Ways to play a playlist

| You type | What happens |
|---|---|
| `/playlist:swift` | Loads the playlist and stops, ready for your next message |
| `/playlist:swift review LoginView` | Loads it, then carries out the request with those skills applied |
| `/playlist swift review LoginView` | The same, through the menu command. This works for a playlist you created a moment ago, before it has reached the slash menu |
| "Play it now" at the end of creating one | Loads the new playlist into the conversation straight away |

### Settings for each playlist

Every playlist has four settings. Change them from `/playlist`, then **Edit a playlist**, or say what you want in one line.

| Setting | Values | What it does | Say this |
|---|---|---|---|
| Load mode | `all` (default) | Loads every skill, every time | `/playlist make swift load every skill` |
| | `pick` | Lists each skill with its description and lets Claude load only the ones the request needs. Suits large playlists, and is the only mode that uses less context | `/playlist make swift load only what a request needs` |
| Auto-load rule | off (default) | The playlist plays only when you call it, so many skills never load by surprise | `/playlist stop loading swift automatically` |
| | a rule you write | Claude may load the playlist on its own when the rule applies | `/playlist load swift automatically when working on Swift code` |
| Description | short text | Shown first in the hover text beside the playlist | `/playlist change the description of swift` |
| Where it lives | personal (default) | `~/.claude/skills/playlist/`, available in every project | |
| | project | `<repo>/.claude/skills/playlist/`, committed with the repo. Experimental, see below | `/playlist share swift with my team` |

A playlist does not make skills cheaper. Loading 20 skills costs the same context whether you load them one by one or from a playlist. `pick` is the only setting that loads less.

### Everything the menu understands

Run `/playlist` alone for the guided steps, or add a request and it skips the steps you already answered.

| You want to | Say |
|---|---|
| Create from skills you name | `/playlist new nuxt-app with nuxt vue pinia shadcn vitest a11y` |
| Create from the skills loaded in this conversation | `/playlist save the skills I just used as review` |
| Create from your project's stack | `/playlist`, then **Create**, then **Suggest for this project** |
| Get ideas from your history | `/playlist suggest playlists from my history` |
| Add or remove skills | `/playlist add swiftdata to swift`, `/playlist remove focusengine from swift` |
| Rename or delete | `/playlist rename db to data`, `/playlist delete review` |
| See what you have | `/playlist show my playlists`, `/playlist show swift` |
| Check for renamed or uninstalled skills | `/playlist check my playlists` |

Partial skill names are fine. Claude looks up the exact ids, picks the obvious match, marks the places where it chose between similar skills, and asks only when it cannot tell. Deleting always asks first and never removes the skills themselves.

### Command line

The menu calls a small command line tool, and you can use it directly:

```
sh ~/.claude/skills/playlist/bin/playlist <command>
```

| Command | What it does |
|---|---|
| `list` | Your playlists, with skill counts, location and load mode |
| `show <playlist>` | The skills in one playlist, and whether each is installed |
| `new <name> [skill ...]` | Create a playlist. `--session <id>` captures a conversation's skills, `--last N` limits that to its last N turns, `-d "text"` sets the description, `--mode all\|pick`, `--project` saves it in the current repo, `--force` replaces an existing one |
| `add <playlist> <skill ...>` | Add skills. `--session <id>` adds everything loaded in a conversation |
| `remove <playlist> <skill ...>` | Remove skills. It refuses to empty a playlist; delete it instead |
| `set <playlist>` | `-d "text"`, `--mode all\|pick`, `--auto "when ..."`, `--no-auto` |
| `rename <playlist> <new-name>` | Rename, keeping its skills and settings |
| `share <playlist>` | Copy a personal playlist into the current repo so it can be committed. Your personal copy stays |
| `delete <playlist>` | Delete the playlist. The skills stay installed |
| `skills [word ...]` | Search your installed skills by word. `--limit N` |
| `match <word ...>` | The best installed skills for several words in one pass. `--limit N` per word |
| `loaded --session <id>` | The skills a conversation has loaded, without creating anything |
| `suggest` | Sets of skills you repeatedly load in the same turn. `--min-support N` sets how often (default 3), `--dismiss N ...` hides suggestions for good, `--json` for scripts |
| `doctor` | Checks every playlist for skills that are no longer installed and for hand-edited files |
| `sync` | Regenerates every playlist's `SKILL.md` from its `playlist.json` |

Playlist names use lowercase letters, digits, `-` and `_`, up to 48 characters. Words the menu acts on, such as `new`, `show` and `delete`, cannot be names. Skill ids are written exactly as Claude Code shows them, including a plugin prefix such as `supabase:supabase`.

### The playlist file

Each playlist is one folder with two files. `playlist.json` is the one to edit; `SKILL.md` is generated from it, so run `sync` after a hand edit.

```json
{
  "name": "swift",
  "description": "Full Swift and SwiftUI pass",
  "mode": "all",
  "auto_when": "",
  "skills": ["swiftui-pro", "swift-concurrency", "supabase:supabase"]
}
```

| Field | Meaning |
|---|---|
| `name` | For reference only. The folder name is what counts |
| `description` | Short text shown first in the hover text. Flattened to one line |
| `mode` | `all` or `pick` |
| `auto_when` | Empty, or the rule that lets Claude load the playlist unasked |
| `skills` | Skill ids in load order. Entries that are not shaped like a skill id are ignored, and `doctor` says how many |

The hover text is built from these: the description, the skill count, then every skill, grouped under a capitalised label when three or more share a first word. Claude Code caps a description at 1,024 characters, so a very large playlist lists what fits and ends with "And N more."

### Troubleshooting

| What you see | What to do |
|---|---|
| A new or renamed playlist is missing from the `/` menu | Type `/reload-plugins`, or start a new session. Until then `/playlist <name>` plays it |
| The hover text is out of date | The same. Claude Code reads it when plugins load |
| A skill is reported as not loaded | Run `/playlist check my playlists`. The skill was probably renamed or uninstalled |
| "not found on disk" beside a skill | Built-in skills and skills synced from claude.ai are never on disk, so this is normal for them. For anything else, check the spelling with `skills <word>` |
| "Python 3.8 or newer was not found" | Install Python and make sure `python3`, `python` or `py` is on PATH |

## How it works

The tool is a plugin that lives in your skills directory. Claude Code registers such a plugin's root skill under its bare name and the skills inside it as `name:skill`, which is what puts the menu at `/playlist` and each playlist at `/playlist:<name>`:

```
~/.claude/skills/playlist/
  .claude-plugin/plugin.json
  SKILL.md                       /playlist, the guided menu
  bin/                           the CLI the menu calls
  skills/swift/playlist.json     a playlist
  skills/swift/SKILL.md          /playlist:swift, generated from it
```

A generated `SKILL.md` is static text that tells Claude which skills to load. Playing a playlist runs no command and needs no permission.

### Share with a team (experimental)

Ask `/playlist` to share a playlist with your team and it writes the playlist to `<repo>/.claude/skills/playlist/`, which you can commit. Claude Code loads a plugin from a project's skills folder only after the workspace trust prompt, and only from the folder the session starts in. Running a personal and a project copy of the `playlist` plugin side by side has not been tested yet, so treat this as a preview.

### Safety

Project playlists are committed and shared, so every `playlist.json` is treated as untrusted. Only entries shaped like a skill id reach a generated skill; everything else is dropped and `doctor` reports the count. Names come from the folder, descriptions are flattened to one short line, and text you type into the menu is reduced to an allow-list of characters before it goes near a command.

## Develop

```
python3 -m unittest discover -s tests -v
sh bin/playlist --help
```

`PLAYLISTS_HOME` and `CLAUDE_CONFIG_DIR` redirect where playlists and skills are looked up, which keeps experiments away from your real `~/.claude`.

## License

MIT. See [LICENSE](LICENSE).
