# LinkedIn launch post

Drafted 18 September, 1,145 characters, link kept for the first comment.

```
I typed the same 20 skill names into Claude Code 13 times before I admitted I had a problem.

So I built the fix, and today it is open source.

If you use Claude Code with a lot of skills, you know the routine. Every new session starts with "load swiftui-pro, swift-concurrency, swift-testing" and fifteen more. Claude stacks about six skills per message, and nothing is saved for next time.

Playlist fixes that.

You group any of your installed skills under one name. Then you type /playlist:swift and all 20 load at once. Claude tells you how many loaded and gets on with your request.

What I cared about while building it:

→ It feels native. Type /playlist and the normal slash menu lists your playlists. No new syntax.
→ You never search skill by skill. Type them all on one line, or let Claude read your project's dependencies and suggest the set.
→ No surprises. You see a token estimate before anything loads.
→ Playing a playlist runs no commands. Tested on macOS, Linux and Windows.

Free, MIT licensed. Link in the comments.

Which skills do you load at the start of every session?

#ClaudeCode #AIAgents #DeveloperTools #OpenSource
```

First comment:

```
Repo and the one-line install: https://github.com/mvoshell652/playlist

It installs with a small script, not /plugin install. The README explains why: a marketplace install cannot register the bare /playlist command and would wipe your playlists on every update.
```


# LinkedIn follow-up: the desktop app warning

Drafted 9 October, 1,068 characters, link kept for the first comment. Image: `docs/desktop-warning.png`, padded to 1200x627.

```
I tried to load two skills at once in the Claude Code desktop app today. It refused to send my message.

That is the warning in the image. Once a message starts with a slash command, it cannot contain a second one.

Which is funny, because that is the exact problem I built Playlist to solve.

If you use Claude Code with a lot of skills, you know the routine. Every session starts with the same list. The terminal stacks about six skills per message. The desktop app refuses a second one. Neither saves the list for next time.

Playlist turns the list into one command.

Group your skills under a name once. Then type /playlist:swift and all 20 load. It is a single slash command, so the desktop app sends it. Claude tells you how many skills loaded and gets on with your request.

→ It shows up in the normal slash menu. No new syntax.
→ It works in the desktop app, the terminal and the IDE extensions.
→ Free and MIT licensed.

Link in the comments.

How many skills do you load before you start real work?

#ClaudeCode #AIAgents #DeveloperTools #OpenSource
```

First comment:

```
Repo and the one-line install: https://github.com/mvoshell652/playlist
```
