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

Drafted 9 October, 793 characters, link kept for the first comment. Image: `docs/desktop-warning.png`, padded to 1200x627.

```
Start a message in the Claude Code desktop app with two skills, like /swiftui-pro /swift-testing, and you get this. Nothing sends.

The desktop app won't take a second slash command once a message starts with one. In the terminal you can stack about six. Neither remembers which skills you used, so you retype them every session.

The banner says to remove them. Playlist, which I open-sourced three weeks ago, lets you keep them.

You group your skills under one name once. My /playlist:swift loads 20, and since it's a single slash command, the desktop app sends it. It shows up in the normal slash menu and works in the terminal and IDE extensions too.

Free and MIT licensed. Repo's in the first comment.

Do you keep a fixed set of skills per project, or pick them per task?

#ClaudeCode
```

First comment:

```
Playlist repo: https://github.com/mvoshell652/playlist. Install steps are in the README.
```
