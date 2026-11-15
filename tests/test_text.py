import unittest

from cvbuild.text import bold_terms, numbers_in, plain, squash
from cvbuild.vocabulary import has_term, terms_in


class WholeTerms(unittest.TestCase):
    def test_a_term_must_stand_alone(self):
        self.assertFalse(has_term("We use JavaScript", "Java"))
        self.assertTrue(has_term("Java, Spring", "Java"))
        self.assertFalse(has_term("C++ and C#", "C"))
        self.assertTrue(has_term("C, C++", "C"))

    def test_short_terms_are_case_sensitive(self):
        self.assertFalse(has_term("go beyond the brief", "Go"))
        self.assertTrue(has_term("Go or Rust", "Go"))

    def test_aliases_map_to_one_name(self):
        self.assertEqual(terms_in("Postgres, K8s and NodeJS"), {"PostgreSQL", "Kubernetes", "Node.js"})

    def test_extra_keywords_count_when_present(self):
        self.assertEqual(terms_in("We use Flyway and Go", ["Flyway", "Liquibase"]), {"Flyway", "Go"})


class Markup(unittest.TestCase):
    def test_plain_drops_emphasis_and_link_targets(self):
        self.assertEqual(plain("*Lead:* **9** partners via [the docs](https://example.com/x)"), "Lead: 9 partners via the docs")

    def test_squash_compares_quotes_loosely(self):
        self.assertEqual(squash("Built  **6+**\nservices"), "built 6+ services")

    def test_numbers(self):
        self.assertEqual(numbers_in("cut p95 from 840 ms to 120 ms; 1,200 users; 95.5%"), {"95", "840", "120", "1200", "95.5"})


class Bolding(unittest.TestCase):
    def test_first_appearance_only_and_remembered_across_calls(self):
        used: set[str] = set()
        first = bold_terms("Built on Kafka. More Kafka.", ["Kafka"], used)
        self.assertEqual(first, "Built on **Kafka**. More Kafka.")
        self.assertEqual(bold_terms("Kafka again", ["Kafka"], used), "Kafka again")

    def test_never_inside_bold_or_a_link_label(self):
        used: set[str] = set()
        self.assertEqual(bold_terms("**Kafka** and [Kafka docs](https://example.com)", ["Kafka"], used), "**Kafka** and [Kafka docs](https://example.com)")

    def test_whole_words_only(self):
        self.assertEqual(bold_terms("JavaScript", ["Java"], set()), "JavaScript")


if __name__ == "__main__":
    unittest.main()
