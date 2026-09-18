# Security

This tool writes files into your Claude Code skills folder and runs a small Python script, so security reports are welcome and taken seriously.

## Report a vulnerability

Report it privately: open the [Security tab](https://github.com/mvoshell652/playlist/security/advisories/new) and choose **Report a vulnerability**. Please do not open a public issue for a security problem.

Include what you did, what happened, and the output of:

```
sh ~/.claude/skills/playlist/bin/playlist doctor
```

You can expect a first reply within a week. Fixes ship in a new release, and the release notes credit you unless you ask otherwise.

## What counts

- Anything that lets a playlist file, a skill file or text typed into the menu run a command, read a file outside the skills folders, or put instructions in front of Claude that the user did not write.
- A project playlist, which arrives through a repository and is treated as untrusted, doing any of the above.

## How the tool protects you

- Playing a playlist runs no command. A generated `SKILL.md` is static text.
- Only entries shaped like a skill id are written into a generated skill. Everything else in a `playlist.json` is dropped, and `doctor` reports the count.
- Text typed into the menu is reduced to an allow-list of characters before it goes near a command line.
- Skill descriptions are read only from real Markdown files. A project skill that is a symlink to somewhere outside the repository is never read.

## Supported versions

The latest release.
