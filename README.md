# Trending Not Peak

The public story archive for a daily AI and developer podcast: twenty emerging
stories, around ten minutes, with original summaries and links to the evidence.

Read it at **https://trendingnotpeak.com/**.

Subscribe in your podcast app with [the RSS feed](https://trendingnotpeak.com/feed.xml).
The feed includes episode audio, source notes, transcripts and chapters.

## Build

Python 3.10+ and Make are sufficient. No package installation or API keys.

```sh
make verify
make serve PORT=8765
```

Edit public records in `episodes/YYYY-MM-DD.json`, then run `make build`.
The builder writes the complete static site to `docs/`, including JSON downloads
and transcripts. Podcast metadata lives in `podcast.json`; it retains the show ID
and each edition's original publication timestamp. The feed uses the audio URLs
and byte counts from the public episode records. Commit both the source and generated files. GitHub Pages serves
`main` → `/docs`; a push updates the site.

For visual or interaction changes, also run `TNP_TEST_URL=https://your-site-root/`
`make test-journeys` with Playwright and Chromium already available to Node.
Run `make test-podcast` for feed navigation, artwork, transcript and enclosure
checks. Also run `make test-mobile-audio` for the WebKit iPhone playback journey; this
catches media-loading failures that viewport resizing in Chromium cannot.
Run `make test-discovery` for link previews, site search, licenses, crawler
files and a mobile layout check.
An existing WebKit executable can be selected with `TNP_WEBKIT_EXECUTABLE`.
These browser checks install nothing. It navigates from the homepage to
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
logo and block borders. Pixelify Sans gives major headings and prominent callouts
their pixel character, alongside small numeric accents. Smooth Avenir/system
sans-serif keeps navigation, controls and story copy easy to read. Headings have
no hard text shadow. The arrow's outlined amber
peak stays ahead of its mint tip. The reusable mark is [assets/mark.svg](assets/mark.svg). The podcast cover is
[assets/cover.png](assets/cover.png), rendered from [its editable SVG](assets/cover.svg).
To regenerate it with an existing Playwright/Chromium installation, serve the
repository root locally, set `TNP_COVER_URL` to its `assets/cover.svg` URL and run
`node tools/render-cover.cjs`. Ordinary site builds use the committed PNG.

[Pixelify Sans](https://github.com/google/fonts/tree/main/ofl/pixelifysans) is
bundled unmodified with its [SIL Open Font License](assets/fonts/OFL.txt).
No font CDN or frontend dependencies are required. The cassette player adapts
[dqnamo’s Kitchen Cassette Audio Player](https://www.dqnamo.com/experiments/cassette-player)
to static HTML, CSS and JavaScript, with episode playback, seeking, restart,
mute, volume and playback-speed controls. The reels turn automatically with
playback, matching the original Kitchen component; pause stops them. Reduced
motion still disables decorative hover effects and smooth scrolling. Native
audio controls remain available when JavaScript is disabled.

This repository contains public story records and website source. Do not add
credentials, account information, internal operational notes, or original
third-party article bodies.
Public availability of this repository does not relicense linked third-party work.

## Reuse

Original episode recordings, scripts, transcripts, summaries, story data and
original artwork are [CC BY 4.0](LICENSE-CONTENT.md): reuse them with credit to
Trending Not Peak, a link to the relevant edition and license, and a note about
any changes. Original website code is [MIT licensed](LICENSE). Linked sources,
the bundled font and other third-party material retain their own terms.

Thanks to Intelligrit for sponsoring this daily update.
