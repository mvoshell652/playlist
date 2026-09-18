---
name: manage
description: Create, edit, delete and view skill playlists through a short guided menu. A playlist is a named set of installed skills that loads from /playlist:<name>. Use when the user wants to make a playlist, add or remove skills from one, rename or delete one, see their playlists, or get playlist suggestions.
argument-hint: "[leave empty for the menu, or say what you want]"
allowed-tools: Bash(sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" *), Bash(sh ${CLAUDE_PLUGIN_ROOT}/bin/playlists *)
---

Manage the user's skill playlists by walking them through a short menu.

The user's input: $ARGUMENTS

## How to run the menu

- Ask every question with the AskUserQuestion tool so the user picks instead of typing. One step per call. If that tool is unavailable, ask the same question in plain text with the same choices.
- AskUserQuestion limits: 2 to 4 options per question, at most 4 questions per call, headers of 12 characters or fewer. The user can always type their own answer under "Other", so never add an "Other" option yourself.
- A question needs at least two real choices. When only one applies, do not ask: take it and say in one line what you did.
- If the user's input already answers a step ("add swiftdata to swift"), skip that step. Ask only for what is still missing.
- If the user names a different playlist or changes their mind part way, treat that as a fresh answer to the step it belongs to and carry on from there.
- Do the work with the bundled CLI, run through the Bash tool:

      sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" <command>

- Before the first question, run `list` so you know which playlists exist. Do not show its output unless the user asks to see their playlists.
- If no playlists exist yet, say so in one line and go straight to **Create**.

## Text the user types (read before building any command)

Text typed under "Other" is never placed on a command line as typed. Reduce it first, by keeping only the allowed characters and dropping every other character:

- **A playlist name:** lowercase it, turn spaces into hyphens, then keep only `a-z`, `0-9` and `-`. "My Swift Stuff!" becomes `my-swift-stuff`. Tell the user the final name. If nothing is left, or the CLI rejects the name (already taken, or invalid), show its message and ask again.
- **A description or an auto-load rule:** keep only letters, digits, spaces, commas, periods and hyphens, at most 80 characters, then put it in single quotes.
- **A skill or a search word:** keep only letters, digits, `.`, `-`, `_` and `:`. Every skill id you pass to the CLI must be copied from the output of `skills`, `show`, `loaded` or `suggest`, never from what the user typed and never invented.

## Step 1: the action

Question "What do you want to do with your playlists?", header "Action":

| Option | Description |
|---|---|
| Create a playlist | Group skills under a new /playlist:<name> |
| Edit a playlist | Add or remove skills, rename it, or change its description |
| Delete a playlist | Remove a playlist. The skills in it stay installed. |
| See my playlists | List them, or look inside one |

## Create

1. **Name.** Question "What should we call your playlist?", header "Name". Offer two or three short names that fit what the user is working on, such as the project or the stack in this conversation. In a fresh session with nothing to go on, offer plain starters such as `my-stack` and `daily`. They type their own under "Other"; reduce it as described above.
2. **Where the skills come from.** Question "Which skills do you want to add?", header "Skills". First run `loaded --session ${CLAUDE_SESSION_ID}` and `suggest`, then offer only the sources that have something:

   | Option | Description | Offer it when |
   |---|---|---|
   | From this conversation | The N skills already loaded here | `loaded` lists any |
   | Search my skills | Find installed skills by a word, such as swift or supabase | always |
   | From my history | Sets of skills you often load together | `suggest` proposes any |

   If "Search my skills" is the only source, skip this question and go to the search. Skill names typed under "Other" are search words.
3. **Pick the skills.**
   - From this conversation: take every skill `loaded` listed. The user can drop some at the Confirm step.
   - Search: ask for the word if they have not given one, run `skills <word> --limit 48`, then see "Picking from a list".
   - History: question "Which set?", header "History", one option per suggestion (label: a short name you propose; description: how many skills and how often they were loaded together). Choosing one takes all of its skills. With a single suggestion, offer it against "Search instead".
4. **Confirm.** Show the chosen skills as numbered text. Question "Create /playlist:<name> with these N skills?", header "Confirm", options "Create it", "Add more skills", "Remove some", "Start over". "Add more skills" returns to step 2 and keeps what is chosen. "Remove some" lets them pick from the chosen skills (see "Picking from a list"), then returns here.
5. Run `new <name> <id> [<id> ...] -d '<description>'`. Write the description yourself: six words or fewer on what the set is for, using only letters, digits and spaces. Add `--project` only if the user asked to share the playlist with their team.
6. Tell the user it is ready as `/playlist:<name>`, and repeat the note the command printed about when it appears in the / menu.

## Edit

1. **Which playlist.** With one playlist, use it and say so. Otherwise question "Which playlist?", header "Playlist", one option per playlist, described as "N skills" plus its description. With more than four, offer the three that fit what the user is working on, or the first three that `list` printed when nothing points to one, and say how many more there are; they type any other name under "Other".
2. **What to change.** Question "What do you want to change in <name>?", header "Change":

   | Option | What to do |
   |---|---|
   | Add skills | Create steps 2 and 3, then `add <name> <id> ...`. "From this conversation" is `add <name> --session ${CLAUDE_SESSION_ID}`. |
   | Remove skills | Run `show <name>`, let them pick from its skills (see "Picking from a list"), then `remove <name> <id> ...`. |
   | Rename it | Ask for the name as in Create step 1, then `rename <name> <new-name>`. |
   | Change description | Offer two short descriptions; they type their own under "Other", reduced as described above. Then `set <name> -d '<text>'`. |

   Typed requests under "Other": "load only what a request needs" is `set <name> --mode pick`; "load every skill" is `set <name> --mode all`; "load it automatically when ..." is `set <name> --auto '<when>'` with the text reduced as described above, and `--no-auto` turns that off.
3. Show what the command printed. After adding or removing, that includes the new skill count, and the change is live in this session. Then ask once, header "Next": "Add skills", "Remove skills", "Done".

## Delete

1. Pick the playlist as in Edit step 1.
2. Question "Delete /playlist:<name>? It has N skills, and they stay installed.", header "Confirm", options "Delete it", "Keep it". Do nothing without "Delete it". Write "1 skill" when N is 1.
3. Run `delete <name>` and show what it printed.

## See my playlists

Run `list` and show the result as a table. If they want to look inside one, run `show <name>`. If a skill shows as not found, run `doctor` and explain what it reports.

## Picking from a list

The same steps serve adding (candidates come from `skills <word>`) and removing (candidates are the playlist's own skills from `show`, or the chosen skills at the Confirm step). Say "add" or "remove" to match.

Use multi-select questions, four skills per question, up to four questions in one call, so one screen shows up to 16 skills. Label each option with the exact skill id and describe it with the first sentence of its description. Number the headers "Pick 1-4", "Pick 5-8", which stays within 12 characters even past 100. When the last question of a screen would hold a single skill, move one skill over from the question before it so both have at least two.

- With more than 16 candidates, first ask, header "How many": "Select all N", "Let me pick", "Filter by a word". "Let me pick" shows 16 per screen; say how many screens remain. "Filter by a word" narrows the current candidates: when adding, run `skills` again with the extra word; when removing, keep only the playlist's own skills that contain the word, and never call `skills`.
- With two to four candidates, ask one question.
- With one candidate, ask a yes or no question instead, header "Confirm": "Add <id> to <name>?" or "Remove <id> from <name>?", options "Yes" and "Cancel". When creating, skip even that, because the Confirm step follows.
- Picking nothing on a screen is fine; move on to the next screen.
- Anything typed under "Other" is another search or filter word.

## After every command

Show the user what the command printed, briefly. If it starts with "Playlist error", nothing was changed: explain it and return to the step that caused it.
