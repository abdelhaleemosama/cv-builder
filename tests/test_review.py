import unittest

from cvbuild import render
from cvbuild.master import Master
from cvbuild.match import keyword_report
from cvbuild.review import review_summary
from cvbuild.selection import resolve

from .support import MASTER_FILE, general

MASTER = Master(MASTER_FILE)


class RecruiterReview(unittest.TestCase):
    def test_only_real_quotes_count_as_evidence(self):
        cv_text = render.to_text(resolve(MASTER, general())[0])
        review = {
            "skim": {"keep_reading": True},
            "requirements": [
                {"requirement": "Go services", "level": "must", "evidence": "moved the dispatch   service from a Rails monolith to Go"},
                {"requirement": "Kubernetes", "level": "must", "evidence": None},
                {"requirement": "Elasticsearch", "level": "must", "evidence": "Operated Elasticsearch clusters in production"},
                {"requirement": "PostgreSQL", "level": "must", "evidence": "PostgreSQL", "weak": True},
                {"requirement": "Terraform", "level": "nice", "evidence": None},
            ],
            "findings": [
                {"severity": "must-fix", "kind": "presentation", "problem": "Go is buried"},
                {"severity": "must-fix", "kind": "gap", "problem": "No Elasticsearch"},
                {"severity": "optional", "kind": "presentation", "problem": "Long bullet"},
            ],
        }
        result = review_summary(review, cv_text)
        self.assertEqual((result["musts_proved"], result["musts"]), (2, 4), "Go and PostgreSQL are quoted from the CV")
        self.assertEqual(result["unproved"], ["Kubernetes", "Elasticsearch"])
        self.assertEqual(result["misquoted"], ["Elasticsearch"], "an invented quote is caught, not counted")
        self.assertEqual(result["weak"], ["PostgreSQL"])
        self.assertEqual([len(result[key]) for key in ("fixable", "gaps", "optional")], [1, 1, 1])

    def test_an_empty_review_is_harmless(self):
        result = review_summary({}, "anything")
        self.assertEqual((result["musts"], result["musts_proved"]), (0, 0))
        self.assertTrue(result["keep_reading"])


class JobMatch(unittest.TestCase):
    def test_three_buckets(self):
        selection = general()
        selection["skills"][3]["items"] = [item for item in selection["skills"][3]["items"] if item != "Terraform"]
        cv_text = render.to_text(resolve(MASTER, selection)[0])
        job = "We need Go, Kafka, Terraform and Elasticsearch. Experience with Flyway is a plus."
        report = keyword_report(job, cv_text, MASTER, ["Flyway"])
        self.assertEqual(report["covered"], ["Go", "Kafka"])
        self.assertEqual(report["addable"], ["Terraform"], "true, in the profile, but left off this CV")
        self.assertEqual(report["gaps"], ["Elasticsearch", "Flyway"], "real gaps: never to be added")


if __name__ == "__main__":
    unittest.main()
