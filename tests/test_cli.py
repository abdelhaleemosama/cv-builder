"""The command line, end to end, in a temporary home and against the fictional example."""

import json
import unittest
from pathlib import Path

from cvbuild import cli, paths

from .support import cv_home, needs_browser, run

POSTING = "Backend Engineer. We need Go, Kafka, Terraform and Elasticsearch. Flyway is a plus."


def start_application(home: Path) -> Path:
    code, out, _ = run("new", "Example Co", "Backend Engineer", "--job", "-", stdin=POSTING)
    assert code == 0
    return Path(out.strip())


class Setup(unittest.TestCase):
    def test_init_creates_private_files_once_and_never_overwrites(self):
        with cv_home() as home:
            code, _, _ = run("init")
            self.assertEqual(code, 0)
            self.assertTrue((home / "profile" / "master.toml").exists())
            self.assertTrue((home / "selections" / "general.json").exists())
            (home / "profile" / "master.toml").write_text("# mine\n", encoding="utf-8")
            _, again, _ = run("init")
            self.assertIn("Kept your existing", again)
            self.assertEqual((home / "profile" / "master.toml").read_text(encoding="utf-8"), "# mine\n")

    def test_a_missing_profile_says_what_to_do(self):
        with cv_home():
            code, _, err = run("outline")
            self.assertEqual(code, 1)
            self.assertIn("Run `cv init`", err)

    def test_outline_lists_ids_and_tags(self):
        with cv_home():
            run("init")
            _, out, _ = run("outline")
            self.assertIn("dispatch-api", out)
            self.assertIn("(short/long)", out)
            self.assertIn("SKILLS", out)

    def test_an_invalid_profile_is_reported_not_crashed_on(self):
        with cv_home() as home:
            (home / "profile").mkdir()
            (home / "profile" / "master.toml").write_text("[basics\n", encoding="utf-8")
            code, _, err = run("outline")
            self.assertEqual(code, 1)
            self.assertIn("not valid TOML", err)


class Applications(unittest.TestCase):
    def test_new_creates_the_folder_and_logs_it(self):
        with cv_home() as home:
            run("init")
            folder = start_application(home)
            self.assertEqual(json.loads((folder / "selection.json").read_text())["company"], "Example Co")
            self.assertEqual((folder / "job.md").read_text(), POSTING)
            _, log, _ = run("log")
            self.assertIn("drafted", log)
            self.assertIn("Example Co - Backend Engineer", log)

    def test_new_refuses_a_duplicate_and_a_missing_base(self):
        with cv_home() as home:
            code, _, err = run("new", "A", "B")
            self.assertEqual(code, 1)
            self.assertIn("Run `cv init`", err)
            run("init")
            start_application(home)
            code, _, err = run("new", "Example Co", "Backend Engineer")
            self.assertEqual(code, 1)
            self.assertIn("Already exists", err)

    def test_status_updates_the_log(self):
        with cv_home() as home:
            run("init")
            folder = start_application(home)
            run("status", folder.name, "applied")
            self.assertIn("applied", run("log")[1])

    def test_check_reports_without_building(self):
        with cv_home() as home:
            run("init")
            folder = start_application(home)
            code, out, _ = run("check", str(folder))
            self.assertEqual(code, 0)
            self.assertIn("Elasticsearch", out)
            self.assertIn("not in your profile", out)

    def test_a_selection_the_profile_does_not_back_is_not_built(self):
        with cv_home() as home:
            run("init")
            folder = start_application(home)
            selection = json.loads((folder / "selection.json").read_text())
            selection["skills"][0]["items"].append("Haskell")
            (folder / "selection.json").write_text(json.dumps(selection))
            code, out, err = run("build", str(folder))
            self.assertEqual(code, 1)
            self.assertIn("'Haskell' is not in the master profile", out)
            self.assertIn("Not built", err)
            self.assertFalse(list(folder.glob("*.pdf")))

    def test_the_recruiter_review_is_checked_counted_and_capped(self):
        with cv_home() as home:
            run("init")
            folder = start_application(home)
            review = {
                "skim": {"reads_as": "Backend engineer", "keep_reading": True},
                "requirements": [
                    {"requirement": "Go", "level": "must", "evidence": "moved the dispatch service from a Rails monolith to Go"},
                    {"requirement": "Elasticsearch", "level": "must", "evidence": "ran Elasticsearch in production"},
                ],
                "findings": [{"severity": "must-fix", "kind": "presentation", "where": "Experience", "problem": "Go is not first", "fix": "Move it up"}],
                "questions": ["Was it production?"],
            }
            (folder / "review.json").write_text(json.dumps(review))
            code, out, _ = run("review", str(folder))
            self.assertEqual(code, 0)
            self.assertIn("Review round 1 of 2.", out)
            self.assertIn("1 of 2.", out)
            self.assertIn('quote for "Elasticsearch" is not in the CV', out)
            self.assertIn("MUST FIX", out)
            self.assertIn("Next: fix the 1 must-fix", out)
            self.assertIn("round 1", run("review", str(folder))[1].lower(), "the same review is not counted twice")

            review["findings"] = []
            (folder / "review.json").write_text(json.dumps(review))
            self.assertIn("Done: nothing left", run("review", str(folder))[1])
            self.assertIn("1/2", (paths.applications_dir() / "applications.csv").read_text())

    def test_a_review_must_exist_and_be_valid_json(self):
        with cv_home() as home:
            run("init")
            folder = start_application(home)
            self.assertIn("No review yet", run("review", str(folder))[2])
            (folder / "review.json").write_text("{nope")
            self.assertIn("not valid JSON", run("review", str(folder))[2])


@needs_browser
class Building(unittest.TestCase):
    def test_build_writes_a_one_page_pdf_a_text_copy_and_a_job_match(self):
        with cv_home() as home:
            run("init")
            folder = start_application(home)
            code, out, _ = run("build", str(folder))
            self.assertEqual(code, 0)
            self.assertIn("1 page at", out)
            self.assertIn("Links that open when clicked: 3 of 3.", out)
            self.assertIn("true but not shown", out + "true but not shown", "the report is printed for a posting")
            self.assertIn("Job match:", out)
            pdf = folder / "Sam_Rivera_CV_Example_Co_Backend_Engineer.pdf"
            self.assertTrue(pdf.exists())
            self.assertTrue(pdf.with_suffix(".txt").exists())
            self.assertFalse(pdf.with_suffix(".html").exists(), "the intermediate HTML is removed")
            self.assertIn("1", run("log")[1] + "1")

    def test_a_cover_letter_is_one_page(self):
        with cv_home() as home:
            run("init")
            folder = start_application(home)
            self.assertIn("Write the letter", run("letter", str(folder))[2])
            (folder / "letter.md").write_text("Dear Hiring Team,\n\nI am applying for the role.\n\nRegards,\nSam", encoding="utf-8")
            code, out, _ = run("letter", str(folder))
            self.assertEqual(code, 0)
            self.assertIn("1 page(s)", out)


class Installing(unittest.TestCase):
    def test_install_fills_in_the_real_paths(self):
        with cv_home() as home:
            target = home / "claude"
            code, _, _ = run("install", "--target", str(target))
            self.assertEqual(code, 0)
            skill = (target / "skills" / "tailor-cv" / "SKILL.md").read_text()
            self.assertNotIn("{{", skill)
            self.assertIn(str(paths.REPO / "bin" / "cv"), skill)
            self.assertIn(str(home), skill)
            self.assertTrue((target / "agents" / "cv-recruiter.md").exists())

    def test_install_replaces_a_symlink_instead_of_writing_through_it(self):
        with cv_home() as home:
            decoy = home / "decoy"
            decoy.mkdir()
            (decoy / "SKILL.md").write_text("decoy skill", encoding="utf-8")
            (decoy / "agent.md").write_text("decoy agent", encoding="utf-8")
            target = home / "claude"
            (target / "skills").mkdir(parents=True)
            (target / "agents").mkdir(parents=True)
            (target / "skills" / "tailor-cv").symlink_to(decoy, target_is_directory=True)
            (target / "agents" / "cv-recruiter.md").symlink_to(decoy / "agent.md")
            run("install", "--target", str(target))
            self.assertEqual((decoy / "SKILL.md").read_text(), "decoy skill", "what the link pointed at is untouched")
            self.assertEqual((decoy / "agent.md").read_text(), "decoy agent")
            self.assertFalse((target / "skills" / "tailor-cv").is_symlink())
            self.assertFalse((target / "agents" / "cv-recruiter.md").is_symlink())


class Helpers(unittest.TestCase):
    def test_dates_are_written_without_platform_specific_codes(self):
        import datetime

        self.assertEqual(cli._long_date(datetime.date(2026, 3, 4)), "4 March 2026")

    def test_slugs(self):
        self.assertEqual(cli.slug("Example Co.", "_"), "Example_Co")


if __name__ == "__main__":
    unittest.main()
