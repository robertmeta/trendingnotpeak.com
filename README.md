# Trending Not Peak

The public story archive for a daily AI and developer podcast: twenty emerging
stories, around ten minutes, with original summaries and links to the evidence.

Read it at **https://robertmeta.github.io/trendingnotpeak.com/**.

## Build

Python 3.10+ and Make are sufficient. No package installation or API keys.

```sh
make verify
make serve PORT=8765
```

Edit public records in `episodes/YYYY-MM-DD.json`, then run `make build`.
The builder writes the complete static site to `docs/`, including JSON downloads
and transcripts. Commit both the source and generated files. GitHub Pages serves
`main` → `/docs`; a push updates the site.

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

This repository contains public story records and website source. Do not add
credentials, account information, internal operational notes, or original
third-party article bodies.
Public availability of this repository does not relicense linked third-party work.

Thanks to Intelligrit for sponsoring this daily update.
