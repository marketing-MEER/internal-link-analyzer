<div align="center">

# 🕸️ internal-link-analyzer

### Orphan pages, click depth, broken internal links and internal PageRank from one crawl.

[![tests](https://github.com/marketing-MEER/internal-link-analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/marketing-MEER/internal-link-analyzer/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![No API keys](https://img.shields.io/badge/API%20keys-none%20needed-brightgreen)
[![Part of SEO Toolbox](https://img.shields.io/badge/part%20of-SEO%20Toolbox-orange)](https://github.com/marketing-MEER/seo-toolbox)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Meer%20Hamza-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/meerhamza-seo)

[🚀 Quick start](#quick-start) · [⚙️ How it works](#how-it-works) · [📄 Report](#report) · [❓ FAQ](#faq) · [👤 Author](#author)

</div>

---

## 💡 What it does

It crawls your site the way a search engine follows links, starting at the home page, and compares what it
finds with your sitemap. You get every page's click depth, how many pages link to it and its share of internal
PageRank, plus the pages nobody links to, links that hit redirects or 404s, and dead ends.

- ✅ Orphan pages (in the sitemap, never linked), pages deeper than 3 clicks, pages with a single inlink
- ✅ Internal links to 404s and redirects, nofollowed internal links, pages with no links out
- ✅ Optional: mark your money pages and add a GSC export to see which top-traffic pages don't link to them
- ✅ Free, MIT licensed, no API keys. Works with the exports you already have.

## 📊 Why this matters

> **Blog Posts Drive The Majority Of SEO Traffic** · NP Digital, November 2024
> - Blog posts account for 30% of total SEO traffic, the largest share of any page type.
> - Tools pages drive 15% of SEO traffic, ranking second overall.
>
> Data: [Neil Patel marketing stats](https://neilpatel.com/marketing-stats/which-page-type-drives-the-most-seo-traffic/)

**How internal-link-analyzer uses this:** one of the study's actionable insights is to build internal links from
high-traffic blog posts to commercial pages. With `--money` and `--traffic`, the tool lists your top-traffic pages
that don't link to any commercial page, and shows how deep and how well linked your money pages are. A second NP
Digital stat ([topic vs keyword SEO](https://neilpatel.com/marketing-stats/keyword-vs-topic-seo-performance/)) says
to use internal linking to reinforce topic authority, which is what inlinks and internal PageRank measure.

<a id="quick-start"></a>

## 🚀 Quick start

```bash
git clone https://github.com/marketing-MEER/internal-link-analyzer.git
cd internal-link-analyzer
pip install -e .
internal-link-analyzer https://www.example.com --money "/pricing|/product/" --traffic gsc_pages.csv
```

This writes **`internal_links_report.html`** (a formatted report you can open, share or print to PDF) and **`internal_links_report.xlsx`** (all the data).

> [!TIP]
> If the `internal-link-analyzer` command isn't found, use `python -m internal_link_analyzer`.

## 📥 Input

| Input | Required | How to get it |
|---|---|---|
| Domain or start URL | yes | The crawl starts here and stays on this host |
| `--sitemap` | no | Found in robots.txt or at `/sitemap.xml` automatically; used to find orphans |
| `--money` | no | A regex for your commercial URLs, e.g. `"/pricing|/demo|/product/"` |
| `--traffic` | no | GSC → Performance → Pages → Export (CSV or XLSX). Columns `Top pages`/`Page`/`URL` and `Clicks`/`Sessions` are found automatically |

<a id="how-it-works"></a>

## ⚙️ How it works

1. Reads robots.txt (and respects it), loads the sitemap, then crawls breadth-first from the start URL with
   its own user agent and at least 0.5 s between requests. Redirects are recorded, not silently followed.
2. Follows `<a href>` links on the same host. `rel="nofollow"` links are recorded but not followed. Images, PDFs and other files are skipped.
3. Click depth = the fewest clicks from the start page. Internal PageRank is classic PageRank (damping 0.85) over
   followed internal links, scaled so the strongest page is 100.
4. Flags (general best practice):

| Check | Severity |
|---|---|
| Orphan page: in the sitemap but never linked | error |
| Internal links to a 4xx/5xx page | error |
| Internal links to a redirect | warning |
| Indexable page more than 3 clicks deep | warning |
| Dead end: page with no internal links out | warning |
| Money page deeper than 2 clicks (with `--money`) | warning |
| Top 20% traffic page (non-money) that doesn't link to a money page (with `--money` and `--traffic`) | warning |
| Only one internal link points to the page | notice |
| Internal nofollow links | notice |

If the crawl stops at `--max-pages`, sitemap URLs it didn't reach are listed as "not reached" (notice) instead of orphans.

### Options

| Option | Default | What it does |
|---|---|---|
| `--sitemap` | from robots.txt | Sitemap URL to compare with |
| `--money` | | Regex for commercial pages |
| `--traffic` | | GSC Pages export with clicks |
| `--max-pages` | `500` | Most pages to crawl |
| `--delay` | `0.5` | Seconds between requests (never less than 0.5) |
| `-o`, `--output` | `internal_links_report` | File name for the report (`.html` + `.xlsx`) |

<a id="report"></a>

## 📄 The report

- **Cards**: pages, internal links, orphans, pages deeper than 3 clicks, broken link targets, max depth.
- **Benchmarks**: the two NP Digital stats, with source and link.
- **Issues** (`Issues` sheet): URL, severity, issue and detail, errors first.
- **Pages by internal PageRank** (`Pages` sheet): status, depth, inlinks, outlinks, PageRank, in sitemap, indexable, money page, links to a money page, clicks, title.
- **Orphan pages** (`Orphans`), **Pages per click depth** (`Depth`) and **All internal links** (`Links`, with anchor text and target status).

<details>
<summary>📄 Example: real output from <code>examples/</code></summary>

Run on the fictional site in `examples/site`
(`internal-link-analyzer http://localhost:8000 --money "/pricing" --traffic examples/gsc_pages.csv`):
9 pages, 21 links, 1 orphan, 1 page deeper than 3 clicks, 12 issues.

| url | severity | issue | detail |
|---|---|---|---|
| http://localhost:8000/case-studies.html | error | Internal links to a 404 page | 1 linking page(s), e.g. http://localhost:8000/pricing.html |
| http://localhost:8000/webinar.html | error | Orphan page | Only reachable from the sitemap |
| http://localhost:8000/features/reports/export/csv.html | warning | Dead end: no internal links out |  |
| http://localhost:8000/blog | warning | Internal links to a 301 page | 1 linking page(s), e.g. http://localhost:8000/ |
| http://localhost:8000/features/reports/export/csv.html | warning | More than 3 clicks from the home page | depth 4 |
| http://localhost:8000/blog/post-b.html | warning | Top-traffic page does not link to a money page | 1240 clicks; add a link to a commercial page |
| http://localhost:8000/login.html | notice | Internal nofollow links | 1 link(s) |
| http://localhost:8000/blog/post-a.html | notice | Only one internal link points here | 1 linking page(s) |
| http://localhost:8000/blog/post-b.html | notice | Only one internal link points here | 1 linking page(s) |
| http://localhost:8000/features/reports.html | notice | Only one internal link points here | 1 linking page(s) |
| http://localhost:8000/features/reports/export.html | notice | Only one internal link points here | 1 linking page(s) |
| http://localhost:8000/features/reports/export/csv.html | notice | Only one internal link points here | 1 linking page(s) |

Pages by internal PageRank:

| url | status | depth | inlinks | outlinks | pagerank | money page | links to money page | clicks |
|---|---|---|---|---|---|---|---|---|
| http://localhost:8000/ | 200 | 0 | 5 | 4 | 100 | no | yes | 280 |
| http://localhost:8000/features.html | 200 | 1 | 2 | 3 | 86.1 | no | yes | 40 |
| http://localhost:8000/pricing.html | 200 | 1 | 3 | 3 | 82.6 | yes | no | 95 |
| http://localhost:8000/features/reports.html | 200 | 2 | 1 | 2 | 32.9 | no | no |  |
| http://localhost:8000/blog/ | 200 | 2 | 2 | 3 | 30.2 | no | no |  |
| http://localhost:8000/features/reports/export.html | 200 | 3 | 1 | 2 | 22.4 | no | no |  |
| http://localhost:8000/features/reports/export/csv.html | 200 | 4 | 1 | 0 | 18 | no | no |  |
| http://localhost:8000/blog/post-a.html | 200 | 3 | 1 | 2 | 17 | no | yes | 310 |
| http://localhost:8000/blog/post-b.html | 200 | 3 | 1 | 1 | 17 | no | no | 1,240 |
| http://localhost:8000/admin/ | blocked by robots.txt | 1 | 1 | 0 | 0 | no | no |  |
| http://localhost:8000/blog | 301 | 1 | 1 | 0 | 0 | no | no |  |
| http://localhost:8000/case-studies.html | 404 | 2 | 1 | 0 | 0 | no | no |  |

</details>

## 🧰 More free SEO tools

This repo is one tool in the **[SEO Toolbox](https://github.com/marketing-MEER/seo-toolbox)**, a family of free, single-purpose SEO tools. Related:
- [topic-cluster-planner](https://github.com/marketing-MEER/topic-cluster-planner): plan pillar and spoke pages with an internal link plan
- [redirect-chain-fixer](https://github.com/marketing-MEER/redirect-chain-fixer): fix the redirects your internal links point to
- [robots-sitemap-validator](https://github.com/marketing-MEER/robots-sitemap-validator): robots.txt and XML sitemap checks
- [seo-workhorse](https://github.com/marketing-MEER/seo-workhorse): audit, clustering, redirects and GSC quick wins in one CLI

<a id="faq"></a>

## ❓ FAQ

<details><summary><b>Does it render JavaScript?</b></summary>

No. It reads the HTML the server sends. Links that only appear after JavaScript runs are not seen, which is
also a useful check: search engines find those links later, if at all.
</details>

<details><summary><b>Is internal PageRank the same as Google's?</b></summary>

No. It is the classic formula run on your internal links only. Use it to compare your own pages with each
other, for example to see whether your money pages get as much internal weight as your blog index.
</details>

<details><summary><b>Is my data sent anywhere?</b></summary>

No. Everything runs on your machine. The only requests are GETs to your own site (robots.txt, sitemap and
pages) with the user agent `internal-link-analyzer/1.0`. The traffic file is read locally.
</details>

## 🧪 Tests

```bash
python -m unittest discover -s tests -t . -v
```

## 📄 License

[MIT](LICENSE). Free for personal and commercial use. Benchmark figures © their original publishers and quoted with a link to the source.

<a id="author"></a>

## 👤 Author

**Meer Hamza** · SEO Team Lead · Berlin 🇩🇪
10+ years in SEO, AEO and GEO. I build small tools that take the spreadsheet work out of SEO.

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/meerhamza-seo)
[![Email](https://img.shields.io/badge/Email-meerhamza5%40gmail.com-D14836?logo=gmail&logoColor=white)](mailto:meerhamza5@gmail.com)

<div align="center">

**If this saved you time, a ⭐ helps other SEOs find it.**

</div>
