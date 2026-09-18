#!/usr/bin/env python3
"""Skill playlists for Claude Code: a named list of skills that one reference loads.

A playlist is a small JSON file. `catalog` and `play` print the text that reaches
the model; everything else manages the files. Standard library only, so the
plugin has no install step.

Two rules shape the design:

* Playlists are data read at play time, never generated skills. A running session
  does not see skill files created after it started, but it always sees a JSON
  file written a second ago.
* Nothing a user types is ever placed on a shell command line, and nothing read
  from a playlist file reaches the model unless it matches a strict pattern.
  Project playlists are committed and shared, so their contents are untrusted.
"""
import argparse
import collections
import glob
import itertools
import json
import os
import re
import sys

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,47}$")
SKILL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}(?::[A-Za-z0-9][A-Za-z0-9._-]{0,63})?$")
TOKEN_RE = re.compile(r"(?<![\w@])@@([a-z0-9][a-z0-9_-]{0,47})(?::(invoke|inline|index))?(?![\w-])")
CODE_RE = re.compile(r"```.*?(?:```|\Z)|`[^`\n]*`", re.S)
CMD_RE = re.compile(r"<command-name>/?([^<\s]+)</command-name>")
MODES = ("invoke", "inline", "index")
# Bash tool output is shown inline up to 30,000 characters; stay well under it, wrappers included.
INLINE_BUDGET = 24000
CATALOG_BUDGET = 20000
# A hook may add at most 10,000 characters of context.
HOOK_BUDGET = 9500
# Skills the harness loads for its own purposes; nobody picks these, so they are noise in a mined playlist.
HARNESS_SKILLS = {"artifact-design", "artifact-capabilities", "artifact-diagramming", "workflow-authoring"}


class PlaylistError(Exception):
    pass


# ---------------------------------------------------------------- locations

def config_dir():
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")


def global_dir():
    return os.environ.get("PLAYLISTS_HOME") or os.path.join(config_dir(), "playlists")


def project_root(start=None):
    """Nearest ancestor holding .claude or .git; None when there is none (or it is the home dir)."""
    cur = os.path.abspath(start or os.getcwd())
    home = os.path.expanduser("~")
    while True:
        if cur != home and any(os.path.exists(os.path.join(cur, m)) for m in (".claude", ".git")):
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        cur = parent


def project_dir(cwd=None):
    root = project_root(cwd)
    return os.path.join(root, ".claude", "playlists") if root else None


# ---------------------------------------------------------------- playlists

def check_name(name):
    if not NAME_RE.match(name or ""):
        raise PlaylistError(f"'{one_line(name, 60)}' is not a valid playlist name. "
                            f"Use lowercase letters, digits, - or _ (max 48).")
    return name


def check_skills(skills):
    bad = [s for s in skills if not SKILL_RE.match(s)]
    if bad:
        raise PlaylistError(f"Not a skill id: {', '.join(repr(one_line(s, 60)) for s in bad)}. "
                            f"Ids look like swiftui-pro or supabase:supabase. Run `skills <word>` to find one.")
    return list(dict.fromkeys(skills))


def one_line(text, limit=120):
    text = "".join(ch if ch.isprintable() else " " for ch in str(text or ""))
    return re.sub(r"\s+", " ", text).strip()[:limit]


def load_file(path):
    """A playlist's name is its filename. Anything in the file that fails validation is dropped, not passed on."""
    name = check_name(os.path.basename(path)[:-5])
    try:
        with open(path) as fh:
            data = json.load(fh)
    except (OSError, ValueError) as e:
        raise PlaylistError(f"Could not read {path}: {e}")
    raw = data.get("skills", []) if isinstance(data, dict) else None
    if not isinstance(raw, list):
        raise PlaylistError(f"{path} is not a playlist: expected an object with a \"skills\" list.")
    valid = [s for s in raw if isinstance(s, str) and SKILL_RE.match(s)]
    return {"name": name, "description": one_line(data.get("description")),
            "mode": data.get("mode") if data.get("mode") in MODES else "invoke",
            "skills": list(dict.fromkeys(valid)), "rejected": len(raw) - len(valid), "path": path}


def all_playlists(cwd=None, problems=None):
    """name -> playlist. A project playlist shadows a personal one with the same filename."""
    found = {}
    for scope, d in (("personal", global_dir()), ("project", project_dir(cwd))):
        if not d or not os.path.isdir(d):
            continue
        for path in sorted(glob.glob(os.path.join(d, "*.json"))):
            try:
                pl = load_file(path)
            except PlaylistError as e:
                if problems is not None:
                    problems.append(str(e))
                continue
            pl["scope"] = scope
            found[pl["name"]] = pl
    return found


def get_playlist(name, cwd=None):
    lists = all_playlists(cwd)
    if name not in lists:
        hint = " That looks like a skill id; this command takes a playlist name." if ":" in name else ""
        raise PlaylistError(f"No playlist named '{one_line(name, 60)}'.{hint} "
                            f"Playlists: {', '.join(sorted(lists)) or 'none yet'}.")
    return lists[name]


def write_playlist(name, skills, description="", mode="invoke", project=False, cwd=None, path=None):
    """Writes to `path` when editing an existing playlist, so an edit never changes its scope or location."""
    check_name(name)
    skills = check_skills(skills)
    if path is None:
        d = project_dir(cwd) if project else global_dir()
        if not d:
            raise PlaylistError("Not inside a project (no .git or .claude found), so there is nowhere to save a project playlist.")
        path = os.path.join(d, name + ".json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    body = {"name": name, "description": one_line(description), "mode": mode, "skills": skills}
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(body, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, path)
    return path


# ---------------------------------------------------------------- installed skills

def read_description(path):
    """Description from SKILL.md frontmatter; handles plain, quoted and folded (> or |) values."""
    try:
        with open(path, errors="ignore") as fh:
            head = fh.read(6000).replace("\r\n", "\n")
    except OSError:
        return ""
    if not head.startswith("---"):
        return ""
    lines = head.split("\n")[1:]
    for i, line in enumerate(lines):
        if line.strip() == "---":
            break
        if line.startswith("description:"):
            value = line[len("description:"):].strip()
            if value in (">", "|", ">-", "|-", ""):
                block = itertools.takewhile(lambda l: l.startswith((" ", "\t")) or not l.strip(), lines[i + 1:])
                value = " ".join(l.strip() for l in block if l.strip())
            return one_line(value.strip("\"'"), 300)
    return ""


def readable_skill_file(path, inside=None):
    """Inline mode pastes file contents into context, so only ever read real markdown files.

    A repo can plant `.claude/skills/x/SKILL.md` as a symlink to a private file, so project
    skills must resolve inside the project. Personal skill folders are the user's own and
    are often symlinked by skill managers, so those only need to be markdown.
    """
    real = os.path.realpath(path)
    if not real.lower().endswith(".md") or not os.path.isfile(real):
        return False
    if inside:
        root = os.path.realpath(inside)
        return os.path.commonpath([root, real]) == root
    return True


def skill_index(cwd=None):
    """Skill id -> SKILL.md path, for every skill found on disk.

    Skills bundled with Claude Code or synced from claude.ai are not on disk, so a
    miss here means "cannot verify", not "does not exist".
    """
    index = {}

    def add(key, path, inside=None):
        if SKILL_RE.match(key) and key not in index and readable_skill_file(path, inside):
            index[key] = path

    def add_dir(skills_dir, prefix="", inside=None):
        for path in glob.glob(os.path.join(skills_dir, "*", "SKILL.md")):
            add(prefix + os.path.basename(os.path.dirname(path)), path, inside)

    root = project_root(cwd)
    if root:
        add_dir(os.path.join(root, ".claude", "skills"), inside=root)
    add_dir(os.path.join(config_dir(), "skills"))
    for base, inside in ((root and os.path.join(root, ".claude", "commands"), root),
                         (os.path.join(config_dir(), "commands"), None)):
        for path in glob.glob(os.path.join(base, "*.md")) if base else []:
            add(os.path.basename(path)[:-3], path, inside)
    try:
        with open(os.path.join(config_dir(), "plugins", "installed_plugins.json")) as fh:
            plugins = json.load(fh).get("plugins", {})
    except (OSError, ValueError, AttributeError):
        plugins = {}
    for key, installs in plugins.items() if isinstance(plugins, dict) else []:
        for inst in installs if isinstance(installs, list) else []:
            if isinstance(inst, dict) and inst.get("installPath"):
                add_dir(os.path.join(inst["installPath"], "skills"), prefix=key.split("@")[0] + ":")
    return index


def not_on_disk(skills, cwd=None):
    index = skill_index(cwd)
    missing = [s for s in skills if s not in index]
    if not missing:
        return ""
    return (f"\nNot found on disk: {', '.join(missing)}. Built-in and claude.ai-synced skills always show here; "
            f"for anything else check the spelling with `skills <word>`.")


def strip_frontmatter(text):
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:].lstrip("\n")
    return text


# ---------------------------------------------------------------- play

def parse_refs(arg):
    """'swift+db:index', 'swift, db' -> [('swift', None), ('db', 'index')]. Duplicates collapse."""
    refs = {}
    for part in re.split(r"[+,\s]+", arg or ""):
        if not part:
            continue
        name, _, mode = part.partition(":")
        if mode and mode not in MODES:
            raise PlaylistError(f"'{one_line(part, 60)}' is not a playlist reference. Write a playlist name, optionally "
                                f"followed by :inline or :index. Skill ids such as supabase:supabase go inside a playlist.")
        refs.setdefault(name, mode or None)
    return list(refs.items())


def numbered(skills):
    return "\n".join(f"{i}. {s}" for i, s in enumerate(skills, 1))


INVOKE_RULES = (
    "Call the Skill tool once per skill, all in a single message so they load in parallel. Skip a skill only if it "
    "was already loaded earlier in this conversation. Do not substitute, summarise or drop any. When the calls "
    "return, start your reply with one line, `▶ {label}: <loaded>/{total} loaded`. Count a skill as loaded only if its "
    "Skill call returned the skill's content, and name every skill whose call failed. Then carry out the user's "
    "request with all of them applied."
)


def render_invoke(label, skills):
    return f"Load every skill below now. {INVOKE_RULES.format(label=label, total=len(skills))}\n\n{numbered(skills)}"


def render_index(label, skills, index):
    rows = [f"- {s}: {read_description(index[s]) or '(no description)'}\n  {index[s]}" for s in skills if s in index]
    unknown = [s for s in skills if s not in index]
    out = (f"These {len(rows)} skills are available for this request. Read the SKILL.md of each one the request "
           f"actually touches before you start; you do not need all of them.\n\n" + "\n".join(rows))
    if unknown:
        out += "\n\nNot found on disk, so load these with the Skill tool if they are relevant:\n" + numbered(unknown)
    return out + f"\n\nStart your reply with one line: `▶ {label}: read <n> of {len(skills)}`."


def render_inline(label, skills, index):
    parts, deferred, used = [], [], 0
    for s in skills:
        piece = None
        if s in index:
            try:
                with open(index[s], errors="ignore") as fh:
                    body = strip_frontmatter(fh.read()).rstrip()
                piece = f"<skill name=\"{s}\" base-directory=\"{os.path.dirname(index[s])}\">\n{body}\n</skill>"
            except OSError:
                piece = None
        if piece is None or used + len(piece) > INLINE_BUDGET:
            deferred.append(s)
            continue
        used += len(piece) + 2
        parts.append(piece)
    out = (f"{len(parts)} of {len(skills)} skills are included in full below. Treat each as loaded; relative paths "
           f"inside a skill resolve against its base-directory.\n\n" + "\n\n".join(parts))
    if deferred:
        out += (f"\n\nThese {len(deferred)} did not fit the inline budget or are not on disk. Load them with the "
                f"Skill tool, all in one message:\n" + numbered(deferred))
    return out + f"\n\nStart your reply with one line: `▶ {label}: {len(skills)} skills applied`."


def render_play(refs, cwd=None):
    """Text for the model. Several playlists merge into one de-duplicated list; the first explicit mode wins."""
    refs = list(dict(refs).items()) if refs else []
    if not refs:
        raise PlaylistError("Name a playlist, for example `/playlists:play swift`.")
    lists = [get_playlist(name, cwd) for name, _ in refs]
    mode = next((m for _, m in refs if m), None) or (lists[0]["mode"] if len(lists) == 1 else "invoke")
    skills = list(dict.fromkeys(s for pl in lists for s in pl["skills"]))
    label = "+".join(pl["name"] for pl in lists)
    if not skills:
        raise PlaylistError(f"Playlist '{label}' has no valid skills. Add some with `add {lists[0]['name']} <skill>`.")
    header = f"Skill playlist \"{label}\": {len(skills)} skills, {mode} mode.\n\n"
    if mode == "invoke":
        return header + render_invoke(label, skills)
    return header + (render_index if mode == "index" else render_inline)(label, skills, skill_index(cwd))


def render_catalog(cwd=None):
    """Every playlist with its skills, for the play skill. Takes no input, so nothing typed reaches a shell."""
    lists = all_playlists(cwd)
    if not lists:
        return "There are no skill playlists yet. Offer to create one with the playlists:manage skill."
    blocks = [f"## {n} ({p['scope']}, {p['mode']} mode, {len(p['skills'])} skills)\n{numbered(p['skills'])}"
              for n, p in sorted(lists.items())]
    text = "Skill playlists available here:\n\n" + "\n\n".join(blocks)
    if len(text) > CATALOG_BUDGET:
        rows = "\n".join(f"- {n} ({p['scope']}, {p['mode']} mode, {len(p['skills'])} skills)" for n, p in sorted(lists.items()))
        text = ("Skill playlists available here. There are too many to list in full, so run `play <name>` with the "
                "Bash tool to get a playlist's skills:\n\n" + rows)
    return text


# ---------------------------------------------------------------- transcripts

def transcript_turns(path, known=None):
    """Yield (cwd, [skills]) per user turn that loaded at least one skill, in order of first use.

    A turn runs from the user's message to their next one. Stacked `/a /b` commands arrive as
    several user lines with no assistant output between them, and skill bodies arrive as
    isMeta user lines, so a user line opens a new turn only after the assistant has replied.
    """
    cur, cwd, replied = [], None, False
    with open(path, errors="ignore") as fh:
        for line in fh:
            if '"user"' not in line and '"assistant"' not in line:  # cheap skip before parsing; spacing-agnostic
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("isSidechain"):
                continue
            cwd = d.get("cwd") or cwd
            content = (d.get("message") or {}).get("content")
            if d.get("type") == "user":
                is_result = isinstance(content, list) and any(
                    isinstance(x, dict) and x.get("type") == "tool_result" for x in content)
                if not is_result and not d.get("isMeta") and replied:
                    if cur:
                        yield cwd, cur
                    cur, replied = [], False
                text = content if isinstance(content, str) else " ".join(
                    x.get("text", "") for x in content if isinstance(x, dict) and x.get("type") == "text"
                ) if isinstance(content, list) else ""
                # A typed /command counts only when it names an installed skill; /model, /clear and friends do not.
                cur.extend(n for n in CMD_RE.findall(text) if known is None or n in known)
            elif d.get("type") == "assistant":
                replied = True
                for x in content if isinstance(content, list) else []:
                    if isinstance(x, dict) and x.get("type") == "tool_use" and x.get("name") == "Skill":
                        name = (x.get("input") or {}).get("skill")
                        if isinstance(name, str) and SKILL_RE.match(name):
                            cur.append(name)
    if cur:
        yield cwd, cur


def canonical(skill):
    """`x:x` is the plugin copy of personal skill `x`; mining treats them as one skill."""
    head, _, tail = skill.partition(":")
    return head if tail and head == tail else skill


def clean(skills):
    """Drop harness-loaded skills and our own; keep exact ids in first-use order."""
    out = []
    for s in skills:
        if canonical(s) not in HARNESS_SKILLS and not s.startswith("playlists:") and s not in out:
            out.append(s)
    return out


def session_skills(session_id, last=None, cwd=None):
    if not re.match(r"^[A-Za-z0-9_-]{1,80}$", session_id or ""):
        raise PlaylistError("That is not a session id.")
    paths = glob.glob(os.path.join(config_dir(), "projects", "*", session_id + ".jsonl"))
    if not paths:
        raise PlaylistError(f"No transcript found for session {session_id}.")
    turns = [t for t in (clean(t) for _, t in transcript_turns(paths[0], set(skill_index(cwd)))) if t]
    return clean(itertools.chain.from_iterable(turns[-last:] if last else turns))


def jaccard(a, b):
    return len(a & b) / len(a | b)


def suggest(min_support=3, min_size=2, threshold=0.8, core_share=0.7, cwd=None):
    """Cluster near-identical multi-skill turns; each cluster's stable core is one suggestion."""
    known = set(skill_index(cwd))
    observed, spelled = [], collections.Counter()
    for path in glob.glob(os.path.join(config_dir(), "projects", "*", "*.jsonl")):
        try:
            for c, t in transcript_turns(path, known):
                spelled.update(clean(t))
                observed.append((c, frozenset(canonical(x) for x in clean(t)), path))
        except OSError:
            continue
    multi = [o for o in observed if len(o[1]) >= min_size]
    clusters = []
    for s in sorted({m[1] for m in multi}, key=len, reverse=True):
        # Sets whose sizes differ by more than the threshold cannot match, which skips most comparisons.
        home = next((c for c in clusters if len(s) >= threshold * len(c[0]) and jaccard(s, c[0]) >= threshold), None)
        if home:
            home.append(s)
        else:
            clusters.append([s])
    existing = [frozenset(canonical(s) for s in p["skills"]) for p in all_playlists(cwd).values() if p["skills"]]
    dismissed = set(load_state().get("dismissed", []))

    def exact(skill):
        """The id this user actually types most often for a canonical skill, so the playlist loads as-is."""
        forms = [(n, f) for f, n in spelled.items() if canonical(f) == skill]
        return max(forms)[1] if forms else skill

    out = []
    for members in clusters:
        member_set = set(members)
        uses = [o for o in multi if o[1] in member_set]
        if len(uses) < min_support:
            continue
        counts = collections.Counter(s for _, skills, _ in uses for s in skills)
        core = sorted(s for s, n in counts.items() if n / len(uses) >= core_share)
        key = "|".join(core)
        if len(core) < min_size or key in dismissed or any(jaccard(frozenset(core), e) >= threshold for e in existing):
            continue
        cwds = collections.Counter(c for c, _, _ in uses if c)
        top = cwds.most_common(1)[0] if cwds else (None, 0)
        single_project = len(cwds) == 1 and top[1] == len(uses)
        out.append({"skills": [exact(s) for s in core],
                    "sometimes": sorted(exact(s) for s, n in counts.items() if s not in core and n >= 2),
                    "turns": len(uses), "sessions": len({p for _, _, p in uses}),
                    "project": top[0] if single_project else None, "key": key})
    out.sort(key=lambda s: s["turns"] * len(s["skills"]), reverse=True)
    return {"turns_scanned": len(observed), "multi_skill_turns": len(multi), "suggestions": out}


def load_state():
    try:
        with open(os.path.join(global_dir(), ".state.json")) as fh:
            state = json.load(fh)
        return state if isinstance(state, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(state):
    os.makedirs(global_dir(), exist_ok=True)
    with open(os.path.join(global_dir(), ".state.json"), "w") as fh:
        json.dump(state, fh, indent=2)


# ---------------------------------------------------------------- hook

def run_hook():
    """UserPromptSubmit: expand @@name tokens. Must never block a prompt, so every failure exits 0 silently."""
    try:
        event = json.load(sys.stdin)
        prompt, cwd = event.get("prompt") or "", event.get("cwd")
        if "@@" not in prompt:
            return
        lists = all_playlists(cwd)
        # Pasted code is full of @@ (Ruby class variables, diff hunks), so tokens inside code spans never count.
        refs = dict((n, m or None) for n, m in TOKEN_RE.findall(CODE_RE.sub(" ", prompt)) if n in lists)
        if not refs:
            return
        lead = ("The user's message names a skill playlist with an @@name token. If that token is plainly part of "
                "pasted code or data and not a request to load skills, ignore this note. ")
        note = lead + render_play(list(refs.items()), cwd)
        if len(note) > HOOK_BUDGET:
            note = lead + render_play([(n, "invoke") for n in refs], cwd)
        if len(note) > HOOK_BUDGET:
            names = " ".join(refs)
            note = lead + (f"Playlist \"{names}\" is too large to list here. Use the playlists:play skill with "
                           f"\"{names}\" to load it.")
        json.dump({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": note}}, sys.stdout)
    except Exception:
        return


# ---------------------------------------------------------------- cli

def cmd_play(a):
    print(render_play(parse_refs(" ".join(a.ref))))


def cmd_catalog(a):
    print(render_catalog())


def cmd_list(a):
    problems = []
    lists = all_playlists(problems=problems)
    if not lists:
        print("No playlists yet. Create one with `new <name> <skill> [<skill> ...]`, or capture this conversation "
              "with `save-session`. `skills <word>` finds skill ids.")
    else:
        width = max(len(n) for n in lists)
        print("\n".join(
            f"{n.ljust(width)}  {len(p['skills']):>3} skills  {p['scope']:<8}  {p['mode']:<6}  {p['description']}".rstrip()
            for n, p in sorted(lists.items())))
    for p in problems:
        print(f"Skipped: {p}")


def cmd_show(a):
    pl = get_playlist(a.name)
    index = skill_index()
    print(f"{pl['name']} ({pl['scope']}, {pl['mode']} mode) {pl['description']}\n{pl['path']}\n")
    for s in pl["skills"]:
        print(f"  {'ok        ' if s in index else 'not found '} {s}")
    if pl["rejected"]:
        print(f"\n{pl['rejected']} entries in the file are not valid skill ids and are ignored.")
    print(not_on_disk(pl["skills"]).strip())


def cmd_skills(a):
    index = skill_index()
    words = [w.lower() for w in a.query]
    rows = [(k, read_description(v)) for k, v in sorted(index.items())]
    rows = [(k, d) for k, d in rows if all(w in k.lower() or w in d.lower() for w in words)]
    print(f"{len(rows)} of {len(index)} installed skills" + (f" match '{' '.join(a.query)}'" if words else "") + ":\n")
    for k, d in rows[:a.limit]:
        print(f"{k}  {d[:110]}")
    if len(rows) > a.limit:
        print(f"\n... {len(rows) - a.limit} more. Narrow it with a word, for example `skills swift`.")


def cmd_new(a):
    if a.name in all_playlists() and not a.force:
        raise PlaylistError(f"Playlist '{a.name}' already exists. Pass --force to replace it, or use `add`.")
    path = write_playlist(a.name, a.skills, a.description or "", a.mode, a.project)
    print(f"Saved '{a.name}' with {len(set(a.skills))} skills to {path}\n"
          f"Play it with /playlists:play {a.name}, or write @@{a.name} anywhere in a message." + not_on_disk(a.skills))


def cmd_edit(a):
    pl = get_playlist(a.name)
    skills = [s for s in pl["skills"] if s not in a.skills] if a.command == "remove" else pl["skills"] + a.skills
    write_playlist(pl["name"], skills, pl["description"], pl["mode"], path=pl["path"])
    print(f"'{pl['name']}' now has {len(set(skills))} skills." + (not_on_disk(a.skills) if a.command == "add" else ""))


def cmd_set(a):
    pl = get_playlist(a.name)
    write_playlist(pl["name"], pl["skills"], a.description if a.description is not None else pl["description"],
                   a.mode or pl["mode"], path=pl["path"])
    print(f"Updated '{pl['name']}'.")


def cmd_rename(a):
    pl = get_playlist(a.name)
    check_name(a.new_name)
    if a.new_name in all_playlists():
        raise PlaylistError(f"Playlist '{a.new_name}' already exists.")
    write_playlist(a.new_name, pl["skills"], pl["description"], pl["mode"],
                   path=os.path.join(os.path.dirname(pl["path"]), a.new_name + ".json"))
    os.remove(pl["path"])
    print(f"Renamed '{pl['name']}' to '{a.new_name}'.")


def cmd_delete(a):
    pl = get_playlist(a.name)
    os.remove(pl["path"])
    print(f"Deleted '{pl['name']}' ({pl['path']}).")


def cmd_save_session(a):
    a.skills = session_skills(a.session, a.last)
    if not a.skills:
        raise PlaylistError("No skills were loaded in this session yet, so there is nothing to save.")
    cmd_new(a)


def cmd_suggest(a):
    state = load_state()
    if a.dismiss:
        # Numbers refer to the list the user last saw, not a fresh one whose order may have shifted.
        shown = state.get("last_suggested", [])
        picked = [shown[int(n) - 1] for n in a.dismiss if n.isdigit() and 0 < int(n) <= len(shown)]
        state["dismissed"] = sorted(set(state.get("dismissed", [])) | set(picked))
        save_state(state)
        print(f"Dismissed {len(picked)} suggestion(s)." if picked else "Run `suggest` first, then dismiss by its numbers.")
        return
    result = suggest(min_support=a.min_support)
    state["last_suggested"] = [s["key"] for s in result["suggestions"]]
    save_state(state)
    if a.json:
        json.dump(result, sys.stdout, indent=1)
        return
    print(f"{result['turns_scanned']} skill turns scanned; {result['multi_skill_turns']} loaded 2 or more skills.\n")
    if not result["suggestions"]:
        print("Nothing repeats often enough to suggest yet.")
    for i, s in enumerate(result["suggestions"], 1):
        where = f"only in {s['project']}" if s["project"] else "across projects"
        print(f"{i}. {len(s['skills'])} skills, loaded together in {s['turns']} turns / {s['sessions']} sessions, {where}")
        print("   " + " ".join(s["skills"]))
        if s["sometimes"]:
            print("   sometimes also: " + " ".join(s["sometimes"]))
        print()


def cmd_doctor(a):
    index, problems, unreadable = skill_index(), 0, []
    for name, pl in sorted(all_playlists(problems=unreadable).items()):
        missing = [s for s in pl["skills"] if s not in index]
        problems += bool(missing)
        print(f"{name}: {len(pl['skills']) - len(missing)}/{len(pl['skills'])} on disk" +
              (f"; not found: {', '.join(missing)}" if missing else "") +
              (f"; {pl['rejected']} invalid entries ignored" if pl["rejected"] else ""))
    for p in unreadable:
        print(f"Skipped: {p}")
    print("\nNot-found skills may be built-in or synced from claude.ai. Anything else was renamed or uninstalled."
          if problems else "\nAll playlist skills are installed.")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="playlists", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("play", help="print the load text for one or more playlists (swift+db, swift:index)")
    p.add_argument("ref", nargs="*")
    p.set_defaults(fn=cmd_play)
    sub.add_parser("catalog", help="print every playlist with its skills").set_defaults(fn=cmd_catalog)
    sub.add_parser("list", help="list playlists").set_defaults(fn=cmd_list)
    p = sub.add_parser("show", help="show a playlist and whether each skill is installed")
    p.add_argument("name")
    p.set_defaults(fn=cmd_show)
    p = sub.add_parser("skills", help="search installed skills by word, to find ids for a playlist")
    p.add_argument("query", nargs="*")
    p.add_argument("--limit", type=int, default=40)
    p.set_defaults(fn=cmd_skills)
    for name, fn in (("new", cmd_new), ("save-session", cmd_save_session)):
        p = sub.add_parser(name)
        p.add_argument("name")
        if name == "new":
            p.add_argument("skills", nargs="+")
        else:
            p.add_argument("--session", required=True, help="session id (${CLAUDE_SESSION_ID})")
            p.add_argument("--last", type=int, help="only the last N turns that loaded skills")
        p.add_argument("--description", "-d")
        p.add_argument("--mode", choices=MODES, default="invoke")
        p.add_argument("--project", action="store_true", help="save in this repo's .claude/playlists (shareable)")
        p.add_argument("--force", action="store_true")
        p.set_defaults(fn=fn)
    for name in ("add", "remove"):
        p = sub.add_parser(name)
        p.add_argument("name")
        p.add_argument("skills", nargs="+")
        p.set_defaults(fn=cmd_edit)
    p = sub.add_parser("set", help="change a playlist's description or default mode")
    p.add_argument("name")
    p.add_argument("--description", "-d")
    p.add_argument("--mode", choices=MODES)
    p.set_defaults(fn=cmd_set)
    p = sub.add_parser("rename")
    p.add_argument("name")
    p.add_argument("new_name")
    p.set_defaults(fn=cmd_rename)
    p = sub.add_parser("delete")
    p.add_argument("name")
    p.set_defaults(fn=cmd_delete)
    p = sub.add_parser("suggest", help="propose playlists from skills you repeatedly load together")
    p.add_argument("--min-support", type=int, default=3)
    p.add_argument("--json", action="store_true")
    p.add_argument("--dismiss", nargs="+", metavar="N", help="never suggest these numbered candidates again")
    p.set_defaults(fn=cmd_suggest)
    sub.add_parser("doctor", help="check every playlist against installed skills").set_defaults(fn=cmd_doctor)
    sub.add_parser("hook", help="UserPromptSubmit hook entry point").set_defaults(fn=lambda a: run_hook())

    args = ap.parse_args(argv)
    try:
        args.fn(args)
    except PlaylistError as e:
        # Exit 0 on purpose: a non-zero exit inside `!` injection aborts the whole skill and hides this message.
        print(f"Playlist error: {e}")


if __name__ == "__main__":
    main()
