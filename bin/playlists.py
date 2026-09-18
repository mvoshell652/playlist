#!/usr/bin/env python3
"""Skill playlists for Claude Code: a named list of skills that one reference loads.

A playlist is a small JSON file. `play` prints the text that reaches the model;
everything else manages the files. Standard library only, so the plugin has no
install step.

Playlists are data read at play time, never generated skills: a running session
does not see skill files created after it started, but it always sees a JSON
file written a second ago.
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
TOKEN_RE = re.compile(r"(?<![\w@])@@([a-z0-9][a-z0-9_-]{0,47})(?::(invoke|inline|index))?\b")
CMD_RE = re.compile(r"<command-name>/?([^<\s]+)</command-name>")
MODES = ("invoke", "inline", "index")
# `!` injection output shares the Bash tool's 30,000-character inline ceiling.
INLINE_BUDGET = 24000
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
        raise PlaylistError(f"'{name}' is not a valid playlist name. Use lowercase letters, digits, - or _ (max 48).")
    return name


def load_file(path):
    try:
        with open(path) as fh:
            data = json.load(fh)
    except (OSError, ValueError) as e:
        raise PlaylistError(f"Could not read {path}: {e}")
    skills = [s for s in data.get("skills", []) if isinstance(s, str) and s.strip()]
    mode = data.get("mode") if data.get("mode") in MODES else "invoke"
    return {"name": data.get("name") or os.path.basename(path)[:-5], "description": data.get("description", ""),
            "mode": mode, "skills": list(dict.fromkeys(skills)), "path": path}


def all_playlists(cwd=None):
    """name -> playlist. A project playlist shadows a global one of the same name."""
    found = {}
    for scope, d in (("global", global_dir()), ("project", project_dir(cwd))):
        if not d or not os.path.isdir(d):
            continue
        for path in sorted(glob.glob(os.path.join(d, "*.json"))):
            try:
                pl = load_file(path)
            except PlaylistError:
                continue
            pl["scope"] = scope
            found[pl["name"]] = pl
    return found


def get_playlist(name, cwd=None):
    lists = all_playlists(cwd)
    if name not in lists:
        known = ", ".join(sorted(lists)) or "none yet"
        raise PlaylistError(f"No playlist named '{name}'. Playlists: {known}.")
    return lists[name]


def write_playlist(name, skills, description="", mode="invoke", project=False, cwd=None):
    check_name(name)
    d = project_dir(cwd) if project else global_dir()
    if not d:
        raise PlaylistError("Not inside a project (no .git or .claude found), so there is nowhere to save a project playlist.")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, name + ".json")
    body = {"name": name, "description": description, "mode": mode, "skills": list(dict.fromkeys(skills))}
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
            head = fh.read(6000)
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
            return value.strip("\"'")
    return ""


def skill_index(cwd=None):
    """Skill id -> SKILL.md path, for every skill found on disk.

    Skills bundled with Claude Code or synced from claude.ai are not on disk, so a
    miss here means "cannot verify", not "does not exist".
    """
    index = {}

    def add_dir(skills_dir, prefix=""):
        for path in glob.glob(os.path.join(skills_dir, "*", "SKILL.md")):
            index.setdefault(prefix + os.path.basename(os.path.dirname(path)), path)

    root = project_root(cwd)
    if root:
        add_dir(os.path.join(root, ".claude", "skills"))
    add_dir(os.path.join(config_dir(), "skills"))
    for base in filter(None, (root and os.path.join(root, ".claude", "commands"), os.path.join(config_dir(), "commands"))):
        for path in glob.glob(os.path.join(base, "*.md")):
            index.setdefault(os.path.basename(path)[:-3], path)
    try:
        with open(os.path.join(config_dir(), "plugins", "installed_plugins.json")) as fh:
            plugins = json.load(fh).get("plugins", {})
    except (OSError, ValueError):
        plugins = {}
    for key, installs in plugins.items():
        for inst in installs if isinstance(installs, list) else []:
            if inst.get("installPath"):
                add_dir(os.path.join(inst["installPath"], "skills"), prefix=key.split("@")[0] + ":")
    return index


def strip_frontmatter(text):
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:].lstrip("\n")
    return text


# ---------------------------------------------------------------- play

def parse_refs(arg):
    """'swift+supabase:index' -> [('swift', None), ('supabase', 'index')]."""
    refs = []
    for part in re.split(r"[+,]", arg or ""):
        part = part.strip()
        if not part:
            continue
        name, _, mode = part.partition(":")
        if mode and mode not in MODES:
            raise PlaylistError(f"Unknown mode '{mode}'. Modes: {', '.join(MODES)}.")
        refs.append((name, mode or None))
    return refs


def numbered(skills):
    return "\n".join(f"{i}. {s}" for i, s in enumerate(skills, 1))


def render_invoke(label, skills):
    return (
        f"Load every skill below now. Call the Skill tool once per skill, all in a single message so they load "
        f"in parallel. Skip a skill only if it was already loaded earlier in this conversation. Do not "
        f"substitute, summarise or drop any.\n\n{numbered(skills)}\n\n"
        f"When the calls return, start your reply with one line, `▶ {label}: <loaded>/{len(skills)} loaded`, and name "
        f"any skill that failed to load. Then carry out the user's request with all of them applied."
    )


def render_index(label, skills, index):
    rows, unknown = [], []
    for s in skills:
        if s in index:
            rows.append(f"- {s}: {read_description(index[s]) or '(no description)'}\n  {index[s]}")
        else:
            unknown.append(s)
    out = (f"These {len(rows)} skills are available for this request. Read the SKILL.md of each one the request "
           f"actually touches before you start; you do not need all of them.\n\n" + "\n".join(rows))
    if unknown:
        out += "\n\nNot found on disk, so load these with the Skill tool if they are relevant:\n" + numbered(unknown)
    return out + f"\n\nStart your reply with one line: `▶ {label}: read <n> of {len(skills)}`."


def render_inline(label, skills, index):
    parts, deferred, used = [], [], 0
    for s in skills:
        body = None
        if s in index:
            try:
                with open(index[s], errors="ignore") as fh:
                    body = strip_frontmatter(fh.read())
            except OSError:
                body = None
        if body is None or used + len(body) > INLINE_BUDGET:
            deferred.append(s)
            continue
        used += len(body)
        parts.append(f"<skill name=\"{s}\" base-directory=\"{os.path.dirname(index[s])}\">\n{body.rstrip()}\n</skill>")
    out = (f"{len(parts)} of {len(skills)} skills are included in full below. Treat each as loaded; relative paths "
           f"inside a skill resolve against its base-directory.\n\n" + "\n\n".join(parts))
    if deferred:
        out += (f"\n\nThese {len(deferred)} did not fit the inline budget or are not on disk. Load them with the "
                f"Skill tool, all in one message:\n" + numbered(deferred))
    return out + f"\n\nStart your reply with one line: `▶ {label}: {len(skills)} skills applied`."


def render_play(refs, cwd=None):
    """Text for the model. Several playlists merge into one de-duplicated list; the first explicit mode wins."""
    if not refs:
        raise PlaylistError("Name a playlist, for example `/playlists:play swift`.")
    skills, labels, mode = [], [], None
    for name, ref_mode in refs:
        pl = get_playlist(name, cwd)
        labels.append(pl["name"])
        mode = mode or ref_mode
        skills.extend(pl["skills"])
        default_mode = pl["mode"]
    mode = mode or (default_mode if len(refs) == 1 else "invoke")
    skills = list(dict.fromkeys(skills))
    if not skills:
        raise PlaylistError(f"Playlist '{labels[0]}' is empty. Add skills with `playlists.py add {labels[0]} <skill>`.")
    label = "+".join(labels)
    header = f"Skill playlist \"{label}\": {len(skills)} skills, {mode} mode.\n\n"
    if mode == "invoke":
        return header + render_invoke(label, skills)
    index = skill_index(cwd)
    return header + (render_index if mode == "index" else render_inline)(label, skills, index)


# ---------------------------------------------------------------- transcripts

def transcript_turns(path, known=None):
    """Yield (cwd, [skills]) per user turn that loaded at least one skill, in order of first use."""
    cur, cwd = [], None
    with open(path, errors="ignore") as fh:
        for line in fh:
            if '"Skill"' not in line and "<command-name>" not in line and '"type":"user"' not in line:
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
                if not is_result and not d.get("isMeta"):
                    if cur:
                        yield cwd, cur
                    cur = []
                text = content if isinstance(content, str) else " ".join(
                    x.get("text", "") for x in content if isinstance(x, dict) and x.get("type") == "text"
                ) if isinstance(content, list) else ""
                # A typed /command counts only when it names an installed skill; /model, /clear and friends do not.
                cur.extend(n for n in CMD_RE.findall(text) if known is None or n in known)
            elif d.get("type") == "assistant" and isinstance(content, list):
                for x in content:
                    if isinstance(x, dict) and x.get("type") == "tool_use" and x.get("name") == "Skill":
                        name = (x.get("input") or {}).get("skill")
                        if name:
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


def session_skills(session_id, last=None):
    paths = glob.glob(os.path.join(config_dir(), "projects", "*", session_id + ".jsonl"))
    if not paths:
        raise PlaylistError(f"No transcript found for session {session_id}.")
    turns = [clean(t) for _, t in transcript_turns(paths[0])]
    turns = [t for t in turns if t]
    if last:
        turns = turns[-last:]
    return clean(itertools.chain.from_iterable(turns))


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
        home = next((c for c in clusters if jaccard(s, c[0]) >= threshold), None)
        if home:
            home.append(s)
        else:
            clusters.append([s])
    existing = [frozenset(canonical(s) for s in p["skills"]) for p in all_playlists(cwd).values() if p["skills"]]

    def exact(skill):
        """The id this user actually types most often for a canonical skill, so the playlist loads as-is."""
        forms = [(n, f) for f, n in spelled.items() if canonical(f) == skill]
        return max(forms)[1] if forms else skill

    dismissed = set(load_state().get("dismissed", []))
    out = []
    for members in clusters:
        uses = [o for o in multi if o[1] in set(members)]
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
        out.append({"skills": [exact(s) for s in core], "sometimes": sorted(s for s, n in counts.items() if s not in core and n >= 2),
                    "turns": len(uses), "sessions": len({p for _, _, p in uses}),
                    "project": top[0] if single_project else None, "key": key})
    out.sort(key=lambda s: s["turns"] * len(s["skills"]), reverse=True)
    return {"turns_scanned": len(observed), "multi_skill_turns": len(multi), "suggestions": out}


def load_state():
    try:
        with open(os.path.join(global_dir(), ".state.json")) as fh:
            return json.load(fh)
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
        lists = all_playlists(cwd)
        refs = [(n, m or None) for n, m in TOKEN_RE.findall(prompt) if n in lists]
        if not refs:
            return
        text = render_play(list(dict.fromkeys(refs)), cwd)
        # A hook may add at most 10,000 characters; inline bodies do not fit, so fall back to invoke.
        if len(text) > 9000:
            text = render_play([(n, "invoke") for n, _ in dict.fromkeys(refs)], cwd)
        note = "The user's message references a skill playlist with an @@name token. " + text
        json.dump({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": note}}, sys.stdout)
    except Exception:
        return


# ---------------------------------------------------------------- cli

def cmd_play(a):
    arg = "" if a.ref.startswith("$") else a.ref  # an unfilled `$0` placeholder means no argument was typed
    if not arg:
        return cmd_list(a, preface="No playlist named. Ask the user which one to play.\n\n")
    print(render_play(parse_refs(arg)))


def cmd_list(a, preface=""):
    lists = all_playlists()
    if not lists:
        print(preface + "No playlists yet. Create one: playlists.py new <name> <skill> [<skill> ...]")
        return
    width = max(len(n) for n in lists)
    print(preface + "\n".join(
        f"{n.ljust(width)}  {len(p['skills']):>3} skills  {p['scope']:<7}  {p['mode']:<6}  {p['description']}".rstrip()
        for n, p in sorted(lists.items())))


def cmd_show(a):
    pl = get_playlist(a.name)
    index = skill_index()
    print(f"{pl['name']} ({pl['scope']}, {pl['mode']} mode): {pl['description']}\n{pl['path']}\n")
    for s in pl["skills"]:
        print(f"  {'ok ' if s in index else '?  '} {s}")
    if any(s not in index for s in pl["skills"]):
        print("\n? = not found on disk. Built-in and claude.ai-synced skills always show this; otherwise check the name.")


def cmd_new(a):
    if a.name in all_playlists() and not a.force:
        raise PlaylistError(f"Playlist '{a.name}' already exists. Pass --force to replace it, or use `add`.")
    path = write_playlist(a.name, a.skills, a.description or "", a.mode, a.project)
    print(f"Saved '{a.name}' with {len(set(a.skills))} skills to {path}\n"
          f"Play it with /playlists:play {a.name}, or write @@{a.name} anywhere in a message.")


def cmd_edit(a):
    pl = get_playlist(a.name)
    skills = [s for s in pl["skills"] if s not in a.skills] if a.command == "remove" else pl["skills"] + a.skills
    write_playlist(pl["name"], skills, pl["description"], pl["mode"], pl["scope"] == "project")
    print(f"'{pl['name']}' now has {len(set(skills))} skills.")


def cmd_set(a):
    pl = get_playlist(a.name)
    write_playlist(pl["name"], pl["skills"], a.description if a.description is not None else pl["description"],
                   a.mode or pl["mode"], pl["scope"] == "project")
    print(f"Updated '{pl['name']}'.")


def cmd_delete(a):
    pl = get_playlist(a.name)
    os.remove(pl["path"])
    print(f"Deleted '{pl['name']}' ({pl['path']}).")


def cmd_save_session(a):
    skills = session_skills(a.session, a.last)
    if not skills:
        raise PlaylistError("No skills were loaded in this session yet, so there is nothing to save.")
    a.skills = skills
    cmd_new(a)


def cmd_suggest(a):
    result = suggest(min_support=a.min_support)
    if a.dismiss:
        picked = [s["key"] for i, s in enumerate(result["suggestions"], 1) if str(i) in a.dismiss]
        state = load_state()
        state["dismissed"] = sorted(set(state.get("dismissed", [])) | set(picked))
        save_state(state)
        print(f"Dismissed {len(picked)} suggestion(s).")
        return
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
    index, problems = skill_index(), 0
    for name, pl in sorted(all_playlists().items()):
        missing = [s for s in pl["skills"] if s not in index]
        problems += bool(missing)
        print(f"{name}: {len(pl['skills']) - len(missing)}/{len(pl['skills'])} on disk" +
              (f"; not found: {', '.join(missing)}" if missing else ""))
    print("\nNot-found skills may be built-in or synced from claude.ai. Anything else was renamed or uninstalled."
          if problems else "\nAll playlist skills are installed.")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="playlists", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)

    p = sub.add_parser("play", help="print the load text for one or more playlists (swift+supabase, swift:index)")
    p.add_argument("ref", nargs="?", default="")
    p.set_defaults(fn=cmd_play)
    sub.add_parser("list", help="list playlists").set_defaults(fn=cmd_list)
    p = sub.add_parser("show", help="show a playlist and whether each skill is installed")
    p.add_argument("name")
    p.set_defaults(fn=cmd_show)
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
