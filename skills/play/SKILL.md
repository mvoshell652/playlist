---
name: play
description: Load a saved skill playlist, which is a named set of Claude Code skills, in one go. Use when the user says "play <name>", "load my <name> playlist" or "load my <name> skills", or names a skill playlist to apply to their request. Not for playing music, video or any other media.
argument-hint: "<playlist>[+<playlist>][:inline|:index] [your request]"
allowed-tools: Bash(sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" *), Bash(sh ${CLAUDE_PLUGIN_ROOT}/bin/playlists *)
---

!`sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" catalog`

The user's message: $ARGUMENTS

Play the playlist the user named:

1. The first word of their message is the playlist reference: one name, or several joined with `+` (people also write `swift, db` or `swift and db`). A `:inline` or `:index` suffix picks a load mode. The rest of the message is their request.
2. Match each name against the catalog above, exactly. If a name is not there, tell the user, list the playlists that exist, and stop. Never guess at skills.
3. For `invoke` mode, which is the default, load every skill of the named playlists now. Merge several playlists into one list without duplicates. Call the Skill tool once per skill, all in a single message so they load in parallel. Skip a skill only if it was already loaded earlier in this conversation. Do not substitute, summarise or drop any. When the calls return, start your reply with one line, `▶ <playlist>: <loaded>/<total> loaded`. Count a skill as loaded only if its Skill call returned the skill's content, and name every skill whose call failed. Then carry out the user's request with all of them applied.
4. For a playlist whose mode is `inline` or `index`, or when the user added that suffix, run this with the Bash tool and follow what it prints:

       sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" play <name>[:inline|:index]

   Put only names copied from the catalog on that command line. Never paste text the user typed into a shell command.
5. If the catalog above is missing, because the line shows a literal command or says shell execution is disabled, run `sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" catalog` with the Bash tool first, then continue from step 1.
