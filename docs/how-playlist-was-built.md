# How Playlist was built

A record of the one working day, 18 September 2026, in which this tool went from a complaint typed into Claude Code to a public, tested, released repository. It is written from the session transcripts and the git history, and it quotes the owner's messages as typed, typos included, because the wording of each correction is what steered the design.

The person building it was Matthew Voshell, working in the Claude Code desktop app with Claude as the pair. Times are Pacific.

## Contents

1. [The complaint](#1-the-complaint)
2. [Research before building](#2-research-before-building)
3. [The first build, and the review that broke it](#3-the-first-build-and-the-review-that-broke-it)
4. [Finding the native shape](#4-finding-the-native-shape)
5. [Making the menu usable](#5-making-the-menu-usable)
6. [The refresh problem](#6-the-refresh-problem)
7. [Hover text](#7-hover-text)
8. [Going public](#8-going-public)
9. [Distribution](#9-distribution)
10. [What the day settled](#10-what-the-day-settled)
11. [Timeline](#11-timeline)
12. [Mechanics verified along the way](#12-mechanics-verified-along-the-way)
13. [What is still open](#13-what-is-still-open)

Appendices: [submission drafts](#appendix-a-submission-drafts), [LinkedIn post](#appendix-b-linkedin-post).

---

## 1. The complaint

11:26. The first message, sent from the MatchRox mobile repository with no plan beyond the problem:

> I am always having to call multiple skills when i send a message, but there is no way in claude to insert a pre built collection is skills calls; I think I want to build a product for claude that cant do that; IE either you suggest collections or a user can build a collection of skill calls and then they refernce the once collection and it inserts all the skills for the users...

Before designing anything, Claude mined the owner's own Claude Code transcripts, 123 sessions, to see how real the problem was. Of 352 turns that invoked a skill, 69 invoked two or more. The same 21-skill Swift and SwiftUI set had been loaded about 13 times, usually by pasting a long prompt that began "Load all Swift and SwiftUI skills in parallel". Those 21 skill files added up to about 220 KB, roughly 55,000 tokens, every time.

Four minutes later the owner set the scope, and it was wider than their own habit:

> these are just examples though, i want to productize this idea so users can create "playlists" of whatever collection of skills they want

That sentence named the product. Everything after it was about making "playlist" mean something real inside Claude Code.

## 2. Research before building

Claude ran a research workflow with three agents in parallel: one to verify the exact mechanics of Claude Code's extension points against the official docs, one to look for prior art, and one to assess distribution. Three designs were then drafted from different angles, scored by two judges, and merged into one spec.

The findings that shaped everything:

- Anthropic had already been asked for this. Issue anthropics/claude-code#17349, "Allow users to trigger multiple Skills within a single message", was closed as not planned. The native workaround, typing `/a /b /c` at the start of a message, stacks about six skills and remembers nothing.
- With over a thousand skills installed, the listing Claude sees each turn is capped at about 1% of the context window. Descriptions are dropped for the least-used skills, so auto-triggering by description becomes unreliable. That is why people load skills by hand, and why a saved list is worth having.
- A plugin can ship skills, agents, hooks and MCP servers. It cannot ship a window, a pane or any drag-and-drop surface. This ruled out a whole class of designs before they were tried.
- The judges split. The tie-break rule was to prefer whichever design used only mechanics the research had verified.

The research also produced a fact that turned out to be false, and was corrected later in the day: that the desktop app does not notice a new skill file until the next session. See section 6.

## 3. The first build, and the review that broke it

By 12:01 the first version existed: a marketplace plugin called `playlists` with a `/playlists:play` command, a `/playlists:manage` command, a hook that expanded `@@name` tokens anywhere in a message, three load modes, and a miner that suggested playlists from transcript history. Playlists were JSON files read at play time, chosen precisely because a generated skill file would not, it was believed, appear until the next session.

Claude then ran an adversarial review: four reviewers, each with a different lens, and a separate skeptic assigned to refute every finding. Twenty-nine findings came back; twenty-seven survived verification. Two were critical:

- The play command put the user's typed argument straight into a shell line. Typing `/playlists:play $(anything)` ran `anything`. This is a property of how Claude Code substitutes `$0` into a `` !`command` `` line, and no amount of quoting in the template fixes it, because the value is substituted as raw text before the shell sees it.
- Project playlists are committed to repositories and shared, so a playlist file is untrusted. Nothing validated the fields, and a skill entry containing a newline and an instruction reached the model verbatim.

The fix, committed at 12:34, removed every path from typed text to a shell, treated every playlist file as untrusted, and added a regression test for each finding. The rule that came out of it is now the second paragraph of the CLI's docstring: nothing a user types is ever placed on a shell command line, and nothing read from a playlist file reaches the model unless it matches a strict pattern.

The owner had the plugin installed and asked to try it at 12:38, then at 19:41: "how do I manage the playlists?"

## 4. Finding the native shape

This is the part of the day where the product was actually designed, and the owner did it by saying no.

**12:42.** The first idea for management was a visual builder:

> I was thinking more of some kind of plugin ui where the user can select from their currently installed skills and drag / push them into differten playlists, the same way you would build a music playlist

Claude started planning a local web page and was interrupted twice within a minute:

> no, does claude offer this as a built in plugin? like i want to trigger the manage from claude and have it open in a claude based window?

> no.... i want this product to seem claude native, if thats the case, how will users interact with and call the different playlists?

The answer, checked against the plugin reference, was that no plugin gets a window. The only native surfaces are the slash menu, plain conversation, and the question panel Claude uses to ask the user to choose between options. So the product had to be built from those three things.

**12:51.** The owner then wrote the specification in one message:

> I want the user to call "/playlist: " and have it auto complete to show all options, ie all existing playlists so the user can tab / select the playlist they want to pull in; What happens once they do? does the response from the agent say "loading 20 skills" so its obviously the playlist loaded many skills?
>
> and then managing the skills, how can I easiliy add / remove a skill from a specific playlist; and then i need to manage (new / remove) entire playlists, make sense?

Three requirements: autocomplete under `/playlist:`, a visible "loading N skills" line, and easy management. The mechanism that satisfies the first is a Claude Code feature called a skills-directory plugin: a folder under `~/.claude/skills/` with a manifest, whose inner skills register as `pluginname:skillname`. Each playlist became a real generated skill inside a plugin named `playlist`. The `/playlist:` prefix came free, and so did tab completion.

**13:01.** The owner sent a screenshot of the menu and asked why actions and playlists were "commingled". The six management commands, `playlists:new`, `playlists:add` and so on, sorted in between the playlists because the desktop menu ranks prefix matches by name length. Claude offered a different prefix, `/dj:` or `/pl:`, and was refused:

> no, alwyays call it "playlist" but, yeah, i think we collpase the actions into a single command and then utilize the text field question / answer module and users can select the action they want in a stepped process

**13:25.** After seeing `playlists:manage` in the menu:

> first, no "s" on playlist, I see its added to the manage line; second, I think it should just be the root "/playlist" and that base command triggers the manage flow, understood?

That last correction forced a change in the repository's shape. A skills-directory plugin with a `SKILL.md` at its root registers a bare command under the plugin's own name, which Claude verified in a sandbox before rebuilding. The whole tool became one folder: the root skill is the menu, `/playlist`, and each playlist sits beneath it as `/playlist:<name>`. The separate manager plugin, the `@@name` hook and the two extra load modes were deleted. At 13:28 the owner sent a screenshot of the menu showing `playlist`, `playlist:db` and `playlist:swift`, and wrote "great job!"

## 5. Making the menu usable

The guided menu was dry-run by five agents playing scripted users before the owner ever saw it. They found eighteen defects in its instructions, including a one-option question that the panel rejects, an "Add all 20" button shown while removing skills, and a typed description reaching a shell with only a blacklist in the way. All were fixed before the first live run.

**13:33.** The owner ran it and rejected the skill-selection step:

> creating the name etc, is great, the only thing I dont like is selecting the skills themselves, i dont like that I have to search via keyword, esp when I want to add multiple skills like the image attached across differnert types, this would take forever in the current workflow

The screenshot showed a seven-skill Nuxt stack. Searching one keyword at a time would have taken seven rounds. The replacement lets the user type every skill on one line, or asks Claude to read the project's dependency files and propose skills, then shows one review list. A new `match` command resolves many words in a single call; the seven-skill example resolved in 0.3 seconds against the owner's 1,300 installed skills. "this is a lot better, i like it" came at 13:39.

**15:14.** A second pass on the panels, after the owner noticed the wording did not explain itself:

> its not obvious that the suggstions are based on the current folder the user is in, etc, I know questions allow for subtitles, right? So can we write the question itself better and then add a subtitle to provide more detailed explanation for the user?

The panel has no subtitle field, but each option has a grey description line, and a plain line of chat can sit above the panel. Every question was rewritten as one short sentence, every option's description was made to say what would happen and what it was based on, with real values such as the folder's name and a token estimate, and "Suggest for this project" became "Suggest from this folder". A Wording section with a word list was added to the menu's instructions so that improvised text stays consistent, and a test now holds every question to those rules.

## 6. The refresh problem

**13:39.** The same message that approved the skill picker asked the question that occupied the next twenty minutes:

> if i'm in a conversation, I create a new playlist, then I finish, how do I ensure the playlist is now available in the list? right now i dont see it

The research from the morning had said new skill files are not seen until the next session. Claude re-tested it and found the earlier test had been too fast. A plain skill under `~/.claude/skills/` does appear in the running session after about ten seconds. A skill inside a plugin folder does not, until `/reload-plugins` is typed or a new session starts. The colon in `playlist:swift` exists only because the playlists live in a plugin folder, so the colon and the instant refresh are mutually exclusive.

Claude built the alternative, plain skills named `playlist-<name>`, and asked which the owner preferred. The reply arrived mid-build:

> oh sorry, i hate the hypen, keep as colon

The hyphen work was saved as a patch and discarded. The owner then tried three ways to close the gap:

> can we just auto issue the reload plugins command when we finish creating a new playlist?

> even if the user has it set to "auto" it wont do issue the command?

> maybe everytime a user creates a new playlist, we follow up at the end of the question / answer session with 1 more qustion asking "would you like us to reload your plugins so the new playlist appears?" and use that as the user permission?

None of these can work. `/reload-plugins` is a built-in command of the app's own interface, not a tool, and the harness refuses when Claude tries to invoke it. No hook can trigger it, no permission mode changes that, and a Yes button that does nothing is worse than no button. What shipped instead: the menu ends a create by offering to play the new playlist immediately, which works because the menu reads playlists from disk, and then prints `/reload-plugins` on its own line as a headed call-out for the user to type. The owner reported "reload works fine" at 14:39, and at 14:23 had asked for the call-out to be made less "understated", which is why it is the last thing on screen after a create.

## 7. Hover text

**14:30.** The owner liked the menu overview and asked for the hover text beside each playlist to list every skill in it. The first attempt used one skill per line. The desktop tooltip strips line breaks, so the result, in the owner's words at 14:32, was "still hard to readh, kinda runs together".

The rewrite treats the tooltip as one wrapped paragraph: the purpose first, then the count, then the skills as comma lists grouped under a capitalised family label such as `SWIFTUI:` and `SWIFT:`, with non-breaking hyphens so a skill name never splits across lines, and plugin ids shown once. Asked to "evaluate" the result, Claude proposed collapsing near-duplicates like `concurrency, concurrency-expert, concurrency-pro` to `concurrency (3)`. The owner declined: "every skill stay spelled out."

## 8. Going public

**14:39.** "i would like to create a new repo under my personal account @mvoshell652". Before the first push, every commit was rewritten to the GitHub private no-reply address, because the local git identity carried a typo the owner then fixed globally themselves. The repo went up private at 14:41. A one-line install was written and then rewritten when the owner's own test showed it could not be run twice, because it cloned into a fixed path.

Between 15:01 and 15:55 the repo was made ready for strangers, in the order Claude proposed and the owner approved with "start", "go" and "execite 3 steps":

- An MIT licence, and a README with install, update, uninstall, a section explaining why the tool is not a `/plugin install`, an Options section documenting every mode and command, and a five-step screenshot walkthrough of the menu.
- Repo topics, a manifest with keywords, and a social preview card built from a real screenshot of the slash menu. The owner asked for the version without a command box.
- The visibility flip, preceded by a scan of the whole history for emails, paths and secrets, and followed by an anonymous clone-and-install with no credentials to prove a stranger could use it.
- CI on Linux, macOS and Windows, on Python 3.8 and 3.13. Preparing for Windows exposed a real bug: every file was opened with the platform's default encoding, which would have crashed on the first accented description. All I/O became explicit UTF-8.
- Secret scanning with push protection, private vulnerability reporting with a `SECURITY.md`, a rule protecting `main` from force-pushes and deletion, a contributing guide, issue forms and a pull request template.
- Release v0.6.4, tagged on the commit CI had passed, at 15:58.

## 9. Distribution

The owner's question at 14:45 was whether to use the plugin marketplace. Claude installed the repo through a local marketplace in a sandbox to find out, and four research agents checked the rest. The answer is that a marketplace install breaks the tool twice over: the bare `/playlist` command is not registered, and the files land in a versioned cache that is replaced on every update, which would delete a user's playlists. The skills-directory install is the only channel that meets all four of the owner's requirements, and it is a documented, first-class Claude Code mechanism, so it stayed primary.

Submissions were drafted for four discovery channels and checked by three reviewers against each target's real rules and accepted entries. The result, at the end of the day: one target is eligible only from 2 October and must be submitted by a human under its own rules; one is a ten-minute pull request with poor odds; and two, both directories that generate a marketplace-style install command, are on hold until a small safety net exists that turns a marketplace install into a pointer to the real one. Appendix A has the drafts.

## 10. What the day settled

Everything below was decided by the owner, in most cases by rejecting something Claude had built or proposed.

| Decision | Chosen | Rejected on the way |
|---|---|---|
| The word | `playlist`, singular, always | `playlists`, `/dj:`, `/pl:`, any other prefix |
| How to play one | `/playlist:<name>` in the slash menu, with a "Loading N skills" line and an `N/N loaded` count | `/play <name>`, `@@name` tokens in a message, bare `/swift`-style top-level skills |
| How to manage | One bare `/playlist` command running a guided menu in the native question panel | A web page with drag-and-drop, six separate verb commands, a `playlists:manage` entry |
| Choosing skills | Type them all on one line, or suggest from the folder; one review list | Searching one keyword at a time, a 16-per-screen picker for everything |
| Colon or hyphen | Colon, accepting that a new playlist reaches the dropdown only after `/reload-plugins` | `playlist-<name>` plain skills, which appear instantly |
| After creating | Offer to play it now, then print `/reload-plugins` as a call-out | Auto-running the reload, or a Yes button that could not do anything |
| Hover text | Purpose, count, every skill spelled out, grouped under capitalised labels | Bullets, line breaks, collapsing variants to `concurrency (3)` |
| Distribution | Git clone plus `install.sh`, into the skills directory | Marketplace listing, `npx skills`, hyphenated fallback |
| Safety | No typed text on a shell line; playlist files untrusted; playing runs no command | Quoting the argument, blacklists |

## 11. Timeline

All on 18 September 2026, Pacific time. Commit hashes are from the public repository.

| Time | What happened |
|---|---|
| 11:26 | First message: the complaint |
| 11:30 | "productize this idea so users can create playlists" |
| 11:31–11:55 | Research workflow: mechanics, prior art, distribution; three designs; two judges; one spec |
| 11:55–12:01 | First build, 46 tests |
| 12:01 | `63642cf` first commit |
| 12:05–12:30 | Adversarial review, 33 agents, 27 confirmed findings |
| 12:34 | `4305f6c` shell and prompt injection closed |
| 12:38 | Installed locally at the owner's request |
| 12:41 | "how do I manage the playlists?" |
| 12:42–12:51 | Web UI, native window and prefix ideas rejected; the specification message |
| 12:58 | `0687036` each playlist is a real skill under `/playlist:` |
| 13:01 | "seems commingled" |
| 13:09 | `a0e48f4` six verbs collapsed into one guided menu |
| 13:22 | `78d0bb5` menu hardened after the five-scenario dry run |
| 13:25 | "no s on playlist… the root /playlist" |
| 13:27 | `ed6b40d` the tool is `/playlist` itself, one folder |
| 13:28 | "great job!" |
| 13:33 | Skill picker rejected |
| 13:35 | `7300207` skills gathered in one step |
| 13:39–13:51 | The refresh problem; hyphen built and discarded; "Play it now" shipped |
| 14:23–14:36 | Hover text, three iterations |
| 14:39 | "create a new repo under my personal account" |
| 14:41 | Repo created, private |
| 14:45 | "whats best way to distribute this?" |
| 15:01–15:31 | Licence, README, screenshots, walkthrough |
| 15:36–15:44 | Metadata, social preview, repo public |
| 15:56 | `7ad28ea` CI, security policy, contributing guide |
| 15:58 | Release v0.6.4 |
| 16:06 | Submission drafts |
| 16:19 | LinkedIn post drafted |
| 24 Sep | This document |

## 12. Mechanics verified along the way

These are the facts about Claude Code that the design rests on. Each was checked against the official documentation or reproduced in a sandbox, and several overturned an assumption made earlier the same day.

- A skills-directory plugin, a folder under `~/.claude/skills/` with a `.claude-plugin/plugin.json`, registers its root `SKILL.md` as a bare command under the plugin's name and its `skills/*` as `name:skill`. A marketplace-installed plugin never gets the bare command.
- Edits to an existing skill's `SKILL.md` take effect in the running session. A new skill inside a plugin folder does not, until `/reload-plugins` or a new session. A new plain skill does, after roughly ten seconds.
- `/reload-plugins` is a user-only command. No tool, hook or permission mode lets Claude run it.
- `$0` and `$ARGUMENTS` are substituted into a `` !`command` `` line as raw text before the shell runs. Quoting in the template cannot make this safe. The tool never puts typed text on a shell line.
- A `UserPromptSubmit` hook can add at most 10,000 characters of context and cannot rewrite the prompt.
- The question panel accepts two to four options per question, up to four questions per call, headers of twelve characters or fewer, and always adds its own free-text "Other".
- The slash-menu tooltip shows a skill's description as one wrapped paragraph with line breaks stripped; the specification caps a description at 1,024 characters.
- Native `/a /b` stacking is capped at about six skills, and Anthropic closed the feature request for more.
- A marketplace install copies a plugin into a versioned cache replaced on update. `${CLAUDE_PLUGIN_DATA}` survives updates but is never scanned for skills, and manifest paths cannot leave the plugin root.

## 13. What is still open

- The two awesome-list submissions have not been sent. The larger list is eligible only from 2 October and must be submitted by a human.
- A `setup` safety net for marketplace-style installs has been designed but not built. Until it exists, the two plugin directories are on hold, and they may index the repo unasked, so the manifest description now opens with the install warning.
- Two README screenshots show the owner's folder name and a doubled plugin skill id; the owner chose to publish anyway.
- Team sharing through a repository's `.claude/skills/playlist/` is implemented but untested with a personal and a project copy side by side.
- Playing a playlist has been watched to start loading skills in parallel, but the completed `N/N loaded` line has not been captured in a screenshot.

---

## Appendix A: submission drafts

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

## Appendix B: LinkedIn post

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
