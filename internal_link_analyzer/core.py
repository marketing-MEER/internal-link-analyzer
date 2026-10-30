"""Crawl a site's internal links: click depth, orphan pages, inlinks and internal PageRank.

General best practice: important pages within 3 clicks of the home page, every indexable page linked at least
once (pages only in the sitemap are orphans), no internal links to redirects or errors.
NP Digital (which-page-type-drives-the-most-seo-traffic): "Build internal links from high-traffic blog posts
to commercial pages to transfer SEO equity efficiently." With --money and --traffic the tool checks exactly that.
"""
import re
import time
from collections import deque
from urllib import robotparser
from urllib.parse import urldefrag, urljoin, urlsplit, urlunsplit
from xml.etree import ElementTree

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .report import find_column, to_number

USER_AGENT = "internal-link-analyzer/1.0 (+https://github.com/marketing-MEER/internal-link-analyzer)"
MAX_DEPTH_OK = 3
PAGE_COLS = ["url", "status", "depth", "inlinks", "outlinks", "pagerank", "in_sitemap", "indexable",
             "money_page", "links_to_money_page", "clicks", "title"]
SKIP_EXT = re.compile(r"\.(?:jpe?g|png|gif|webp|svg|pdf|zip|mp4|mp3|css|js|ico|xml|txt)$", re.I)


def norm(url: str) -> str:
    url = urldefrag(url.strip())[0]
    p = urlsplit(url)
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or "/", p.query, ""))


class Fetcher:
    """Polite GETs: own user agent, at least 0.5 s between requests, redirects not followed."""

    def __init__(self, delay=0.5, timeout=20, session=None):
        self.delay, self.timeout = max(delay, 0.5), timeout
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self._last, self.requests = 0.0, 0

    def get(self, url):
        wait = self.delay - (time.monotonic() - self._last)
        if wait > 0 and self.requests:
            time.sleep(wait)
        self._last = time.monotonic()
        self.requests += 1
        try:
            return self.session.get(url, timeout=self.timeout, allow_redirects=False)
        except requests.RequestException as exc:
            return exc


def sitemap_urls(url, fetch, depth=0):
    resp = fetch.get(url)
    if isinstance(resp, Exception) or resp.status_code != 200:
        return []
    try:
        root = ElementTree.fromstring(resp.content)
    except ElementTree.ParseError:
        return []
    locs = [e.text.strip() for e in root.iter() if e.tag.endswith("loc") and e.text]
    if root.tag.endswith("sitemapindex") and depth < 2:
        return [u for loc in locs for u in sitemap_urls(loc, fetch, depth + 1)]
    return locs


def crawl(start: str, fetch: Fetcher, max_pages=500, sitemap=None):
    """Breadth-first crawl of one host. Returns (pages dict, links list, sitemap URL list)."""
    if not re.match(r"^https?://", start, re.I):
        start = "https://" + start
    host = urlsplit(start).netloc.lower()
    base = f"{urlsplit(start).scheme}://{host}"
    robots = robotparser.RobotFileParser()
    resp = fetch.get(base + "/robots.txt")
    robots.parse(resp.text.splitlines() if not isinstance(resp, Exception) and resp.status_code == 200 else [])
    smaps = [sitemap] if sitemap else (list(robots.site_maps() or []) or [base + "/sitemap.xml"])
    in_sitemap = list(dict.fromkeys(norm(u) for sm in smaps for u in sitemap_urls(sm, fetch)
                                    if urlsplit(u).netloc.lower() == host))
    pages, links = {}, []
    queue, depth = deque([norm(start)]), {norm(start): 0}
    while queue and len(pages) < max_pages:
        url = queue.popleft()
        if not robots.can_fetch(USER_AGENT, url):
            pages[url] = {"url": url, "status": "blocked by robots.txt", "depth": depth[url], "location": "",
                          "noindex": False, "canonical": "", "title": ""}
            continue
        r = fetch.get(url)
        info = {"url": url, "depth": depth[url], "location": "", "noindex": False, "canonical": "", "title": ""}
        if isinstance(r, Exception):
            info["status"] = "failed"
            pages[url] = info
            continue
        info["status"] = r.status_code
        if r.is_redirect:
            info["location"] = norm(urljoin(url, r.headers.get("Location", "")))
        pages[url] = info
        targets = [info["location"]] if info["location"] else []
        if r.status_code == 200 and "html" in r.headers.get("Content-Type", "text/html"):
            soup = BeautifulSoup(r.text, "html.parser")
            info["title"] = soup.title.get_text(strip=True)[:120] if soup.title else ""
            meta = soup.find("meta", attrs={"name": re.compile("^robots$", re.I)})
            info["noindex"] = bool(meta and "noindex" in (meta.get("content") or "").lower())
            can = soup.find("link", rel="canonical", href=True)
            info["canonical"] = norm(urljoin(url, can["href"])) if can else ""
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                if href.startswith(("mailto:", "tel:", "javascript:", "#")):
                    continue
                target = norm(urljoin(url, href))
                if urlsplit(target).netloc.lower() != host or SKIP_EXT.search(urlsplit(target).path):
                    continue
                nofollow = "nofollow" in [x.lower() for x in (a.get("rel") or [])]
                links.append({"source": url, "target": target, "anchor": a.get_text(" ", strip=True)[:80],
                              "nofollow": "yes" if nofollow else "no"})
                if not nofollow:
                    targets.append(target)
        for t in targets:
            if t not in depth:
                depth[t] = depth[url] + 1
                queue.append(t)
    return pages, links, in_sitemap


def pagerank(nodes, edges, damping=0.85, iterations=40):
    """Plain PageRank over internal followed links, scaled so the top page is 100."""
    nodes = list(nodes)
    if not nodes:
        return {}
    out = {n: [] for n in nodes}
    for s, t in edges:
        if s in out and t in out and s != t:
            out[s].append(t)
    pr = {n: 1 / len(nodes) for n in nodes}
    for _ in range(iterations):
        dangling = sum(pr[n] for n in nodes if not out[n])
        new = {n: (1 - damping) / len(nodes) + damping * dangling / len(nodes) for n in nodes}
        for s, ts in out.items():
            for t in ts:
                new[t] += damping * pr[s] / len(ts)
        pr = new
    top = max(pr.values())
    return {n: round(100 * v / top, 1) for n, v in pr.items()}


def load_traffic(path) -> dict:
    """URL -> clicks from a GSC 'Pages' export (or any CSV/XLSX with a URL and a clicks/sessions column)."""
    df = pd.read_excel(path) if str(path).lower().endswith((".xlsx", ".xls")) else pd.read_csv(path)
    url_col = find_column(df, ["top pages", "page", "url", "landing page", "address"]) or df.columns[0]
    val_col = find_column(df, ["clicks", "sessions", "traffic", "visits", "users"])
    if val_col is None:
        raise ValueError("No clicks/sessions column found in the traffic file")
    return dict(zip(df[url_col].astype(str).map(norm), to_number(df[val_col])))


def analyse(pages, links, in_sitemap, money_pattern=None, traffic=None, limit_hit=False):
    link_df = pd.DataFrame(links, columns=["source", "target", "anchor", "nofollow"])
    if not pages:  # nothing crawled: return empty frames with their columns (pandas 2 trips on empty groupbys)
        return {"pages": pd.DataFrame(columns=PAGE_COLS), "links": link_df.assign(target_status=None),
                "orphans": pd.DataFrame([{"url": u, "reason": "Site could not be crawled"} for u in in_sitemap],
                                        columns=["url", "reason"]),
                "issues": pd.DataFrame(columns=["url", "severity", "issue", "detail"]),
                "depth": pd.DataFrame(columns=["depth", "pages"])}
    status = {u: p["status"] for u, p in pages.items()}
    link_df["target_status"] = link_df["target"].map(lambda t: status.get(t, "not crawled"))
    ok = [u for u, p in pages.items() if p["status"] == 200]
    followed = link_df[link_df["nofollow"] == "no"]
    unique = followed[followed["source"] != followed["target"]].drop_duplicates(["source", "target"])
    pr = pagerank(ok, unique[["source", "target"]].itertuples(index=False, name=None))
    inlinks = unique.groupby("target")["source"].nunique()
    outlinks = unique.groupby("source")["target"].nunique()
    money = re.compile(money_pattern, re.I) if money_pattern else None
    traffic = traffic or {}
    links_to_money = {s for s, t in zip(unique["source"], unique["target"]) if money and money.search(t)}
    rows = []
    for u, p in pages.items():
        rows.append({"url": u, "status": p["status"], "depth": p["depth"], "inlinks": int(inlinks.get(u, 0)),
                     "outlinks": int(outlinks.get(u, 0)), "pagerank": pr.get(u, 0.0),
                     "in_sitemap": "yes" if u in set(in_sitemap) else "no",
                     "indexable": "yes" if p["status"] == 200 and not p["noindex"] and
                     (not p["canonical"] or p["canonical"] == u) else "no",
                     "money_page": "yes" if money and money.search(u) else "no",
                     "links_to_money_page": "yes" if u in links_to_money else "no",
                     "clicks": traffic.get(u, None), "title": p["title"]})
    page_df = pd.DataFrame(rows, columns=PAGE_COLS)
    crawled = set(pages)
    reason = ("Not reached before the crawl limit (raise --max-pages)" if limit_hit
              else "In the sitemap but no internal link found")
    orphans = pd.DataFrame([{"url": u, "reason": reason}
                            for u in in_sitemap if u not in crawled], columns=["url", "reason"])
    issues = []

    def add(url, severity, issue, detail=""):
        issues.append({"url": url, "severity": severity, "issue": issue, "detail": detail})

    for u in orphans["url"]:
        if limit_hit:
            add(u, "notice", "Sitemap URL not reached", "Crawl limit hit; it may still be linked")
        else:
            add(u, "error", "Orphan page", "Only reachable from the sitemap")
    for r in page_df.to_dict("records"):
        if r["status"] != 200:
            continue
        if r["depth"] > MAX_DEPTH_OK and r["indexable"] == "yes":
            add(r["url"], "warning", f"More than {MAX_DEPTH_OK} clicks from the home page", f"depth {r['depth']}")
        if r["inlinks"] <= 1 and r["depth"] > 0 and r["indexable"] == "yes":
            add(r["url"], "notice", "Only one internal link points here", f"{r['inlinks']} linking page(s)")
        if r["outlinks"] == 0:
            add(r["url"], "warning", "Dead end: no internal links out")
        if r["money_page"] == "yes" and r["depth"] > 2:
            add(r["url"], "warning", "Money page is deep", f"depth {r['depth']}; aim for 1-2 clicks")
    bad = link_df[link_df["target_status"].map(lambda s: isinstance(s, int) and s != 200).astype(bool)]
    for t, g in bad.groupby("target"):
        s = g["target_status"].iloc[0]
        add(t, "error" if s >= 400 else "warning", f"Internal links to a {s} page",
            f"{g['source'].nunique()} linking page(s), e.g. {g['source'].iloc[0]}")
    nf = link_df[link_df["nofollow"] == "yes"]
    for t, g in nf.groupby("target"):
        add(t, "notice", "Internal nofollow links", f"{len(g)} link(s)")
    if money and traffic:
        with_clicks = page_df[(page_df["clicks"].fillna(0) > 0) & (page_df["money_page"] == "no")]
        top = with_clicks.sort_values("clicks", ascending=False).head(max(1, round(len(with_clicks) * 0.2)))
        for r in top[top["links_to_money_page"] == "no"].to_dict("records"):
            add(r["url"], "warning", "Top-traffic page does not link to a money page",
                f"{int(r['clicks'])} clicks; add a link to a commercial page")
    sev = {"error": 0, "warning": 1, "notice": 2}
    issue_df = pd.DataFrame(issues, columns=["url", "severity", "issue", "detail"])
    if not issue_df.empty:
        issue_df = issue_df.assign(_r=issue_df["severity"].map(sev)).sort_values(["_r", "issue", "url"]) \
            .drop(columns="_r").reset_index(drop=True)
    depth_df = (page_df[page_df["status"] == 200].groupby("depth").size().reset_index(name="pages")
                if not page_df.empty else pd.DataFrame(columns=["depth", "pages"]))
    page_df = page_df.sort_values(["pagerank", "url"], ascending=[False, True]).reset_index(drop=True)
    return {"pages": page_df, "links": link_df, "orphans": orphans, "issues": issue_df, "depth": depth_df}


def audit(start, delay=0.5, max_pages=500, sitemap=None, money=None, traffic_file=None, fetch=None):
    fetch = fetch or Fetcher(delay=delay)
    pages, links, in_sitemap = crawl(start, fetch, max_pages=max_pages, sitemap=sitemap)
    traffic = load_traffic(traffic_file) if traffic_file else None
    out = analyse(pages, links, in_sitemap, money_pattern=money, traffic=traffic,
                  limit_hit=len(pages) >= max_pages)
    out["requests"] = fetch.requests
    out["sitemap_urls"] = len(in_sitemap)
    return out
