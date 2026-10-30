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

For visual or interaction changes, also run `TNP_TEST_URL=https://your-site-root/`
`make test-journeys` with Playwright and Chromium already available to Node.
This optional browser check installs nothing. It navigates from the homepage to
the retained October 29 fixture, tests playback, filters, numbered and legacy
links, reloads and downloads at desktop/mobile widths. It retains the regression
for clicking the same story fragment after filtering. Screenshots and its JSON
result go to ignored `.cache/browser-journey/` (override `TNP_TEST_ARTIFACTS`).

## Public records

Daily pages use `/YYYY/MM/DD/`, with numbered story links such as
`/2026/10/29/#3` for the third story in the October 29 edition. Each story shows
its transcript, why it was picked, why it is early, what to watch and its source
links. Detailed dated counts expand separately. The story index and filters
help readers jump through a full edition.

Each story retains an ID derived from its topic, its position, category, original
script, source links, selection rationale and dated observations. IDs stay stable
when titles are edited. Counts are historical snapshots; only a pair of suitable
observations can establish measured growth. Source samples cannot establish
global obscurity or guarantee that something will become popular.
Existing `/episodes/YYYY-MM-DD/` URLs and topic-derived hash links still work;
their canonical URL points to the calendar page. Preserve story order in a
published edition so its numbered links continue to identify the same story.

## Visual identity

The site uses a pixel-art palette, original SVG illustration, stepped graph-arrow
logo and block borders. Smooth Avenir/system sans-serif lettering keeps headings,
navigation and story copy easy to read; the pixel font is reserved for small
numeric accents. Headings have no hard text shadow. The arrow's outlined amber
peak stays ahead of its mint tip. The reusable mark is [assets/mark.svg](assets/mark.svg).

[Pixelify Sans](https://github.com/google/fonts/tree/main/ofl/pixelifysans) is
bundled unmodified with its [SIL Open Font License](assets/fonts/OFL.txt).
No font CDN or frontend dependencies are required. Native audio controls,
visible keyboard focus and reduced-motion behavior are preserved.

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
  Its chaptered MP3 embeds the opening, twenty stories and closing (22 markers).
  Chapter menus require a player that supports MP3 chapters; native browser audio
  controls may not display them.
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
