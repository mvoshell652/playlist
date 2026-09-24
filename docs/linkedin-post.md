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
