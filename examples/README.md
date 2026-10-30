# 📂 Examples

`site/` is a tiny made-up website for a fictional CRM brand (`PipelineHQ`). All names, pages and numbers are
invented. It has typical internal linking problems built in on purpose: an orphan page that is only in the
sitemap, a page four clicks deep with no links out, a link to a 404, a link that hits a redirect (`/blog`
without the slash), a nofollow internal link, a section blocked by robots.txt, and a high-traffic blog post
that never links to the pricing page.

`gsc_pages.csv` is a made-up Google Search Console "Pages" export for that site.

```bash
python -m http.server 8000 --directory examples/site
# in a second terminal:
internal-link-analyzer http://localhost:8000 --money "/pricing" --traffic examples/gsc_pages.csv
```

The sitemap and the traffic file use `http://localhost:8000`, so keep port 8000.
