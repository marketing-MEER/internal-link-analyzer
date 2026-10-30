import functools
import http.server
import os
import shutil
import tempfile
import threading
import unittest
from pathlib import Path

from click.testing import CliRunner

from internal_link_analyzer import cli, core

EXAMPLES = Path(__file__).parent.parent / "examples"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class PageRankTest(unittest.TestCase):
    def test_hub_gets_top_score(self):
        pr = core.pagerank(["a", "b", "c"], [("b", "a"), ("c", "a"), ("a", "b")])
        self.assertEqual(pr["a"], 100.0)
        self.assertGreater(pr["b"], pr["c"])

    def test_empty(self):
        self.assertEqual(core.pagerank([], []), {})

    def test_norm(self):
        self.assertEqual(core.norm("HTTP://X.com#top"), "http://x.com/")
        self.assertEqual(core.norm("https://x.com/a?b=1#c"), "https://x.com/a?b=1")

    def test_analyse_empty(self):
        out = core.analyse({}, [], [])
        self.assertTrue(out["pages"].empty and out["issues"].empty and out["orphans"].empty)

    def test_single_page_without_links(self):
        page = {"url": "http://x/", "status": 200, "depth": 0, "location": "", "noindex": False,
                "canonical": "", "title": "t"}
        out = core.analyse({"http://x/": page}, [], ["http://x/a"])
        self.assertEqual(set(out["issues"]["issue"]), {"Orphan page", "Dead end: no internal links out"})


class ExampleSiteTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name) / "site"
        shutil.copytree(EXAMPLES / "site", root)
        cls.server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(root)))
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        for f in list(root.rglob("*.xml")) + list(root.rglob("*.txt")):
            f.write_text(f.read_text(encoding="utf-8").replace("http://localhost:8000", cls.base), encoding="utf-8")
        cls.traffic = Path(cls.tmp.name) / "gsc.csv"
        cls.traffic.write_text((EXAMPLES / "gsc_pages.csv").read_text(encoding="utf-8")
                               .replace("http://localhost:8000", cls.base), encoding="utf-8")
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def test_audit(self):
        r = core.audit(self.base, money="/pricing", traffic_file=str(self.traffic))
        pages = r["pages"].set_index("url")
        b = self.base
        self.assertEqual(list(r["orphans"]["url"]), [b + "/webinar.html"])
        self.assertEqual(pages.loc[b + "/features/reports/export/csv.html", "depth"], 4)
        self.assertEqual(pages.loc[b + "/", "pagerank"], 100.0)
        self.assertEqual(pages.loc[b + "/admin/", "status"], "blocked by robots.txt")
        self.assertEqual(pages.loc[b + "/pricing.html", "money_page"], "yes")
        issues = {(i["url"], i["issue"]) for i in r["issues"].to_dict("records")}
        self.assertIn((b + "/case-studies.html", "Internal links to a 404 page"), issues)
        self.assertIn((b + "/blog", "Internal links to a 301 page"), issues)
        self.assertIn((b + "/blog/post-b.html", "Top-traffic page does not link to a money page"), issues)
        self.assertNotIn((b + "/blog/post-a.html", "Top-traffic page does not link to a money page"), issues)
        self.assertIn((b + "/login.html", "Internal nofollow links"), issues)
        self.assertNotIn(b + "/login.html", pages.index)  # nofollow links are not followed

    def test_crawl_limit_softens_orphans(self):
        r = core.audit(self.base, max_pages=3)
        self.assertTrue(r["orphans"]["reason"].str.startswith("Not reached").all())
        self.assertNotIn("Orphan page", set(r["issues"]["issue"]))

    def test_cli(self):
        runner = CliRunner()
        with runner.isolated_filesystem():
            res = runner.invoke(cli.main, [self.base, "-o", "out"])
            self.assertEqual(res.exit_code, 0, res.output)
            self.assertTrue(os.path.exists("out.html") and os.path.exists("out.xlsx"))


if __name__ == "__main__":
    unittest.main()
