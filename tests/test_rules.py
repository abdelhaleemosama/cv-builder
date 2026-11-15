import unittest

from cvbuild.master import Master
from cvbuild.selection import blocking, resolve

from .support import MASTER_FILE, general

MASTER = Master(MASTER_FILE)


def found(**changes) -> list[str]:
    return resolve(MASTER, {**general(), **changes})[1]


class Refused(unittest.TestCase):
    def test_a_long_summary(self):
        self.assertTrue(any("keep it to 60" in p for p in blocking(found(summary=" ".join(["Engineer"] * 61)))))

    def test_a_skill_listed_twice_even_across_the_also_list(self):
        groups = [{"group": "A", "items": ["Go", "Kafka"]}, {"group": "B", "items": ["Python"], "also": ["kafka"]}]
        self.assertTrue(any("listed twice" in p for p in blocking(found(skills=groups))))

    def test_the_same_bullet_twice(self):
        self.assertTrue(any("appears twice" in p for p in blocking(found(experience=[{"id": "brightline", "items": ["releases", "releases"]}]))))

    def test_too_many_bold_keywords(self):
        keywords = ["Go", "Python", "Kafka", "Redis", "Docker", "AWS", "Rails", "gRPC", "Grafana", "Terraform", "TypeScript"]
        self.assertTrue(any("bold at most 10" in p for p in blocking(found(bold=keywords))))


class OnlyNotes(unittest.TestCase):
    """Judgment calls: shown, never blocking."""

    def test_a_bullet_without_a_number(self):
        items = [{"id": "dispatch-api", "text": "*Dispatch API:* moved the dispatch service to Go."}, "releases"]
        problems = found(experience=[{"id": "brightline", "items": items}])
        notes = [p for p in problems if p.startswith("note: no number")]
        self.assertEqual(len(notes), 1)
        self.assertEqual(blocking(problems), [])

    def test_bullets_that_open_with_the_same_word(self):
        items = [{"id": i, "text": f"*{i}:* built the {i} service, up **{n}x**."} for n, i in enumerate(["dispatch-api", "event-pipeline", "releases"], 2)]
        problems = found(experience=[{"id": "brightline", "items": items}])
        self.assertTrue(any("open with the same word: built (x3)" in p for p in problems))

    def test_a_phrase_repeated_across_bullets(self):
        phrase = "with idempotent writes and a dead-letter topic"
        items = [{"id": i, "text": f"*{i}:* ran it {phrase} for **{n}** teams."} for n, i in enumerate(["dispatch-api", "releases"], 2)]
        self.assertTrue(any("said in more than one bullet" in p for p in found(experience=[{"id": "brightline", "items": items}])))


if __name__ == "__main__":
    unittest.main()
