---
name: playlist
description: Create, edit, delete and view skill playlists through a short guided menu. A playlist is a named set of installed skills that loads together from /playlist:<name>. Use when the user wants to make a playlist, add or remove skills from one, rename or delete one, see their playlists, or get playlist suggestions.
argument-hint: "[leave empty for the menu, or say what you want]"
allowed-tools: Bash(sh "${CLAUDE_SKILL_DIR}/bin/playlist" *), Bash(sh ${CLAUDE_SKILL_DIR}/bin/playlist *)
---

Manage the user's skill playlists by walking them through a short menu.

The user's input: $ARGUMENTS

## How to run the menu

- Ask every question with the AskUserQuestion tool so the user picks instead of typing. One step per call. If that tool is unavailable, ask the same question in plain text with the same choices.
- AskUserQuestion limits: 2 to 4 options per question, at most 4 questions per call, headers of 12 characters or fewer. The user can always type their own answer under "Other", so never add an "Other" option yourself.
- A question needs at least two real choices. When only one applies, do not ask: take it and say in one line what you did.
- If the user's input already answers a step ("add swiftdata to swift"), skip that step. Ask only for what is still missing.
- If the input starts with the name of an existing playlist, they want to play it, and the rest of the input is their request. Play it as described under "Playing a playlist from here". Do not start the menu.
- If the user names a different playlist or changes their mind part way, treat that as a fresh answer to the step it belongs to and carry on from there.
- Do the work with the bundled CLI, run through the Bash tool:

      sh "${CLAUDE_SKILL_DIR}/bin/playlist" <command>

- Before the first question, run `list` so you know which playlists exist. Do not show its output unless the user asks to see their playlists.
- If no playlists exist yet, say so in one line and go straight to **Create**.

## Text the user types (read before building any command)

Text typed under "Other" is never placed on a command line as typed. Reduce it first, by keeping only the allowed characters and dropping every other character:

- **A playlist name:** lowercase it, turn spaces into hyphens, then keep only `a-z`, `0-9` and `-`. "My Swift Stuff!" becomes `my-swift-stuff`. Tell the user the final name. If nothing is left, or the CLI rejects the name (already taken, or invalid), show its message and ask again.
- **A description or an auto-load rule:** keep only letters, digits, spaces, commas, periods and hyphens, at most 80 characters, then put it in single quotes.
- **Skill words for `match`:** split what they typed on spaces and commas, and keep only letters, digits, `.`, `-`, `_` and `:` in each word. Every skill id you pass to the CLI must be copied from the output of `match`, `skills`, `show`, `loaded` or `suggest`, never from what the user typed and never invented.

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
2. **Which skills.** Question "Which skills do you want in it? Pick a source, or type skill names or a description under Other.", header "Skills". First run `loaded --session ${CLAUDE_SESSION_ID}` and `suggest`, then offer:

   | Option | Description | Offer it when |
   |---|---|---|
   | Suggest for this project | I read this project's dependencies and propose the skills that fit | always |
   | I'll type them | One line of names or a description, such as: nuxt vue pinia vitest a11y | always |
   | From this conversation | The N skills already loaded here | `loaded` lists any |
   | From my history | Sets of skills you often load together | `suggest` proposes any |

   Anything typed under "Other" is treated exactly like "I'll type them".
3. **Gather the skills.** The user should never search one word at a time. You do the searching and they review one list.
   - **I'll type them:** ask in plain chat, not with a question panel: "Type the skills you want, or describe the stack. Partial names are fine, all on one line." Take their reply through "Turning words into skills" below.
   - **Suggest for this project:** read the dependency and config files that exist in the working directory, such as `package.json`, `nuxt.config.*`, `Package.swift`, `Podfile`, `pyproject.toml`, `requirements.txt`, `go.mod`, `Cargo.toml`, `Gemfile`, `supabase/`, `firebase.json`, `Dockerfile`. Collect the names of the frameworks, libraries and services in use, skip generic utilities, then take those names through "Turning words into skills". Propose at most 12, most central to the project first. If nothing recognisable is found, say so and fall back to "I'll type them".
   - **From this conversation:** take every skill `loaded` listed.
   - **From my history:** question "Which set?", header "History", one option per suggestion (label: a short name you propose; description: how many skills and how often they were loaded together). Choosing one takes all of its skills. With a single suggestion, offer it against "I'll type them".
4. **Review.** Show the chosen skills as numbered text, one per line with a few words on what each is for. Mark with "(my pick)" every skill you chose between several candidates, and name the runner-up so they can swap it. Question "Create /playlist:<name> with these N skills?", header "Confirm", options "Create it", "Add more skills", "Remove some", "Start over". "Add more skills" returns to step 2 and keeps what is chosen. "Remove some" lets them pick from the chosen skills (see "Picking from a list"), then returns here. They can also type a change under "Other", such as "swap shadcn-ui for shadcn-vue" or "drop the testing ones".
5. Run `new <name> <id> [<id> ...] -d '<description>'`. Write the description yourself: six words or fewer on what the set is for, using only letters, digits and spaces. Add `--project` only if the user asked to share the playlist with their team.
6. **What next.** Say in one line that the playlist is created, with its skill count. Then question "/playlist:<name> is ready. What next?", header "Next":

   | Option | Description |
   |---|---|
   | Play it now | Load its N skills into this conversation right away |
   | Done | Close the menu |

7. **The reload call-out.** Once they answer, print the call-out below, exactly as written apart from the name, under a horizontal rule. It must stand out, so:
   - On "Done", the call-out is the whole of your reply and the last thing on screen. Do not follow it with a list or table of playlists, a summary, or any other text.
   - On "Play it now", or a request typed under "Other", print the call-out first, then play the playlist as described under "Playing a playlist from here".

   ```markdown
   ---

   ### One step left: add it to your / menu

   Type this in the message box:

       /reload-plugins

   `/playlist:<name>` then appears whenever you type `/playlist`. Skip it and it shows up in your next session instead. Only you can run this command. I can't type it for you.
   ```

## Edit

1. **Which playlist.** With one playlist, use it and say so. Otherwise question "Which playlist?", header "Playlist", one option per playlist, described as "N skills" plus its description. With more than four, offer the three that fit what the user is working on, or the first three that `list` printed when nothing points to one, and say how many more there are; they type any other name under "Other".
2. **What to change.** Question "What do you want to change in <name>?", header "Change":

   | Option | What to do |
   |---|---|
   | Add skills | Create steps 2 and 3, show what you gathered as in the Review step, then `add <name> <id> ...`. "From this conversation" is `add <name> --session ${CLAUDE_SESSION_ID}`. |
   | Remove skills | Run `show <name>`, let them pick from its skills (see "Picking from a list"), then `remove <name> <id> ...`. |
   | Rename it | Ask for the name as in Create step 1, then `rename <name> <new-name>`. End with the reload call-out from Create step 7, because the renamed playlist also needs `/reload-plugins` to reach the slash menu. |
   | Change description | Offer two short descriptions; they type their own under "Other", reduced as described above. Then `set <name> -d '<text>'`. |

   Typed requests under "Other": "share it with my team" is `share <name>`, which copies it into this repo to be committed; "load only what a request needs" is `set <name> --mode pick`; "load every skill" is `set <name> --mode all`; "load it automatically when ..." is `set <name> --auto '<when>'` with the text reduced as described above, and `--no-auto` turns that off.
3. Show what the command printed. After adding or removing, that includes the new skill count, and the change is live in this session. Then ask once, header "Next": "Add skills", "Remove skills", "Done".

## Delete

1. Pick the playlist as in Edit step 1.
2. Question "Delete /playlist:<name>? It has N skills, and they stay installed.", header "Confirm", options "Delete it", "Keep it". Do nothing without "Delete it". Write "1 skill" when N is 1.
3. Run `delete <name>` and show what it printed.

## See my playlists

Run `list` and show the result as a table. If they want to look inside one, run `show <name>`. If they ask to check their playlists, or a skill shows as not found, run `doctor` and explain what it reports.

## Playing a playlist from here

A playlist created in this session is not in the slash menu until the user reloads plugins, but it can always be played from this menu. Run `show <name>`, which prints the playlist's folder. Read the `SKILL.md` in that folder and follow it exactly, including its "Loading N skills" line and its loaded count, using the user's request if they gave one. With no request, stop after the loaded count.

## Turning words into skills

Resolve everything in one call, however many words there are:

    sh "${CLAUDE_SKILL_DIR}/bin/playlist" match <word> [<word> ...]

- From a description ("everything for a Nuxt app with Pinia and testing"), pull out the technology words yourself first: `nuxt pinia vitest`.
- `match` prints the best installed skills for each word. For each word:
  - "exact id": take that skill. Take a second row too only when it is clearly the version the user is on, such as `nuxt-v4:nuxt-core` for a Nuxt 4 project.
  - Several candidates: choose the one that fits what the user is building, using the other words and the project as context. For a Nuxt app, "shadcn" means `shadcn-vue`, not the React `shadcn-ui`, and "server" means the Nuxt server skill. Mark it "(my pick)" in the Review step.
  - A genuine toss-up, where context does not decide: ask. Put every toss-up in one call, one question per word, header the word itself, options its top candidates.
  - "no match": try one obvious synonym (`a11y` and `accessibility`, `db` and `database`). If that fails too, tell the user in the Review step which words found nothing.
- Never add a skill whose id `match` did not print.

## Picking from a list

Only for choosing among skills that are already on the table: removing skills from a playlist, "Remove some" at the Review step, and toss-ups. Never use it to browse the whole library.

Use multi-select questions, four skills per question, up to four questions in one call, so one screen shows up to 16 skills. Label each option with the exact skill id and describe it with the first sentence of its description. Number the headers "Pick 1-4", "Pick 5-8", which stays within 12 characters even past 100. When the last question of a screen would hold a single skill, move one skill over from the question before it so both have at least two.

- With more than 16 candidates, first ask, header "How many": "Select all N", "Let me pick", "Filter by a word". "Let me pick" shows 16 per screen; say how many screens remain. "Filter by a word" keeps only the candidates that contain the word.
- With two to four candidates, ask one question.
- With one candidate, ask a yes or no question instead, header "Confirm": "Remove <id> from <name>?", options "Yes" and "Cancel".
- Picking nothing on a screen is fine; move on to the next screen.

## After every command

Show the user what the command printed, briefly. If it starts with "Playlist error", nothing was changed: explain it and return to the step that caused it.
