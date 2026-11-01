"""Build a portable, dependency-free Pages archive from public episode records."""

import json
import hashlib
import re
import shutil
from datetime import date, datetime
from html import escape
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

from podcast import build_feed, validate_chapters, validate_cover

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs'


def link(url):
    parsed = urlsplit(url)
    if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('Public links must use HTTP(S) without credentials')
    return escape(url, quote=True)


def label(day):
    return date.fromisoformat(day).strftime('%B %d, %Y').replace(' 0', ' ')


def episode_path(day):
    """Return the canonical calendar route, relative to the site root."""
    return date.fromisoformat(day).strftime('%Y/%m/%d/')


def observed_at(value):
    if not value:
        return 'time not retained'
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Observation timestamps require a timezone')
    return parsed.astimezone(ZoneInfo('America/New_York')).strftime('%b %d, %Y · %I:%M %p %Z').replace(' 0', ' ')


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def shell(title, body, prefix, canonical, config):
    def asset(name, absolute=False):
        version = hashlib.sha256((ROOT / 'assets' / name).read_bytes()).hexdigest()[:12]
        root = config['base_url'] + '/' if absolute else prefix
        return f'{root}assets/{name}?v={version}'

    page_title = f'{title} · Trending Not Peak'
    share_image = link(asset('share-card.png', absolute=True))
    description = escape(config['description'], quote=True)

    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(page_title)}</title><meta name="description" content="{description}">
<link rel="canonical" href="{link(canonical)}"><link rel="icon" href="{asset('mark.svg')}" type="image/svg+xml">
<link rel="icon" href="{asset('mark-32.png')}" type="image/png" sizes="32x32"><link rel="apple-touch-icon" href="{asset('mark-180.png')}" sizes="180x180">
<link rel="license" href="https://creativecommons.org/licenses/by/4.0/">
<meta property="og:type" content="website"><meta property="og:site_name" content="Trending Not Peak">
<meta property="og:title" content="{escape(page_title, quote=True)}"><meta property="og:description" content="{description}"><meta property="og:url" content="{link(canonical)}">
<meta property="og:image" content="{share_image}"><meta property="og:image:type" content="image/png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="Trending Not Peak arrow graph logo: rising before the peak">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{escape(page_title, quote=True)}"><meta name="twitter:description" content="{description}"><meta name="twitter:image" content="{share_image}"><meta name="twitter:image:alt" content="Trending Not Peak arrow graph logo: rising before the peak">
<link rel="alternate" type="application/rss+xml" title="Trending Not Peak podcast" href="{prefix}feed.xml">
<meta name="theme-color" content="#15182f"><link rel="preload" href="{prefix}assets/fonts/PixelifySans.ttf" as="font" type="font/ttf" crossorigin>
<link rel="stylesheet" href="{asset('style.css')}"><script src="{asset('site.js')}" defer></script>
<link rel="stylesheet" href="{asset('cassette.css')}"><script src="{asset('cassette.js')}" defer></script>
</head><body><a class="skip" href="#main">Skip to content</a>
<header class="site-header"><a class="brand" href="{prefix}" aria-label="Trending Not Peak home"><img src="{asset('mark.svg')}" width="48" height="48" alt="">trending<span>not</span>peak<span class="brand-dot">.</span></a>
<nav aria-label="Main navigation"><a href="{prefix}#listen">Listen</a><a href="{prefix}#archive">Editions</a><a href="{prefix}#method">How we pick</a><a href="{prefix}feed.xml">Podcast RSS</a><a href="{link(config['repository'])}">Source</a></nav></header>
<main id="main">{body}</main>
<footer><p class="footer-brand">Curious before the crowd.</p>
<form class="site-search" action="https://duckduckgo.com/" method="get" role="search" aria-label="Search every edition with DuckDuckGo" data-site-search><label for="site-query">Search every edition with DuckDuckGo</label><div><input id="site-query" type="search" name="q" placeholder="A project, topic or idea…" required><button type="submit">Search ↗</button></div><p class="fine">Your search opens DuckDuckGo and stays within trendingnotpeak.com.</p></form>
<noscript><p class="fine">For a site-only search without JavaScript, add site:trendingnotpeak.com to your query.</p></noscript>
<p>Thanks to <a href="https://intelligrit.com/">Intelligrit</a> for sponsoring this daily update.</p>
<p class="fine">Original summaries. Linked sources. AI-assisted writing and narration, with editorial review.</p>
<p class="fine">Original show content: <a rel="license" href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. Credit Trending Not Peak, link to this site and the license, and mark changes. <a href="{link(config['repository'] + '/blob/main/LICENSE-CONTENT.md')}">Reuse details ↗</a><br>Original site code: <a href="{link(config['repository'] + '/blob/main/LICENSE')}">MIT</a>. Linked sources and bundled third-party assets retain their own terms.</p>
<a href="{link(config['repository'])}">Public story archive &amp; site source ↗</a></footer></body></html>'''


def observations_html(rows):
    if not rows:
        return '<p>No numeric snapshot retained for this story. See the dated source links and selection notes above.</p>'
    items = []
    for row in rows:
        metrics = dict(row.get('metrics', {}))
        community = row.get('community', {})
        metrics.update({key: value for key, value in community.items() if key in ('score', 'comments', 'views')})
        names = {'score': 'likes' if community.get('family') == 'x' else 'points'}
        counts = ' · '.join(f'{value:,} {names.get(key, key)}' for key, value in metrics.items() if isinstance(value, (int, float)))
        growth = row.get('momentum', {})
        change = ''
        if growth.get('type') == 'measured_github_growth':
            change = f"<p>Measured change: +{growth['stars_gained']} stars over {growth['hours']} hours; baseline {escape(observed_at(growth['baseline_at']))}.</p>"
        source = community.get('url', row['url'])
        items.append(f'''<li><a href="{link(source)}">{escape(row.get('kind', 'source').upper())} observation ↗</a>
<p>{escape(counts or 'Qualitative signal')}<br><span class="fine">Observed {escape(observed_at(row.get('observed_at')))}</span></p>{change}</li>''')
    return '<ul class="observations">' + ''.join(items) + '</ul>'


def card(story, prefix):
    role = {'anchor': 'The lead · hottest, not peak', 'closer': 'One for the road'}.get(story['role'], story['category'])
    sources = ''.join(f'<li><a href="{link(source["url"])}">{escape(urlsplit(source["url"]).hostname)} <span class="fine">/ {escape(source["kind"].replace("_", " "))}</span> ↗</a></li>' for source in story['sources'])
    followup = ''
    if story.get('follow_up'):
        follow = story['follow_up']
        old_day = date.fromisoformat(follow['previous_date']).isoformat()
        followup = f'<p class="follow-up">Following our <a href="{prefix}{episode_path(old_day)}">{label(old_day)} edition</a>: {escape(follow["what_changed"])} {escape(follow["why_revisit"])}</p>'
    return f'''<article class="story {escape(story['role'])}" id="{story['number']}" data-story-id="{escape(story['id'])}" data-category="{escape(story['category'], quote=True)}">
<span class="legacy-anchor" id="{escape(story['id'])}" aria-hidden="true"></span>
<div class="story-top"><span class="eyebrow">{escape(role)}</span><a class="number" href="#{story['number']}" aria-label="Permalink to story {story['number']}">#{story['number']:02d} ↗</a></div>
<h2>{escape(story['title'])}</h2><h3 class="transcript-label">Story transcript</h3><p class="script">{escape(story['script'])}</p>{followup}
<dl class="selection"><div><dt>Why picked</dt><dd>{escape(story['why_now'])}</dd></div>
<div><dt>Why early</dt><dd>{escape(story['why_early'])}</dd></div><div><dt>Watch next</dt><dd>{escape(story['watch_next'])}</dd></div></dl>
<h3 class="transcript-label">Sources &amp; further reading</h3>
<ul class="sources" aria-label="Sources for {escape(story['title'], quote=True)}">{sources}</ul>
<details><summary>Dated signal snapshots <span aria-hidden="true">+</span></summary><div class="evidence">
<h3>Our snapshot</h3>{observations_html(story['observations'])}
<p class="fine">Counts describe the observation time, not current popularity. One snapshot shows interest, not acceleration. Our source sample cannot establish global obscurity.</p></div></details></article>'''


def audio_html(episode):
    audio = episode.get('audio')
    if not audio:
        return (f'<div class="audio-status"><span class="status-dot" aria-hidden="true"></span>'
                f'<div><strong>The reading edition is ready.</strong><p>The full audio edition is coming. '
                f'All {len(episode["stories"])} stories and their sources are below.</p></div></div>')
    chapter_note = f" · {audio['embedded_chapters']} embedded MP3 chapters" if audio.get('embedded_chapters') else ''
    return f'''<section class="listen" aria-label="Listen to the episode"><p class="eyebrow">Now playing / {label(episode['date'])}</p><h2>Press play. Follow the links later.</h2>
<div class="cassette-player" data-cassette>
<audio controls preload="metadata" aria-label="Episode audio"><source src="{link(audio['url'])}" type="audio/mpeg">Your browser does not support audio playback.</audio>
<div class="cassette" hidden>
<i class="screw tl" aria-hidden="true"></i><i class="screw tr" aria-hidden="true"></i><i class="screw bl" aria-hidden="true"></i><i class="screw br" aria-hidden="true"></i>
<div class="cassette-label"><div class="cassette-heading"><div><span class="cassette-kicker">Trending Not Peak</span><strong>{label(episode['date'])}</strong></div><span class="cassette-side">Side A</span></div>
<div class="cassette-stripes" aria-hidden="true"><div class="tape-window"><span class="tape left-tape"></span><span class="tape right-tape"></span><span class="reel left-reel"></span><span class="reel right-reel"></span><span class="tape-guides">│ │ │ │ │</span></div></div>
<div class="cassette-progress"><label class="sr-only" for="episode-seek">Seek through episode</label><input id="episode-seek" type="range" min="0" max="1" value="0" step="1" disabled><div class="cassette-times"><span><span class="sr-only">Elapsed time </span><time data-elapsed>0:00</time></span><span><span class="sr-only">Total time </span><time data-duration>0:00</time></span></div></div></div>
<div class="cassette-controls"><button type="button" data-restart aria-label="Restart episode" disabled><span aria-hidden="true">↶</span></button><button type="button" data-play aria-label="Play episode"><span aria-hidden="true">▶</span></button><button type="button" data-mute aria-label="Mute"><span aria-hidden="true">♪</span></button></div>
</div><div class="cassette-settings" hidden><label for="episode-speed">Speed <select id="episode-speed" aria-label="Playback speed"><option value="0.75">0.75×</option><option value="1" selected>1×</option><option value="1.25">1.25×</option><option value="1.5">1.5×</option><option value="1.75">1.75×</option><option value="2">2×</option></select></label><div class="cassette-volume"><label for="episode-volume">Volume</label><input id="episode-volume" type="range" min="0" max="1" value="0.78" step="0.05"></div></div>
<p class="cassette-error" role="alert" hidden></p></div>
<a href="{link(audio['url'])}">Download the MP3 ↗</a><p class="fine">{audio['duration_seconds'] / 60:.1f} minutes · AI narration{chapter_note}</p></section>'''


def listen_html(config, prefix, section_id=''):
    """Render only listener destinations that have a direct show or feed route."""
    cards = []
    for platform in config.get('listen', []):
        icon = platform['icon']
        if icon not in {'listen-spotify.svg', 'listen-amazon.svg', 'listen-pocketcasts.svg'}:
            raise ValueError('Unknown listening platform icon')
        cards.append(f'''<a class="listen-option" href="{link(platform['url'])}"><img src="{prefix}assets/{icon}" width="42" height="42" alt=""><span>{escape(platform['name'])}<small>Open show ↗</small></span></a>''')
    cards.append(f'''<a class="listen-option" href="{link(config['base_url'] + '/feed.xml')}"><img src="{prefix}assets/listen-rss.svg" width="42" height="42" alt=""><span>Podcast RSS<small>Use any podcast app ↗</small></span></a>''')
    identifier = f' id="{section_id}"' if section_id else ''
    return f'''<section class="subscribe"{identifier} aria-labelledby="subscribe-title"><div class="subscribe-heading"><p class="eyebrow">Keep it coming</p><h2 id="subscribe-title">Listen your way.</h2><p>Choose an app to follow the show. New editions land every morning.</p></div><div class="listen-options">{''.join(cards)}</div></section>'''


def episode_page(episode, config, prefix='../../../'):
    day = episode['date']
    categories = sorted({story['category'] for story in episode['stories']})
    options = ''.join(f'<option>{escape(category)}</option>' for category in categories)
    contents = ''.join(f'<li><a href="#{story["number"]}"><span>{story["number"]:02d}</span>{escape(story["title"])}</a></li>' for story in episode['stories'])
    story_cards = []
    for story in episode['stories']:
        story_cards.append(card(story, prefix))
        interlude = episode.get('interlude')
        if interlude and story['number'] == interlude['after_story']:
            story_cards.append(f'<aside class="sponsor-note"><p>{escape(interlude["script"])}</p></aside>')
    body = f'''<section class="edition-heading"><a class="back" href="{prefix}">← All editions</a><p class="eyebrow">The daily field notes · {label(day)}</p>
<h1>Things worth<br>a closer look<span class="accent">.</span></h1>
<p class="dek">The strongest signal first. A little weirdness at the end. Everything you need to follow the threads in between.</p>
<div class="edition-meta"><span>{len(episode['stories'])} stories</span><span>AI + development</span><a href="{prefix}data/{day}.json">Story data ↗</a><a href="{prefix}transcripts/{day}.txt">Transcript ↗</a></div>
{audio_html(episode)}</section>
{listen_html(config, prefix)}
<details class="story-index"><summary>Jump to a story <span>{len(episode['stories'])} signals ↓</span></summary><ol>{contents}</ol></details>
<form class="filters" data-filter hidden role="search"><div><label for="search">Find something you missed</label><input id="search" type="search" placeholder="A project, a topic, a strange idea…" autocomplete="off"></div>
<div><label for="category">Topic</label><select id="category"><option value="">All topics</option>{options}</select></div><button type="reset">Reset</button>
<p id="result-count" role="status" aria-live="polite">{len(episode['stories'])} stories</p></form>
<div class="stories">{''.join(story_cards)}</div><p class="empty" hidden>No stories match. Try another search or reset the filters.</p>
<aside class="edition-end"><p class="eyebrow">Caught up.</p><h2>Keep the useful bits.<br>Leave the hype.</h2><p>Thanks to <a href="https://intelligrit.com/">Intelligrit</a> for sponsoring this daily update.</p><a href="{prefix}#archive">Browse the archive →</a></aside>'''
    return shell(label(day), body, prefix, config['base_url'] + '/' + episode_path(day), config)


def home(episodes, config):
    latest = episodes[-1]
    lead = latest['stories'][0]
    day = latest['date']
    route = episode_path(day)
    editions = ''.join(f'<li><a href="{episode_path(episode["date"])}"><time datetime="{episode["date"]}">{label(episode["date"])}</time><span>{escape(episode["stories"][0]["title"])}</span><span class="archive-count">{len(episode["stories"])} stories ↗</span></a></li>' for episode in reversed(episodes))
    body = f'''<section class="hero"><div class="hero-copy"><p class="eyebrow"><span class="status-dot" aria-hidden="true"></span> AI &amp; development · Before the peak</p>
<h1>Early signals.<br>Useful details<span class="accent">.</span></h1><p class="dek">A daily dose of things gathering momentum. Up to twenty stories, ten minutes or less, and enough context to decide what deserves your attention.</p>
<a class="button" href="{route}">Explore the latest edition <span aria-hidden="true">↗</span></a><p class="fine">{label(day)} · {len(latest['stories'])} stories · {'Audio + field notes' if latest.get('audio') else 'Reading edition available'}</p></div>
<a class="lead-panel" href="{route}#1"><div class="panel-top"><span class="eyebrow">Today's strongest signal</span><span>01 / {len(latest['stories']):02d}</span></div><img class="signal-art" src="./assets/signal-landscape.svg" width="576" height="336" alt="">
<p class="eyebrow">{escape(lead['category'])}</p><h2>{escape(lead['title'])}</h2><p>{escape(lead['script'].split('. ')[0])}.</p><span class="panel-cta">Follow this thread ↗</span></a></section>
{listen_html(config, './', 'listen')}
<section class="archive" id="archive"><div class="section-heading"><div><p class="eyebrow">Miss something?</p><h2>It's all here.</h2></div><span class="fine">The story archive</span></div><ul>{editions}</ul></section>
<section class="method" id="method"><p class="eyebrow">How we pick</p><h2>Interesting is a start.<br>Evidence gets it in.</h2><div class="method-grid"><div><span>01 / Find the signal</span><p>We look across project activity, developer communities, research and curated public posts. GitHub is one source, not the whole map.</p></div><div><span>02 / Follow the source</span><p>Posts lead us to work we can inspect: a paper, a release, a working project. Big claims stay attributed. Limitations stay visible.</p></div><div><span>03 / Show the receipts</span><p>Every story links its sources and explains why it made the cut. Dated counts are clues, not a prediction that something will take off.</p></div></div><p class="fine">We keep a coverage history. When a topic returns, we explain what changed. These are editorial picks from a bounded source sample, not a claim to have measured the entire internet.</p></section>'''
    return shell('Early signals in AI & development', body, './', config['base_url'] + '/', config)


def discovery_files(episodes, config):
    """Write crawler and reader indexes for the public archive only."""
    base = config['base_url'].rstrip('/')
    pages = [base + '/'] + [base + '/' + episode_path(item['date']) for item in episodes]
    sitemap = ET.Element('urlset', xmlns='http://www.sitemaps.org/schemas/sitemap/0.9')
    for url in pages:
        ET.SubElement(ET.SubElement(sitemap, 'url'), 'loc').text = url
    ET.indent(sitemap)
    write(OUT / 'sitemap.xml', ET.tostring(sitemap, encoding='unicode', xml_declaration=True) + '\n')
    write(OUT / 'robots.txt', f'User-agent: *\nAllow: /\n\nSitemap: {base}/sitemap.xml\n')
    lines = [
        '# Trending Not Peak',
        '',
        '> Daily AI and development podcast: emerging stories, original summaries, transcripts, evidence and source links.',
        '',
        '## Archive and downloads',
        f'- [All editions]({base}/): Browse the full public archive.',
        f'- [Podcast RSS]({base}/feed.xml): Subscribe and find episode audio.',
        f'- [Sitemap]({base}/sitemap.xml): Canonical pages.',
    ]
    for item in reversed(episodes):
        day = item['date']
        lines.extend([
            f'- [{label(day)} edition]({base}/{episode_path(day)}): Stories, selection reasons and source links.',
            f'- [{day} transcript]({base}/transcripts/{day}.txt): Full spoken script.',
            f'- [{day} story data]({base}/data/{day}.json): Structured public records and dated signal snapshots.',
        ])
        if item.get('audio'):
            lines.append(f'- [{day} audio]({item["audio"]["url"]}): Download the MP3.')
    lines.extend([
        '',
        '## Reuse and source',
        f'- [Content license]({config["repository"]}/blob/main/LICENSE-CONTENT.md): Original show content is CC BY 4.0 with credit.',
        f'- [Site code]({config["repository"]}): Original website code is MIT licensed; linked sources retain their own rights.',
        '',
    ])
    write(OUT / 'llms.txt', '\n'.join(lines))


def build():
    config = json.loads((ROOT / 'site.json').read_text())
    link(config['base_url'])
    episodes = [json.loads(path.read_text()) for path in sorted((ROOT / 'episodes').glob('*.json'))]
    if not episodes:
        raise ValueError('Add at least one public episode record before building')
    podcast = json.loads((ROOT / 'podcast.json').read_text())
    validate_cover((ROOT / podcast['cover']).read_bytes())
    chapters = {}
    for episode in episodes:
        chapter_path = ROOT / 'chapters' / f"{episode['date']}.json"
        if episode.get('audio') and chapter_path.is_file():
            data = json.loads(chapter_path.read_text())
            validate_chapters(data, episode)
            chapters[episode['date']] = data
    feed = build_feed(config, podcast, episodes, chapters)
    for episode in episodes:
        day = episode['date']
        if date.fromisoformat(day).isoformat() != day or episode['schema_version'] != 1:
            raise ValueError('Unsupported date or episode schema')
        ids = [story['id'] for story in episode['stories']]
        if len(ids) != len(set(ids)) or not all(re.fullmatch(r'story-[0-9a-f]{12}', value) for value in ids):
            raise ValueError('Story IDs must be unique stable anchors')
        if [story['number'] for story in episode['stories']] != list(range(1, len(ids) + 1)):
            raise ValueError('Story numbers must match their order, starting at one')
        write(OUT / episode_path(day) / 'index.html', episode_page(episode, config))
        # Keep existing public URLs and hashed fragments usable; canonical points to the calendar URL.
        write(OUT / 'episodes' / day / 'index.html', episode_page(episode, config, prefix='../../'))
        write(OUT / 'data' / f'{day}.json', json.dumps(episode, ensure_ascii=False, indent=2) + '\n')
        text = [episode['title'], episode['intro']]
        for number, story in enumerate(episode['stories'], 1):
            text.extend([story['title'], story['script']])
            interlude = episode.get('interlude')
            if interlude and number == interlude['after_story']:
                text.extend([interlude['title'], interlude['script']])
        text.append(episode['outro'])
        write(OUT / 'transcripts' / f'{day}.txt', '\n\n'.join(text) + '\n')
    write(OUT / 'index.html', home(episodes, config))
    write(OUT / 'feed.xml', feed)
    discovery_files(episodes, config)
    for day, data in chapters.items():
        write(OUT / 'chapters' / f'{day}.json', json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    write(OUT / '.nojekyll', '')
    shutil.copytree(ROOT / 'assets', OUT / 'assets', dirs_exist_ok=True)
    print(json.dumps({'editions': len(episodes), 'latest': episodes[-1]['date'], 'output': 'docs'}))


if __name__ == '__main__':
    build()
