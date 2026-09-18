# Contributing

Bug reports, ideas and pull requests are welcome.

## Run it from a checkout

```
python3 -m unittest discover -s tests -v
sh bin/playlist --help
```

Point the tool at a scratch folder so experiments never touch your real skills:

```
export CLAUDE_CONFIG_DIR=$(mktemp -d)
sh bin/playlist new demo some-skill other-skill
```

To try a change inside Claude Code, run `sh install.sh`. It copies the tool into `~/.claude/skills/playlist/` and leaves your playlists alone. Start a new session, or type `/reload-plugins`.

## What to know before changing things

- **Standard library only, Python 3.8 and newer.** The tool has no install step, and that is a feature. CI runs the tests on Linux, macOS and Windows.
- **The words on the question panels are part of the product.** `SKILL.md` has a Wording section with the rules and a word list, and a test holds the questions to them.
- **Playlist files are untrusted.** A project playlist arrives through a repository. Anything read from a `playlist.json` is validated before it reaches a generated skill or a command line. New fields need the same care, and a test.
- **The README's command table is tested against the real CLI.** Add a command and the test tells you to document it.
- Every behaviour change comes with a test.

## Pull requests

Keep them small and say what changes for the person using the tool. If the change touches a question panel or the hover text, include a screenshot.
