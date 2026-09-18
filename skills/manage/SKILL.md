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
- If the user's input already answers a step ("add swiftdata to swift"), skip that step. Ask only for what is still missing.
- Do the work with the bundled CLI, run through the Bash tool:

      sh "${CLAUDE_PLUGIN_ROOT}/bin/playlists" <command>

- Before the first question, run `list` so you know which playlists exist. Do not show its output unless the user asks to see their playlists.
- If no playlists exist yet, say so in one line and go straight to **Create**.

## Step 1: the action

Question "What do you want to do with your playlists?", header "Action":

| Option | Description |
|---|---|
| Create a playlist | Group skills under a new /playlist:<name> |
| Edit a playlist | Add or remove skills, rename it, or change its description |
| Delete a playlist | Remove a playlist. The skills in it stay installed. |
| See my playlists | List them, or look inside one |

## Create

1. **Name.** Question "What should we call your playlist?", header "Name". Offer two or three short names that fit what the user is working on, such as the project or the stack in this conversation. They type their own under "Other". Names are lowercase letters, digits and hyphens: tidy what they type (lowercase, spaces to hyphens) and tell them the final name. If that name already exists, say so and ask again.
2. **Where the skills come from.** Question "Which skills do you want to add?", header "Skills":

   | Option | Description |
   |---|---|
   | From this conversation | The skills already loaded here. Offer this only if `loaded --session ${CLAUDE_SESSION_ID}` finds any, and put the count in the description. |
   | Search my skills | Find installed skills by a word, such as swift or supabase |
   | From my history | Sets of skills you often load together |

   Under "Other" they can type skill names directly; resolve each with `skills <word>`.
3. **Pick the skills.** See "Picking from a list" below.
   - Search: ask for the word if they have not given one, then run `skills <word> --limit 48`.
   - History: run `suggest`. Offer each suggestion as one option (label: a short name you propose; description: how many skills and how often). Choosing one selects all of its skills.
4. **Confirm.** Show the final list as numbered text. Question "Create /playlist:<name> with these N skills?", header "Confirm", options "Create it", "Add more skills", "Start over". On "Add more skills" go back to step 2 and keep what is already chosen.
5. Run `new <name> <id> [<id> ...] -d '<description>'`. Write the description yourself: six words or fewer on what the set is for. Put it in single quotes and drop any single quote it contains. Add `--project` only if the user asked to share the playlist with their team.
6. Tell the user it is ready as `/playlist:<name>`, and repeat the note the command printed about when it appears in the / menu.

## Edit

1. **Which playlist.** Question "Which playlist?", header "Playlist". One option per playlist, with "N skills" and its description. With more than four playlists, offer the three that best fit what the user is working on; they type any other name under "Other".
2. **What to change.** Question "What do you want to change in <name>?", header "Change":

   | Option | What to do |
   |---|---|
   | Add skills | Create steps 2 and 3, then `add <name> <id> ...`. "From this conversation" is `add <name> --session ${CLAUDE_SESSION_ID}`. |
   | Remove skills | Run `show <name>`, let them pick from its skills (see "Picking from a list"), then `remove <name> <id> ...`. |
   | Rename it | Ask for the name as in Create step 1, then `rename <name> <new-name>`. |
   | Change description | Offer two short descriptions; they type their own under "Other". Then `set <name> -d '<text>'`. |

   Typed requests under "Other": "load only what a request needs" is `set <name> --mode pick`; "load every skill" is `set <name> --mode all`; "load it automatically when ..." is `set <name> --auto '<when>'`, and `--no-auto` turns that off.
3. Report the new skill count from the command's output. Adding and removing skills takes effect in this session. Then ask once, header "Next": "Add skills", "Remove skills", "Done".

## Delete

1. Pick the playlist as in Edit step 1.
2. Question "Delete /playlist:<name> (N skills)? The skills stay installed.", header "Confirm", options "Delete it", "Keep it". Do nothing without "Delete it".
3. Run `delete <name>` and show what it printed.

## See my playlists

Run `list` and show the result as a table. If they want to look inside one, run `show <name>`. If a skill shows as not found, run `doctor` and explain what it reports.

## Picking from a list

Use multi-select questions, four skills per question, up to four questions in one call, so one screen shows up to 16 skills. Label each option with the exact skill id and describe it with the first sentence of its description. Number the headers "Pick 1-4", "Pick 5-8", which stays within 12 characters even past 100.

- With more than 16, first ask, header "How many": "Add all N", "Let me pick", "Narrow the search". On "Let me pick", show 16 per screen and say how many screens remain.
- With four or fewer, ask one question.
- When there is only one candidate, do not ask; confirm it in the Confirm step instead.
- Anything typed under "Other" counts as more skill names or as a new search word.

## Rules for every command line

- Build commands only from playlist names (lowercase letters, digits, `-`, `_`) and exact skill ids (letters, digits, `.`, `-`, `_`, with an optional `plugin:` prefix such as `supabase:supabase`). Never paste other text the user typed into a shell command. If it contains quotes, `$`, backticks or `;`, leave it out and ask for a plain name.
- Never invent a skill id. Every id must come from the output of `skills`, `show`, `loaded` or `suggest`.
- Show the user what each command printed, briefly.
