import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cvbuild import render
from cvbuild.errors import RenderError
from cvbuild.master import Master
from cvbuild.selection import resolve

from .support import MASTER_FILE, general, needs_browser

MASTER = Master(MASTER_FILE)
DOC = resolve(MASTER, general())[0]


class Markup(unittest.TestCase):
    def test_bold_italic_and_links(self):
        self.assertEqual(
            render.inline("*Lead:* **9** partners, see [docs](https://example.com/a?b=1&c=2)"),
            '<em>Lead:</em> <strong>9</strong> partners, see <a href="https://example.com/a?b=1&amp;c=2">docs</a>',
        )

    def test_text_is_escaped(self):
        self.assertEqual(render.inline("a <script>alert(1)</script> & b"), "a &lt;script&gt;alert(1)&lt;/script&gt; &amp; b")

    def test_a_link_target_cannot_break_out_of_its_attribute(self):
        out = render.inline('[x](https://example.com/" onmouseover="alert(1))')
        self.assertNotIn("<a ", out, "a target with a quote is not turned into a link at all")

    def test_only_web_and_mail_links(self):
        self.assertNotIn("<a ", render.inline("[x](javascript:alert(1))"))


class Document(unittest.TestCase):
    def test_header_links_are_real_links(self):
        body = render.body_html(DOC)
        self.assertIn('href="mailto:sam.rivera@example.com"', body)
        self.assertIn('href="https://example.com/in/sam-rivera"', body)

    def test_a_project_name_links_when_the_profile_has_a_url(self):
        self.assertIn('<a href="https://example.com/tidewatch"><strong>Tidewatch</strong></a>', render.body_html(DOC))

    def test_the_also_list_follows_a_semicolon(self):
        self.assertIn("PostgreSQL, Redis, Kafka; materialized views", render.body_html(DOC))
        self.assertIn("Data and Messaging: PostgreSQL, Redis, Kafka, materialized views", render.to_text(DOC))

    def test_the_text_version_carries_no_markup(self):
        text = render.to_text(DOC)
        self.assertNotIn("*", text)
        self.assertNotIn("](", text)
        self.assertIn("Sam Rivera".upper(), text)


class Browser(unittest.TestCase):
    def test_a_missing_browser_is_a_clear_error(self):
        with (
            tempfile.TemporaryDirectory() as folder,
            mock.patch.object(render, "find_browser", return_value=None),
            self.assertRaisesRegex(RenderError, "CV_BROWSER"),
        ):
            render.print_pdf(Path(folder) / "a.html", Path(folder) / "a.pdf")

    def test_an_override_wins(self):
        with mock.patch.dict("os.environ", {"CV_BROWSER": "/bin/sh"}):
            self.assertEqual(render.find_browser(), "/bin/sh")


@needs_browser
class Pdf(unittest.TestCase):
    def test_one_page_filled_with_working_links(self):
        with tempfile.TemporaryDirectory() as folder:
            pdf = Path(folder) / "cv.pdf"
            pages, size = render.build_pdf(render.body_html(DOC), "Sam Rivera - CV", pdf)
            self.assertEqual(pages, 1)
            self.assertIn(size, render.SIZES)
            links = render.links_in(pdf)
            self.assertLessEqual({"mailto:sam.rivera@example.com", "https://example.com/in/sam-rivera", "https://example.org/sam-rivera"}, links)

    def test_more_content_means_smaller_type(self):
        selection = general()
        selection["variant"] = "long"
        with tempfile.TemporaryDirectory() as folder:
            small, big = Path(folder) / "a.pdf", Path(folder) / "b.pdf"
            _, size_default = render.build_pdf(render.body_html(DOC), "t", small)
            body = render.body_html(DOC) + "<p>" + "extra words " * 400 + "</p>"
            pages, size_crowded = render.build_pdf(body, "t", big)
            self.assertLess(size_crowded, size_default)
            self.assertGreaterEqual(pages, 1)


if __name__ == "__main__":
    unittest.main()
