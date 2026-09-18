#!/usr/bin/env python3
"""Skill playlists for Claude Code: a named list of skills that one slash command loads.

This whole tool is one skills-directory plugin named `playlist`:

    ~/.claude/skills/playlist/.claude-plugin/plugin.json
    ~/.claude/skills/playlist/SKILL.md                      /playlist: the guided create/edit/delete menu
    ~/.claude/skills/playlist/bin/                          this CLI, which that menu calls
    ~/.claude/skills/playlist/skills/<name>/playlist.json   a playlist (source of truth)
    ~/.claude/skills/playlist/skills/<name>/SKILL.md        /playlist:<name>, generated from it

Claude Code registers a plugin's root skill under the plugin's bare name and its other
skills as `name:skill`, so typing `/playlist` lists the menu and then every playlist. The generated
SKILL.md is static text: no shell runs when a playlist is played.

Standard library only, so the plugin has no install step. Anything read from a
playlist file is validated before it is written into a SKILL.md, because project
playlists are committed and shared.
"""
import argparse
import collections
import glob
import itertools
import json
import os
import re
import shutil
import sys

NAMESPACE = "playlist"
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,47}$")
SKILL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}(?::[A-Za-z0-9][A-Za-z0-9._-]{0,63})?$")
CMD_RE = re.compile(r"<command-name>/?([^<\s]+)</command-name>")
MODES = ("all", "pick")
# The Agent Skills spec caps a description at 1,024 characters.
DESCRIPTION_LIMIT = 1024
# Skills the harness loads for its own purposes; nobody picks these, so they are noise in a mined playlist.
HARNESS_SKILLS = {"artifact-design", "artifact-capabilities", "artifact-diagramming", "workflow-authoring"}
MENU_NOTE = ("To add it to the slash menu now, type /reload-plugins; otherwise /{ns}:{name} appears in your next "
             "session. Either way, `/{ns} {name}` followed by a request plays it right now.")


class PlaylistError(Exception):
    pass


# ---------------------------------------------------------------- locations

def config_dir():
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")


def personal_root():
    return os.environ.get("PLAYLISTS_HOME") or os.path.join(config_dir(), "skills", NAMESPACE)


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


def project_plugin_root(cwd=None):
    root = project_root(cwd)
    return os.path.join(root, ".claude", "skills", NAMESPACE) if root else None


def ensure_manifest(root):
    """A folder is only a plugin, and its playlists only appear under /playlist:, if it has a manifest.

    The personal folder ships with one. A project folder gets a minimal one the first time a
    playlist is shared into a repo. An existing manifest is never rewritten.
    """
    path = os.path.join(root, ".claude-plugin", "plugin.json")
    if os.path.exists(path):
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump({"name": NAMESPACE, "version": "1.0.0",
                   "description": "Skill playlists shared with this project. Type /playlist: to pick one."}, fh, indent=2)
        fh.write("\n")


# ---------------------------------------------------------------- playlists

def one_line(text, limit=120):
    text = "".join(ch if ch.isprintable() else " " for ch in str(text or ""))
    return re.sub(r"\s+", " ", text).strip()[:limit]


def count(n):
    return f"{n} skill" + ("" if n == 1 else "s")


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
    if any(s.startswith(NAMESPACE + ":") for s in skills):
        raise PlaylistError("A playlist cannot contain another playlist. List the skills themselves.")
    return list(dict.fromkeys(skills))


def load_file(path):
    """A playlist's name is its folder. Anything in the file that fails validation is dropped, not passed on."""
    name = check_name(os.path.basename(os.path.dirname(path)))
    try:
        with open(path) as fh:
            data = json.load(fh)
    except (OSError, ValueError) as e:
        raise PlaylistError(f"Could not read {path}: {e}")
    raw = data.get("skills", []) if isinstance(data, dict) else None
    if not isinstance(raw, list):
        raise PlaylistError(f"{path} is not a playlist: expected an object with a \"skills\" list.")
    valid = [s for s in raw if isinstance(s, str) and SKILL_RE.match(s) and not s.startswith(NAMESPACE + ":")]
    return {"name": name, "description": one_line(data.get("description")),
            "mode": data.get("mode") if data.get("mode") in MODES else "all",
            "auto_when": one_line(data.get("auto_when"), 200),
            "skills": list(dict.fromkeys(valid)), "rejected": len(raw) - len(valid), "path": path}


def all_playlists(cwd=None, problems=None):
    """name -> playlist. A project playlist shadows a personal one with the same name."""
    found = {}
    for scope, root in (("personal", personal_root()), ("project", project_plugin_root(cwd))):
        for path in sorted(glob.glob(os.path.join(root, "skills", "*", "playlist.json"))) if root else []:
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
    name = name[len(NAMESPACE) + 1:] if name.startswith(NAMESPACE + ":") else name
    if name not in lists:
        raise PlaylistError(f"No playlist named '{one_line(name, 60)}'. "
                            f"Playlists: {', '.join(sorted(lists)) or 'none yet'}.")
    return lists[name]


NB_HYPHEN = "\u2011"  # looks like a hyphen but never wraps, so a skill name is not split across two lines


def family_of(skill):
    """`swiftui-liquid-glass` and `nuxt-v4:nuxt-core` belong to the families `swiftui` and `nuxt`."""
    return re.split(r"[-_.]", skill.split(":")[-1])[0].lower()


def menu_description(pl):
    """The hover text beside a playlist in the slash menu: what it is for, then what is in it.

    The menu shows this as one wrapped paragraph and strips line breaks, so it is written as
    short sentences. Three or more skills that share a first word are grouped under it, which
    says `swiftui` once instead of seven times and leaves the distinct part of each name.
    """
    skills, n = pl["skills"], len(pl["skills"])
    lead = [text.rstrip(". ") + "." for text in (pl["description"], pl["auto_when"] and "Use when " + pl["auto_when"]) if text]
    sizes = collections.Counter(family_of(s) for s in skills)
    grouped = [f for f in dict.fromkeys(family_of(s) for s in skills) if sizes[f] >= 3]
    items = []
    for fam in grouped:
        seen = set()
        for s in (s for s in skills if family_of(s) == fam):
            label = s.split(":")[-1][len(fam):].lstrip("-_.") or fam
            label = s if label in seen else label  # two ids that shorten to the same word keep their full id
            seen.add(label)
            items.append((fam, label))
    rest = [s for s in skills if family_of(s) not in grouped]
    items += [("Also" if grouped else count(n), s) for s in rest]

    def compose(shown):
        parts = lead + ([count(n) + "."] if grouped else [])
        for label, members in itertools.groupby(shown, key=lambda item: item[0]):
            parts.append(f"{label}: " + ", ".join(m.replace("-", NB_HYPHEN) for _, m in members) + ".")
        if len(shown) < n:
            parts.append(f"And {n - len(shown)} more.")
        return " ".join(parts)

    keep = n
    while keep and len(compose(items[:keep])) > DESCRIPTION_LIMIT:
        keep -= 1
    return compose(items[:keep])


def render_skill(pl, index):
    """The SKILL.md a playlist becomes. Static text only, so playing one never runs a command."""
    name, skills, n = pl["name"], pl["skills"], len(pl["skills"])
    front = [f"name: {name}", "description: " + json.dumps(menu_description(pl), ensure_ascii=False)]
    if not pl["auto_when"]:
        # Loading many skills unasked is an expensive surprise, so a playlist only plays when the user calls it.
        front.append("disable-model-invocation: true")
    front.append('argument-hint: "[your request]"')
    if pl["mode"] == "pick":
        rows = "\n".join(f"- {s}" + (f": {read_description(index[s])}" if s in index and read_description(index[s]) else "")
                         for s in skills)
        steps = (
            f"1. Before anything else, tell the user in one line: Loading from playlist \"{name}\" ({n} skills available).\n"
            f"2. From the list below, choose the skills the user's request actually needs. Call the Skill tool once for "
            f"each of those, all in a single message so they load in parallel. If there is no request, load nothing and "
            f"ask what they are working on.\n\n{rows}\n\n"
            f"3. When the calls return, start your reply with one line: `▶ {name} · loaded <k> of {n} skills`, then list "
            f"the ones you loaded and name any whose call failed.")
    else:
        rows = "\n".join(f"   {i}. {s}" for i, s in enumerate(skills, 1))
        steps = (
            f"1. Before anything else, tell the user in one line: Loading {n} skills from playlist \"{name}\".\n"
            f"2. Call the Skill tool once for each skill below, all in a single message so they load in parallel. Skip "
            f"a skill only if it was already loaded earlier in this conversation. Do not substitute, summarise or drop "
            f"any.\n\n{rows}\n\n"
            f"3. When the calls return, start your reply with one line: `▶ {name} · <loaded>/{n} skills loaded`. Count a "
            f"skill as loaded only if its Skill call returned the skill's content, and name every skill whose call failed.")
    return ("---\n" + "\n".join(front) + "\n---\n\n"
            "<!-- Generated from playlist.json by the playlists plugin. Change it with /playlist; "
            "hand edits here are overwritten. -->\n\n"
            f"This is the \"{name}\" skill playlist: {n} skills that load together.\n\n{steps}\n"
            f"4. Then carry out the user's request with those skills applied. If the request below is empty, stop after step 3.\n\n"
            f"The user's request: $ARGUMENTS\n")


def write_playlist(name, skills, description="", mode="all", auto_when="", project=False, cwd=None, folder=None):
    """Writes playlist.json and its SKILL.md. `folder` is given when editing, so an edit never changes scope."""
    check_name(name)
    skills = check_skills(skills)
    if folder is None:
        root = project_plugin_root(cwd) if project else personal_root()
        if not root:
            raise PlaylistError("Not inside a project (no .git or .claude found), so there is nowhere to save a project playlist.")
        folder = os.path.join(root, "skills", name)
    ensure_manifest(os.path.dirname(os.path.dirname(folder)))
    os.makedirs(folder, exist_ok=True)
    pl = {"name": name, "description": one_line(description), "mode": mode if mode in MODES else "all",
          "auto_when": one_line(auto_when, 200), "skills": skills}
    for filename, text in (("playlist.json", json.dumps(pl, indent=2) + "\n"),
                           ("SKILL.md", render_skill(pl, skill_index(cwd) if pl["mode"] == "pick" else {}))):
        tmp = os.path.join(folder, filename + ".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
        os.replace(tmp, os.path.join(folder, filename))
    return folder


def remove_playlist(pl):
    """Deletes only the two files this tool wrote, then the folder if nothing else is in it."""
    folder = os.path.dirname(pl["path"])
    for filename in ("playlist.json", "SKILL.md"):
        if os.path.exists(os.path.join(folder, filename)):
            os.remove(os.path.join(folder, filename))
    if not os.listdir(folder):
        os.rmdir(folder)


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
            return one_line(value.strip("\"'"), 200)
    return ""


def readable_skill_file(path, inside=None):
    """Descriptions are copied into generated skills, so only ever read real markdown files.

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
    """Skill id -> SKILL.md path, for every skill found on disk, playlists excluded.

    Skills bundled with Claude Code or synced from claude.ai are not on disk, so a
    miss here means "cannot verify", not "does not exist".
    """
    index = {}

    def add(key, path, inside=None):
        if key == NAMESPACE:  # this tool's own root skill, not something to put in a playlist
            return
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
    """Drop harness-loaded skills, playlists and our own commands; keep exact ids in first-use order."""
    out = []
    for s in skills:
        ours = s == NAMESPACE or s.startswith((NAMESPACE + ":", "playlists:"))
        if canonical(s) not in HARNESS_SKILLS and not ours and s not in out:
            out.append(s)
    return out


def session_skills(session_id, last=None, cwd=None):
    if not re.match(r"^[A-Za-z0-9_-]{1,80}$", session_id or ""):
        raise PlaylistError("That is not a session id.")
    paths = glob.glob(os.path.join(config_dir(), "projects", "*", session_id + ".jsonl"))
    if not paths:
        raise PlaylistError(f"No transcript found for session {session_id}.")
    turns = [t for t in (clean(t) for _, t in transcript_turns(paths[0], set(skill_index(cwd)))) if t]
    skills = clean(itertools.chain.from_iterable(turns[-last:] if last else turns))
    if not skills:
        raise PlaylistError("No skills were loaded in this conversation yet, so there is nothing to capture.")
    return skills


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
        with open(os.path.join(personal_root(), ".state.json")) as fh:
            state = json.load(fh)
        return state if isinstance(state, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(state):
    os.makedirs(personal_root(), exist_ok=True)
    with open(os.path.join(personal_root(), ".state.json"), "w") as fh:
        json.dump(state, fh, indent=2)


# ---------------------------------------------------------------- cli

def cmd_list(a):
    problems = []
    lists = all_playlists(problems=problems)
    if not lists:
        print("No playlists yet. Create one with `new <name> <skill> [<skill> ...]`, or `new <name> --session <id>` "
              "to capture the skills loaded in this conversation. `skills <word>` finds skill ids.")
    else:
        width = max(len(n) for n in lists) + len(NAMESPACE) + 2
        print("\n".join(
            f"{('/' + NAMESPACE + ':' + n).ljust(width)}  {count(len(p['skills'])):>10}  {p['scope']:<8}  "
            f"{p['mode']:<4}  {p['description']}".rstrip() for n, p in sorted(lists.items())))
    for p in problems:
        print(f"Skipped: {p}")


def cmd_show(a):
    pl = get_playlist(a.name)
    index = skill_index()
    print(f"/{NAMESPACE}:{pl['name']} ({pl['scope']}, loads {pl['mode']}) {pl['description']}")
    if pl["auto_when"]:
        print(f"Claude may load it on its own when {pl['auto_when']}.")
    print(os.path.dirname(pl["path"]) + "\n")
    for i, s in enumerate(pl["skills"], 1):
        print(f"  {i:>2}. {s}" + ("" if s in index else "   (not found on disk)"))
    if pl["rejected"]:
        print(f"\n{pl['rejected']} entries in the file are not valid skill ids and are ignored.")
    print(not_on_disk(pl["skills"]).strip())


def cmd_skills(a):
    index = skill_index()
    words = [w.lower() for w in a.query]
    rows = [(k, read_description(v)) for k, v in sorted(index.items())]
    rows = [(k, d) for k, d in rows if all(w in k.lower() or w in d.lower() for w in words)]
    rows.sort(key=lambda r: (not all(w in r[0].lower() for w in words), r[0]))  # id matches before description matches
    print(f"{len(rows)} of {len(index)} installed skills" + (f" match '{' '.join(a.query)}'" if words else "") + ":\n")
    for k, d in rows[:a.limit]:
        print(f"{k}  {d[:110]}")
    if len(rows) > a.limit:
        print(f"\n... {len(rows) - a.limit} more. Narrow it with another word.")


def cmd_loaded(a):
    skills = session_skills(a.session, a.last)
    print(f"{count(len(skills))} loaded in this conversation:\n" + "\n".join(f"  {i:>2}. {s}" for i, s in enumerate(skills, 1)))


def match_word(word, index, descriptions, limit):
    """Best installed skills for one word: exact id first, then name matches, then description matches."""
    w = re.sub(r"[^a-z0-9._:-]", "", word.lower())
    if not w:
        return [], False
    tiers = {}
    for key in index:
        low = key.lower()
        tail = low.split(":")[-1]
        tokens = set(re.split(r"[-_.:]", low))
        if low == w or tail == w:
            tier = 0
        elif w in tokens:
            tier = 1
        elif low.startswith(w) or tail.startswith(w):
            tier = 2
        elif w in low:
            tier = 3
        elif len(w) >= 3 and re.search(r"\b" + re.escape(w) + r"\b", descriptions[key].lower()):
            tier = 4
        else:
            continue
        # A personal skill beats its plugin copy, and a short id beats a long one, within a tier.
        tiers[key] = (tier, ":" in key, len(key), key)
    ranked = sorted(tiers, key=tiers.get)
    return ranked[:limit], bool(ranked) and tiers[ranked[0]][0] == 0


def cmd_match(a):
    """Resolve many words in one call, so a playlist spanning several technologies needs one step, not one per word."""
    index = skill_index()
    descriptions = {k: read_description(v) for k, v in index.items()}
    for word in dict.fromkeys(a.words):
        found, exact = match_word(word, index, descriptions, a.limit)
        shown = one_line(word, 40)
        if not found:
            print(f"{shown}: no match")
            continue
        print(f"{shown}: " + ("exact id" if exact else f"no exact id, best {len(found)} shown"))
        for k in found:
            print(f"  {k}  {descriptions[k][:90]}")


def cmd_new(a):
    skills = list(a.skills) + (session_skills(a.session, a.last) if a.session else [])
    if not skills:
        raise PlaylistError("List the skills for the playlist, or pass --session to capture this conversation's skills.")
    if a.name in all_playlists() and not a.force:
        raise PlaylistError(f"Playlist '{a.name}' already exists. Pass --force to replace it, or use `add`.")
    folder = write_playlist(a.name, skills, a.description or "", a.mode, project=a.project)
    print(f"Created playlist '{a.name}' with {count(len(set(skills)))} in {folder}\n"
          + "\n".join(f"  {i:>2}. {s}" for i, s in enumerate(dict.fromkeys(skills), 1)) + "\n"
          + MENU_NOTE.format(ns=NAMESPACE, name=a.name) + not_on_disk(skills))


def cmd_edit(a):
    pl = get_playlist(a.name)
    given = list(a.skills) + (session_skills(a.session) if getattr(a, "session", None) else [])
    if not given:
        raise PlaylistError("Name at least one skill.")
    if a.command == "remove":
        absent = [s for s in given if s not in pl["skills"]]
        if absent:
            raise PlaylistError(f"Not in '{pl['name']}': {', '.join(absent)}. It has: {', '.join(pl['skills'])}.")
        skills = [s for s in pl["skills"] if s not in given]
        if not skills:
            raise PlaylistError(f"That would empty '{pl['name']}'. Delete the playlist instead.")
    else:
        skills = pl["skills"] + given
    write_playlist(pl["name"], skills, pl["description"], pl["mode"], pl["auto_when"], folder=os.path.dirname(pl["path"]))
    changed = len(set(skills)) - len(pl["skills"])
    print(f"/{NAMESPACE}:{pl['name']} now has {count(len(set(skills)))} ({changed:+d}). The change is live in this session."
          + (not_on_disk(given) if a.command == "add" else ""))


def cmd_set(a):
    pl = get_playlist(a.name)
    auto = "" if a.no_auto else (a.auto if a.auto is not None else pl["auto_when"])
    write_playlist(pl["name"], pl["skills"], a.description if a.description is not None else pl["description"],
                   a.mode or pl["mode"], auto, folder=os.path.dirname(pl["path"]))
    print(f"Updated '{pl['name']}'.")


def cmd_rename(a):
    pl = get_playlist(a.name)
    check_name(a.new_name)
    if a.new_name in all_playlists():
        raise PlaylistError(f"Playlist '{a.new_name}' already exists.")
    write_playlist(a.new_name, pl["skills"], pl["description"], pl["mode"], pl["auto_when"],
                   folder=os.path.join(os.path.dirname(os.path.dirname(pl["path"])), a.new_name))
    remove_playlist(pl)
    print(f"Renamed '{pl['name']}' to '{a.new_name}'. " + MENU_NOTE.format(ns=NAMESPACE, name=a.new_name))


def cmd_delete(a):
    pl = get_playlist(a.name)
    remove_playlist(pl)
    print(f"Deleted playlist '{pl['name']}' ({count(len(pl['skills']))}). "
          f"It leaves the / menu from your next session. The skills themselves are untouched.")


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
        skill_md = os.path.join(os.path.dirname(pl["path"]), "SKILL.md")
        try:
            with open(skill_md, encoding="utf-8") as fh:
                stale = fh.read() != render_skill(pl, index if pl["mode"] == "pick" else {})
        except OSError:
            stale = True
        print(f"{name}: {len(pl['skills']) - len(missing)}/{len(pl['skills'])} on disk" +
              (f"; not found: {', '.join(missing)}" if missing else "") +
              (f"; {pl['rejected']} invalid entries ignored" if pl["rejected"] else "") +
              ("; SKILL.md is out of date, run `sync`" if stale else ""))
    for p in unreadable:
        print(f"Skipped: {p}")
    print("\nNot-found skills may be built-in or synced from claude.ai. Anything else was renamed or uninstalled."
          if problems else "\nAll playlist skills are installed.")


def cmd_sync(a):
    """Regenerate every SKILL.md from its playlist.json, and bring over playlists saved by version 0.1."""
    legacy = os.path.join(config_dir(), "playlists")
    moved = 0
    for path in sorted(glob.glob(os.path.join(legacy, "*.json"))):
        name = os.path.basename(path)[:-5]
        try:
            with open(path) as fh:
                old = json.load(fh)
            if NAME_RE.match(name) and name not in all_playlists() and isinstance(old.get("skills"), list):
                write_playlist(name, [s for s in old["skills"] if isinstance(s, str) and SKILL_RE.match(s)],
                               old.get("description", ""))
                os.remove(path)
                moved += 1
        except (OSError, ValueError, AttributeError, PlaylistError):
            continue
    if os.path.isdir(legacy) and not [f for f in os.listdir(legacy) if f != ".state.json"]:
        shutil.rmtree(legacy)
    lists = all_playlists()
    for pl in lists.values():
        write_playlist(pl["name"], pl["skills"], pl["description"], pl["mode"], pl["auto_when"],
                       folder=os.path.dirname(pl["path"]))
    print(f"Regenerated {len(lists)} playlist(s)" + (f", {moved} brought over from the old format." if moved else "."))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="playlist", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="list playlists").set_defaults(fn=cmd_list)
    p = sub.add_parser("show", help="show a playlist's skills and whether each is installed")
    p.add_argument("name")
    p.set_defaults(fn=cmd_show)
    p = sub.add_parser("skills", help="search installed skills by word, to find exact ids")
    p.add_argument("query", nargs="*")
    p.add_argument("--limit", type=int, default=25)
    p.set_defaults(fn=cmd_skills)
    p = sub.add_parser("match", help="find the best installed skills for several words at once")
    p.add_argument("words", nargs="+")
    p.add_argument("--limit", type=int, default=5, help="matches to show per word")
    p.set_defaults(fn=cmd_match)
    p = sub.add_parser("loaded", help="show the skills loaded in a conversation, without creating anything")
    p.add_argument("--session", required=True, help="session id (${CLAUDE_SESSION_ID})")
    p.add_argument("--last", type=int, help="only the last N turns that loaded skills")
    p.set_defaults(fn=cmd_loaded)
    p = sub.add_parser("new", help="create a playlist from named skills and/or this conversation's skills")
    p.add_argument("name")
    p.add_argument("skills", nargs="*")
    p.add_argument("--session", help="capture the skills loaded in this session (${CLAUDE_SESSION_ID})")
    p.add_argument("--last", type=int, help="with --session: only the last N turns that loaded skills")
    p.add_argument("--description", "-d")
    p.add_argument("--mode", choices=MODES, default="all")
    p.add_argument("--project", action="store_true", help="save in this repo's .claude/skills/playlist (shareable)")
    p.add_argument("--force", action="store_true")
    p.set_defaults(fn=cmd_new)
    for name in ("add", "remove"):
        p = sub.add_parser(name, help=f"{name} skills {'to' if name == 'add' else 'from'} a playlist")
        p.add_argument("name")
        p.add_argument("skills", nargs="*")
        if name == "add":
            p.add_argument("--session", help="add the skills loaded in this session")
        p.set_defaults(fn=cmd_edit)
    p = sub.add_parser("set", help="change a playlist's description, load mode or auto-load rule")
    p.add_argument("name")
    p.add_argument("--description", "-d")
    p.add_argument("--mode", choices=MODES, help="all: load every skill. pick: Claude loads only what the request needs")
    p.add_argument("--auto", metavar="WHEN", help="let Claude load it unasked, e.g. 'working on Swift or SwiftUI code'")
    p.add_argument("--no-auto", action="store_true")
    p.set_defaults(fn=cmd_set)
    p = sub.add_parser("rename")
    p.add_argument("name")
    p.add_argument("new_name")
    p.set_defaults(fn=cmd_rename)
    p = sub.add_parser("delete", help="delete a playlist (never the skills in it)")
    p.add_argument("name")
    p.set_defaults(fn=cmd_delete)
    p = sub.add_parser("suggest", help="propose playlists from skills you repeatedly load together")
    p.add_argument("--min-support", type=int, default=3)
    p.add_argument("--json", action="store_true")
    p.add_argument("--dismiss", nargs="+", metavar="N", help="never suggest these numbered candidates again")
    p.set_defaults(fn=cmd_suggest)
    sub.add_parser("doctor", help="check every playlist against installed skills").set_defaults(fn=cmd_doctor)
    sub.add_parser("sync", help="regenerate every playlist's SKILL.md").set_defaults(fn=cmd_sync)

    args = ap.parse_args(argv)
    try:
        args.fn(args)
    except PlaylistError as e:
        print(f"Playlist error: {e}")


if __name__ == "__main__":
    main()
