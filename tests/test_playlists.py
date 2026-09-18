"""Run with: python3 -m unittest discover -s tests -v"""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("playlists", os.path.join(ROOT, "bin", "playlists.py"))
pl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pl)


def skill(config, name, description="A skill.", body="Body of {name}.", plugin=None):
    base = os.path.join(config, "plugins", "cache", plugin, "skills") if plugin else os.path.join(config, "skills")
    os.makedirs(os.path.join(base, name))
    with open(os.path.join(base, name, "SKILL.md"), "w") as fh:
        fh.write(f"---\nname: {name}\ndescription: {description}\n---\n\n" + body.format(name=name))


def line(kind, content, **extra):
    return json.dumps({"type": kind, "message": {"content": content}, "cwd": "/repo", **extra})


def skill_call(name):
    return line("assistant", [{"type": "tool_use", "name": "Skill", "input": {"skill": name}}])


class Sandbox(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.config = os.path.join(self.tmp.name, "claude")
        self.repo = os.path.join(self.tmp.name, "repo")
        os.makedirs(os.path.join(self.repo, ".git"))
        os.makedirs(self.config)
        self.env = {k: os.environ.get(k) for k in ("CLAUDE_CONFIG_DIR", "PLAYLISTS_HOME")}
        os.environ["CLAUDE_CONFIG_DIR"] = self.config
        os.environ.pop("PLAYLISTS_HOME", None)
        self.cwd = os.getcwd()
        os.chdir(self.repo)

    def tearDown(self):
        os.chdir(self.cwd)
        for k, v in self.env.items():
            os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        self.tmp.cleanup()

    def run_cli(self, *argv, stdin=None):
        out = io.StringIO()
        old = sys.stdin
        sys.stdin = io.StringIO(stdin) if stdin is not None else old
        try:
            with contextlib.redirect_stdout(out):
                pl.main(list(argv))
        finally:
            sys.stdin = old
        return out.getvalue()


class PlayTests(Sandbox):
    def test_invoke_lists_every_skill_once_in_order(self):
        self.run_cli("new", "swift", "swiftui-pro", "swift-testing", "swiftui-pro")
        text = self.run_cli("play", "swift")
        self.assertIn("1. swiftui-pro\n2. swift-testing", text)
        self.assertNotIn("3.", text)
        self.assertIn("<loaded>/2 loaded", text)

    def test_new_playlist_is_playable_without_any_reload(self):
        self.assertIn("No playlist named 'later'", self.run_cli("play", "later"))
        self.run_cli("new", "later", "a")
        self.assertIn("1. a", self.run_cli("play", "later"))

    def test_two_playlists_merge_and_dedupe(self):
        self.run_cli("new", "swift", "a", "b")
        self.run_cli("new", "db", "b", "c")
        text = self.run_cli("play", "swift+db")
        self.assertIn('"swift+db": 3 skills', text)
        self.assertIn("1. a\n2. b\n3. c", text)

    def test_unfilled_placeholder_lists_playlists_instead_of_failing(self):
        self.run_cli("new", "swift", "a")
        text = self.run_cli("play", "$0")
        self.assertIn("No playlist named", text)
        self.assertIn("swift", text)

    def test_errors_print_and_exit_zero_so_injection_is_not_aborted(self):
        self.assertIn("Playlist error", self.run_cli("play", "nope"))
        self.assertIn("Unknown mode", self.run_cli("play", "nope:loud"))

    def test_inline_includes_bodies_and_base_directory(self):
        skill(self.config, "a", body="Alpha rules.")
        self.run_cli("new", "pair", "a", "ghost", "--mode", "inline")
        text = self.run_cli("play", "pair")
        self.assertIn("Alpha rules.", text)
        self.assertIn(f'base-directory="{os.path.join(self.config, "skills", "a")}"', text)
        self.assertNotIn("description:", text)
        self.assertIn("1. ghost", text)  # not on disk, so deferred to the Skill tool rather than dropped

    def test_inline_defers_what_does_not_fit_and_says_so(self):
        skill(self.config, "big", body="x" * (pl.INLINE_BUDGET - 100))
        skill(self.config, "also-big", body="y" * 500)
        self.run_cli("new", "heavy", "big", "also-big")
        text = self.run_cli("play", "heavy:inline")
        self.assertIn("1 of 2 skills are included", text)
        self.assertIn("1. also-big", text)
        self.assertLess(len(text), 30000)

    def test_index_shows_descriptions_and_paths(self):
        skill(self.config, "a", description="Reviews SwiftUI code.")
        self.run_cli("new", "kit", "a")
        text = self.run_cli("play", "kit:index")
        self.assertIn("a: Reviews SwiftUI code.", text)
        self.assertIn(os.path.join(self.config, "skills", "a", "SKILL.md"), text)

    def test_folded_description_is_read(self):
        os.makedirs(os.path.join(self.config, "skills", "f"))
        path = os.path.join(self.config, "skills", "f", "SKILL.md")
        with open(path, "w") as fh:
            fh.write("---\nname: f\ndescription: >\n  First line\n  second line.\nlicense: MIT\n---\nbody")
        self.assertEqual(pl.read_description(path), "First line second line.")


class ManageTests(Sandbox):
    def test_project_playlist_shadows_global_and_lives_in_repo(self):
        self.run_cli("new", "kit", "global-skill")
        self.run_cli("new", "kit", "project-skill", "--project", "--force")
        self.assertTrue(os.path.exists(os.path.join(self.repo, ".claude", "playlists", "kit.json")))
        self.assertIn("project-skill", self.run_cli("play", "kit"))
        self.assertNotIn("global-skill", self.run_cli("play", "kit"))

    def test_new_refuses_to_overwrite_without_force(self):
        self.run_cli("new", "kit", "a")
        self.assertIn("already exists", self.run_cli("new", "kit", "b"))
        self.assertIn("1. a", self.run_cli("play", "kit"))

    def test_add_remove_delete(self):
        self.run_cli("new", "kit", "a", "b")
        self.run_cli("add", "kit", "c", "a")
        self.run_cli("remove", "kit", "b")
        self.assertIn("1. a\n2. c", self.run_cli("play", "kit"))
        self.run_cli("delete", "kit")
        self.assertIn("No playlists yet", self.run_cli("list"))

    def test_bad_name_is_rejected(self):
        self.assertIn("not a valid playlist name", self.run_cli("new", "../evil", "a"))
        self.assertEqual(os.listdir(self.tmp.name).count("evil.json"), 0)

    def test_plugin_skills_are_indexed_with_their_prefix(self):
        skill(self.config, "supabase", plugin="sb")
        os.makedirs(os.path.join(self.config, "plugins"), exist_ok=True)
        with open(os.path.join(self.config, "plugins", "installed_plugins.json"), "w") as fh:
            json.dump({"plugins": {"supabase@market": [
                {"installPath": os.path.join(self.config, "plugins", "cache", "sb")}]}}, fh)
        self.run_cli("new", "db", "supabase:supabase", "gone")
        report = self.run_cli("doctor")
        self.assertIn("db: 1/2 on disk; not found: gone", report)


class TranscriptTests(Sandbox):
    def write_session(self, name, lines, project="p"):
        d = os.path.join(self.config, "projects", project)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, name + ".jsonl"), "w") as fh:
            fh.write("\n".join(lines) + "\n")

    def test_save_session_captures_skills_in_first_use_order(self):
        self.write_session("s1", [
            line("user", "load my swift skills"),
            skill_call("swiftui-pro"), skill_call("supabase:supabase"), skill_call("workflow-authoring"),
            line("user", [{"type": "tool_result", "content": "ok"}]),
            skill_call("swift-testing"),
            line("assistant", [{"type": "tool_use", "name": "Skill", "input": {"skill": "sub"}}], isSidechain=True),
            line("user", "now this"),
            skill_call("swiftui-pro"),
        ])
        self.run_cli("save-session", "mine", "--session", "s1")
        text = self.run_cli("play", "mine")
        self.assertIn("1. swiftui-pro\n2. supabase:supabase\n3. swift-testing", text)  # exact ids, not collapsed
        self.assertNotIn("workflow-authoring", text)  # harness-loaded
        self.assertNotIn("4.", text)  # the sidechain (subagent) skill is not the user's

    def test_suggest_finds_a_repeated_set_and_skips_covered_or_dismissed(self):
        for i in range(3):
            self.write_session(f"s{i}", [line("user", "go"), skill_call("a"), skill_call("b"), skill_call("c")])
        self.write_session("noise", [line("user", "go"), skill_call("x"), skill_call("y")])
        found = pl.suggest()["suggestions"]
        self.assertEqual([s["skills"] for s in found], [["a", "b", "c"]])
        self.assertEqual(found[0]["turns"], 3)
        self.run_cli("suggest", "--dismiss", "1")
        self.assertEqual(pl.suggest()["suggestions"], [])

    def test_suggest_treats_plugin_copy_as_same_skill_but_returns_the_id_in_use(self):
        self.write_session("s0", [line("user", "go"), skill_call("a"), skill_call("sb")])
        for i in (1, 2):
            self.write_session(f"s{i}", [line("user", "go"), skill_call("a"), skill_call("sb:sb")])
        found = pl.suggest()["suggestions"]
        self.assertEqual([s["skills"] for s in found], [["a", "sb:sb"]])
        self.assertEqual(found[0]["turns"], 3)

    def test_suggest_skips_sets_an_existing_playlist_already_covers(self):
        for i in range(3):
            self.write_session(f"s{i}", [line("user", "go"), skill_call("a"), skill_call("b")])
        self.run_cli("new", "ab", "a", "b")
        self.assertEqual(pl.suggest()["suggestions"], [])

    def test_typed_builtin_commands_are_not_skills(self):
        skill(self.config, "real")
        for i in range(3):
            self.write_session(f"s{i}", [
                line("user", "<command-name>/model</command-name> <command-name>/real</command-name>"),
                skill_call("other")])
        self.assertEqual([s["skills"] for s in pl.suggest()["suggestions"]], [["other", "real"]])


class HookTests(Sandbox):
    def hook(self, prompt):
        return self.run_cli("hook", stdin=json.dumps({"prompt": prompt, "cwd": self.repo}))

    def test_token_anywhere_in_a_sentence_expands(self):
        self.run_cli("new", "swift", "a", "b")
        out = json.loads(self.hook("please review LoginView with @@swift before I commit"))
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")
        self.assertIn("1. a\n2. b", ctx)

    def test_silent_when_nothing_matches(self):
        self.run_cli("new", "swift", "a")
        for prompt in ("no tokens here", "email me at x@@swift", "@@unknown please", ""):
            self.assertEqual(self.hook(prompt), "", prompt)

    def test_never_raises_on_garbage_input(self):
        self.assertEqual(self.run_cli("hook", stdin="not json"), "")

    def test_inline_request_over_the_hook_cap_falls_back_to_invoke(self):
        skill(self.config, "big", body="x" * 20000)
        self.run_cli("new", "heavy", "big", "--mode", "inline")
        ctx = json.loads(self.hook("@@heavy go"))["hookSpecificOutput"]["additionalContext"]
        self.assertLess(len(ctx), 10000)
        self.assertIn("invoke mode", ctx)


if __name__ == "__main__":
    unittest.main()
