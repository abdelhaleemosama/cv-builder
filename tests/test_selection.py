import copy
import unittest

from cvbuild.errors import ProfileError
from cvbuild.master import Master
from cvbuild.selection import blocking, resolve

from .support import MASTER_FILE, general

MASTER = Master(MASTER_FILE)


def problems(**changes) -> list[str]:
    return blocking(resolve(MASTER, {**general(), **changes})[1])


def reworded(bullet_id: str, text: str, entry: str = "brightline") -> list[str]:
    return problems(experience=[{"id": entry, "items": [{"id": bullet_id, "text": text}]}])


class TheExample(unittest.TestCase):
    def test_the_example_profile_and_selection_are_clean(self):
        self.assertEqual(MASTER.problems, [])
        self.assertEqual(resolve(MASTER, general())[1], [], "no problems and no notes")

    def test_a_missing_profile_says_how_to_create_one(self):
        with self.assertRaisesRegex(ProfileError, "Run `cv init`"):
            Master("/nonexistent/master.toml")


class OnlyWhatTheProfileBacks(unittest.TestCase):
    def test_unknown_bullet(self):
        found = problems(experience=[{"id": "brightline", "items": ["dispatch-api", "made-up"]}])
        self.assertEqual(len(found), 1)
        self.assertIn("no such bullet", found[0])

    def test_unknown_entry(self):
        self.assertIn("no 'nowhere' in the master profile", problems(experience=[{"id": "nowhere"}])[0])

    def test_a_skill_must_be_in_the_profile(self):
        found = problems(skills=[{"group": "Data", "items": ["Kafka", "Elasticsearch"]}])
        self.assertEqual(len(found), 1, "Kafka is backed; Elasticsearch is not")
        self.assertIn("'Elasticsearch' is not in the master profile", found[0])

    def test_a_skill_in_the_also_list_is_checked_too(self):
        found = problems(skills=[{"group": "Data", "items": ["Kafka"], "also": ["Elasticsearch"]}])
        self.assertTrue(any("'Elasticsearch'" in p for p in found))

    def test_rewording_is_allowed(self):
        self.assertEqual(reworded("dispatch-api", "*Dispatch API:* moved dispatch to Go; p95 latency fell from **840 ms to 120 ms**."), [])

    def test_a_reworded_bullet_cannot_gain_a_number(self):
        found = reworded("dispatch-api", "*Dispatch API:* p95 latency fell from 840 ms to 120 ms for 10000 users.")
        self.assertIn("10000", found[0])

    def test_a_reworded_bullet_cannot_borrow_another_bullets_number(self):
        found = reworded("dispatch-api", "*Dispatch API:* cut stuck shipments by 70%.")
        self.assertTrue(any("70" in p for p in found))

    def test_a_reworded_bullet_cannot_name_a_technology_the_profile_lacks(self):
        found = reworded("dispatch-api", "*Dispatch API:* Go services on Elasticsearch with Cassandra.")
        self.assertTrue(any("Cassandra" in p and "Elasticsearch" in p for p in found))

    def test_a_summary_may_only_reuse_figures_the_stored_summaries_state(self):
        self.assertEqual(problems(summary="Backend engineer with 4 years of experience in Go."), [])
        found = problems(summary="Backend engineer with 9 years of experience.")
        self.assertIn("any summary in the master profile", found[0])

    def test_a_number_from_a_bullet_does_not_back_a_claim_in_the_summary(self):
        # "9" appears in the profile as "9 partners"; it must not make "9 years" acceptable.
        self.assertTrue(problems(summary="Backend engineer with 9 years of experience."))
        self.assertTrue(problems(summary="Cut stuck shipments by 70% as a backend engineer."))

    def test_a_summary_cannot_name_a_technology_the_profile_lacks(self):
        self.assertTrue(any("Cassandra" in p for p in problems(summary="Backend engineer fluent in Go and Cassandra.")))

    def test_courses_and_certifications_must_exist(self):
        self.assertTrue(any("course 'Astrology'" in p for p in problems(education={"coursework": ["Algorithms", "Astrology"]})))
        self.assertTrue(any("no 'nope'" in p for p in problems(certifications=["aws-dev", "nope"])))

    def test_unknown_section(self):
        self.assertTrue(any("unknown section 'hobbies'" in p for p in problems(sections=["summary", "hobbies"])))


class Choosing(unittest.TestCase):
    def test_the_long_variant_uses_the_fuller_wording_and_blurb(self):
        selection = copy.deepcopy(general())
        selection["projects"] = [{"id": "tidewatch", "variant": "long", "items": ["checker"]}]
        doc, _ = resolve(MASTER, selection)
        projects = dict(doc["sections"])["projects"]
        self.assertIn("cannot send monitoring data", projects[0]["blurb"])

    def test_a_bullet_without_the_requested_wording_falls_back_with_a_note(self):
        _, found = resolve(MASTER, {**general(), "experience": [{"id": "brightline", "items": [{"id": "reliability", "variant": "long"}]}]})
        self.assertTrue(any(p.startswith("note:") and "no 'long' wording" in p for p in found))

    def test_keywords_are_bolded_once_and_never_inside_bold(self):
        doc, found = resolve(MASTER, {**general(), "bold": ["RabbitMQ", "Rails", "6 weeks"]})
        self.assertTrue(any("'RabbitMQ' is not in the master profile" in p for p in found), "cannot bold what is not there")
        text = "\n".join(b for name, content in doc["sections"] if name == "experience" for e in content for b in e["bullets"])
        self.assertEqual(text.count("**Rails**"), 1)
        self.assertNotIn("****", text)

    def test_omitted_sections_are_left_out(self):
        doc, _ = resolve(MASTER, {**general(), "sections": ["summary", "skills"]})
        self.assertEqual([name for name, _ in doc["sections"]], ["summary", "skills"])


if __name__ == "__main__":
    unittest.main()
