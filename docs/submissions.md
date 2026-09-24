# Submission drafts for playlist

Reconstructed from the session on 24 September; the original scratch file did not survive. Nothing has been sent.

### awesome-claude-code

Eligible on or after 2 October 2026, when the repo is 14 days old with commits after the first day. Web issue form only, submitted by the owner in person. Leave the last checkbox, the one that says not to check it, unchecked.

| Field | Value |
|---|---|
| Title | `[Resource]: playlist` |
| Display name | `playlist` |
| Category | `Skills` |
| Link | `https://github.com/mvoshell652/playlist` |
| Author | `Matthew Voshell`, `https://github.com/mvoshell652` |

Description (479 characters, descriptive, not addressed to the reader):

> Groups installed skills into named playlists that load together from the slash menu. Each playlist is generated as a real skill inside a skills-directory plugin, so typing /playlist lists them and /playlist:name loads every skill in parallel and reports how many loaded. A guided menu built on Claude Code's question panel creates and edits playlists, suggests skills from the current folder's dependencies or from past sessions, and shows a token estimate before anything loads.

### awesome-claude-skills

A README-only pull request. Branch `add-playlist`, title `Add playlist to Development & Code Tools`. The line goes alphabetically between `overkill` and `Playwright Browser Automation`:

```markdown
- [playlist](https://github.com/mvoshell652/playlist) - Groups installed skills into named playlists for Claude Code and loads a whole playlist from the slash menu with /playlist:name. A guided menu creates and edits playlists and suggests skills from the current folder or from past sessions. *By [@mvoshell652](https://github.com/mvoshell652)*
```

The repository had 1,340 open pull requests and no merges since May 2026 when checked.

### buildwithclaude and claudepluginhub

On hold. Both hand visitors a marketplace-style install command, which cannot register `/playlist` and would overwrite the user's playlists on update. To be revisited once a `setup` skill exists that a marketplace install would surface and that points to the README's install line.

