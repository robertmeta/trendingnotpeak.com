# Trending Not Peak

The public story archive for a daily AI and developer podcast: twenty emerging
stories, around ten minutes, with original summaries and links to the evidence.

Read it at **https://robertmeta.github.io/trendingnotpeak.com/**.
The intended custom domain is `trendingnotpeak.com`; it has not been connected.

## Build

Python 3.10+ and Make are sufficient. No package installation or API keys.

```sh
make verify
make serve PORT=8765
```

Edit public records in `episodes/YYYY-MM-DD.json`, then run `make build`.
The builder writes the complete static site to `docs/`, including JSON downloads
and transcripts. Commit both the source and generated files. GitHub Pages serves
`main` → `/docs`; a push updates the site. There is no scheduled generation here.

## Public records

Each story retains an ID derived from its topic, its position, category, original
script, source links, selection rationale and dated observations. IDs stay stable
when titles are edited. Counts are historical snapshots; only a pair of suitable
observations can establish measured growth. Source samples cannot establish
global obscurity or guarantee that something will become popular.

Production tools live in a separate private repository. Only explicit public
fields are exported here. Do not add credentials, API configuration, original
article bodies, scraping caches, provider manifests, account information or logs.
Public availability of this repository does not relicense linked third-party work.

## Launch checklist

- [x] Generate and validate the full twenty-story October 29 Sarah voice preview.
- [ ] Complete human listening/editorial acceptance before directory launch.
- [x] Attach a validated MP3 through the record's `audio` field: `url` (absolute
  HTTPS), `duration_seconds`, and `bytes`. Audio is hosted separately from the
  Pages build so the daily archive does not consume the 1 GB published-site limit.
  The launch preview uses a GitHub Release asset; the record includes its SHA-256.
- [ ] Buy `trendingnotpeak.com`, verify ownership in GitHub, configure DNS and
  Pages' custom domain, and require HTTPS. Update `site.json` and rebuild only
  after the domain works. Do not add a `CNAME` before ownership is established.
- [ ] Confirm a real podcast owner/contact email, final square artwork, permanent
  media URLs, HEAD and byte-range support, and a validated podcast RSS feed.
  No podcast RSS feed or directory listing is advertised by this preview site.
- [ ] Submit and claim the same public RSS feed in Apple Podcasts, Spotify,
  Amazon Music and other directories; some require manual account verification.
- [ ] Complete end-to-end testing before enabling the private producer's
  04:00 America/New_York schedule. Nothing in this repository enables it.

GitHub Pages limits: [published site and bandwidth limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).
Podcast delivery requirements: [Apple Podcasts RSS requirements](https://podcasters.apple.com/support/823-podcast-requirements).

Thanks to Intelligrit for sponsoring this daily update.
