"""Command line entry point: `internal-link-analyzer DOMAIN`."""
from pathlib import Path

import click

from . import __version__, core
from .benchmark import STATS
from .report import Report, write_excel


@click.command()
@click.argument("site")
@click.option("--sitemap", default=None, help="Sitemap URL (default: from robots.txt, else /sitemap.xml).")
@click.option("--money", default=None, help="Regex for commercial pages, e.g. '/pricing|/product/'.")
@click.option("--traffic", "traffic_file", default=None, type=click.Path(exists=True),
              help="GSC Pages export (CSV/XLSX) with clicks, to check that top pages link to money pages.")
@click.option("--max-pages", default=500, show_default=True, help="Most pages to crawl.")
@click.option("--delay", default=0.5, show_default=True, help="Seconds between requests (min 0.5).")
@click.option("-o", "--output", default="internal_links_report", show_default=True,
              help="Report name; writes <name>.html and <name>.xlsx")
@click.version_option(__version__)
def main(site, sitemap, money, traffic_file, max_pages, delay, output):
    """Crawl SITE's internal links: click depth, orphans, inlinks and internal PageRank.

    Built by Meer Hamza - linkedin.com/in/meerhamza-seo
    """
    click.echo(f"Crawling {site} ...")
    r = core.audit(site, delay=delay, max_pages=max_pages, sitemap=sitemap, money=money, traffic_file=traffic_file)
    pages, issues = r["pages"], r["issues"]
    ok = pages[pages["status"] == 200] if not pages.empty else pages
    deep = int((ok["depth"] > core.MAX_DEPTH_OK).sum()) if not ok.empty else 0
    broken = int(issues["issue"].str.startswith("Internal links to a 4").sum()) if not issues.empty else 0
    report = Report(title="Internal link report",
                    subtitle=f"{site} · {len(pages)} URLs crawled · {r['requests']} requests",
                    tool="internal-link-analyzer")
    report.add_cards([("Pages (200)", len(ok)), ("Internal links", len(r["links"])),
                      ("Orphan pages", len(r["orphans"]), "bad" if len(r["orphans"]) else "good"),
                      (f"Deeper than {core.MAX_DEPTH_OK} clicks", deep, "warn" if deep else "good"),
                      ("Broken link targets", broken, "bad" if broken else "good"),
                      ("Max click depth", int(ok["depth"].max()) if not ok.empty else 0)])
    report.add_benchmark(STATS[0], how_used="NP Digital's insight: build internal links from high-traffic blog "
                         "posts to commercial pages. With --money and --traffic the report lists top pages that "
                         "don't link to a commercial page, and how deep and well-linked your money pages are.")
    report.add_benchmark(STATS[1], how_used="Topic-focused content beat keyword-focused content in every year of "
                         "the study, and NP Digital says to use internal linking to reinforce topic authority. "
                         "Inlinks and internal PageRank show which pages your structure actually supports.")
    report.add_table("Issues", issues, sheet="Issues")
    report.add_table("Pages by internal PageRank", pages, sheet="Pages",
                     note="PageRank is computed on followed internal links only and scaled so the top page = 100.")
    report.add_table("Orphan pages", r["orphans"], sheet="Orphans")
    report.add_table("Pages per click depth", r["depth"], sheet="Depth")
    report.add_table("All internal links", r["links"], sheet="Links")

    html_path = report.save_html(Path(output).with_suffix(".html"))
    xlsx_path = write_excel(report.sheets, Path(output).with_suffix(".xlsx"))
    click.secho(f"Report: {html_path}\nData:   {xlsx_path}", fg="green", bold=True)
    click.echo(f"{len(ok)} pages, {len(r['links'])} links, {len(r['orphans'])} orphans, {deep} deeper than "
               f"{core.MAX_DEPTH_OK} clicks, {len(issues)} issues")


if __name__ == "__main__":
    main()
