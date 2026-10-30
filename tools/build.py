"""Build a portable, dependency-free Pages archive from public episode records."""

import json
import hashlib
import re
import shutil
from datetime import date, datetime
from html import escape
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

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
    def asset(name):
        version = hashlib.sha256((ROOT / 'assets' / name).read_bytes()).hexdigest()[:12]
        return f'{prefix}assets/{name}?v={version}'

    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)} · Trending Not Peak</title><meta name="description" content="{escape(config['description'], quote=True)}">
<link rel="canonical" href="{link(canonical)}"><link rel="icon" href="{asset('mark.svg')}" type="image/svg+xml">
<meta name="theme-color" content="#15182f"><link rel="preload" href="{prefix}assets/fonts/PixelifySans.ttf" as="font" type="font/ttf" crossorigin>
<link rel="stylesheet" href="{asset('style.css')}"><script src="{asset('site.js')}" defer></script>
</head><body><a class="skip" href="#main">Skip to content</a>
<header class="site-header"><a class="brand" href="{prefix}" aria-label="Trending Not Peak home"><img src="{asset('mark.svg')}" width="48" height="48" alt="">trending<span>not</span>peak<span class="brand-dot">.</span></a>
<nav aria-label="Main navigation"><a href="{prefix}#archive">Editions</a><a href="{prefix}#method">How we pick</a><a href="{link(config['repository'])}">Source</a></nav></header>
<main id="main">{body}</main>
<footer><p class="footer-brand">Curious before the crowd.</p><p>Thanks to <a href="https://intelligrit.com/">Intelligrit</a> for sponsoring this daily update.</p>
<p class="fine">Original summaries. Linked sources. AI-assisted writing and narration, with editorial review.<br>Trending Not Peak is in its launch preview. The custom domain and podcast subscriptions are coming.</p>
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
        return '<div class="audio-status"><span class="status-dot" aria-hidden="true"></span><div><strong>The reading edition is ready.</strong><p>The full audio edition is coming. All twenty stories and their sources are below.</p></div></div>'
    chapter_note = f" · {audio['embedded_chapters']} embedded MP3 chapters" if audio.get('embedded_chapters') else ''
    return f'''<section class="listen" aria-label="Listen to the episode"><p class="eyebrow">Now playing / {label(episode['date'])}</p><h2>Press play. Follow the links later.</h2>
<audio controls preload="metadata" src="{link(audio['url'])}">Your browser does not support audio playback.</audio>
<a href="{link(audio['url'])}">Download the MP3 ↗</a><p class="fine">{audio['duration_seconds'] / 60:.1f} minutes · AI narration{chapter_note}</p></section>'''


def episode_page(episode, config, prefix='../../../'):
    day = episode['date']
    categories = sorted({story['category'] for story in episode['stories']})
    options = ''.join(f'<option>{escape(category)}</option>' for category in categories)
    contents = ''.join(f'<li><a href="#{story["number"]}"><span>{story["number"]:02d}</span>{escape(story["title"])}</a></li>' for story in episode['stories'])
    body = f'''<section class="edition-heading"><a class="back" href="{prefix}">← All editions</a><p class="eyebrow">The daily field notes · {label(day)}</p>
<h1>Twenty things<br>worth a closer look<span class="accent">.</span></h1>
<p class="dek">The strongest signal first. A little weirdness at the end. Everything you need to follow the threads in between.</p>
<div class="edition-meta"><span>{len(episode['stories'])} stories</span><span>AI + development</span><a href="{prefix}data/{day}.json">Story data ↗</a><a href="{prefix}transcripts/{day}.txt">Transcript ↗</a></div>
{audio_html(episode)}</section>
<details class="story-index"><summary>Jump to a story <span>{len(episode['stories'])} signals ↓</span></summary><ol>{contents}</ol></details>
<form class="filters" data-filter hidden role="search"><div><label for="search">Find something you missed</label><input id="search" type="search" placeholder="A project, a topic, a strange idea…" autocomplete="off"></div>
<div><label for="category">Topic</label><select id="category"><option value="">All topics</option>{options}</select></div><button type="reset">Reset</button>
<p id="result-count" role="status" aria-live="polite">{len(episode['stories'])} stories</p></form>
<div class="stories">{''.join(card(story, prefix) for story in episode['stories'])}</div><p class="empty" hidden>No stories match. Try another search or reset the filters.</p>
<aside class="edition-end"><p class="eyebrow">Caught up.</p><h2>Keep the useful bits.<br>Leave the hype.</h2><p>Thanks to <a href="https://intelligrit.com/">Intelligrit</a> for sponsoring this daily update.</p><a href="{prefix}#archive">Browse the archive →</a></aside>'''
    return shell(label(day), body, prefix, config['base_url'] + '/' + episode_path(day), config)


def home(episodes, config):
    latest = episodes[-1]
    lead = latest['stories'][0]
    day = latest['date']
    route = episode_path(day)
    editions = ''.join(f'<li><a href="{episode_path(episode["date"])}"><time datetime="{episode["date"]}">{label(episode["date"])}</time><span>{escape(episode["stories"][0]["title"])}</span><span class="archive-count">{len(episode["stories"])} stories ↗</span></a></li>' for episode in reversed(episodes))
    body = f'''<section class="hero"><div class="hero-copy"><p class="eyebrow"><span class="status-dot" aria-hidden="true"></span> AI &amp; development · Before the peak</p>
<h1>Early signals.<br>Useful details<span class="accent">.</span></h1><p class="dek">A daily dose of things gathering momentum. Twenty stories, about ten minutes, and enough context to decide what deserves your attention.</p>
<a class="button" href="{route}">Explore the latest edition <span aria-hidden="true">↗</span></a><p class="fine">{label(day)} · {len(latest['stories'])} stories · {'Audio + field notes' if latest.get('audio') else 'Reading edition available'}</p></div>
<a class="lead-panel" href="{route}#1"><div class="panel-top"><span class="eyebrow">Today's strongest signal</span><span>01 / {len(latest['stories']):02d}</span></div><img class="signal-art" src="./assets/signal-landscape.svg" width="576" height="336" alt="">
<p class="eyebrow">{escape(lead['category'])}</p><h2>{escape(lead['title'])}</h2><p>{escape(lead['script'].split('. ')[0])}.</p><span class="panel-cta">Follow this thread ↗</span></a></section>
<section class="archive" id="archive"><div class="section-heading"><div><p class="eyebrow">Miss something?</p><h2>It's all here.</h2></div><span class="fine">The story archive</span></div><ul>{editions}</ul></section>
<section class="method" id="method"><p class="eyebrow">How we pick</p><h2>Interesting is a start.<br>Evidence gets it in.</h2><div class="method-grid"><div><span>01 / Find the signal</span><p>We look across project activity, developer communities, research and curated public posts. GitHub is one source, not the whole map.</p></div><div><span>02 / Follow the source</span><p>Posts lead us to work we can inspect: a paper, a release, a working project. Big claims stay attributed. Limitations stay visible.</p></div><div><span>03 / Show the receipts</span><p>Every story links its sources and explains why it made the cut. Dated counts are clues, not a prediction that something will take off.</p></div></div><p class="fine">We keep a coverage history. When a topic returns, we explain what changed. These are editorial picks from a bounded source sample, not a claim to have measured the entire internet.</p></section>'''
    return shell('Early signals in AI & development', body, './', config['base_url'] + '/', config)


def build():
    config = json.loads((ROOT / 'site.json').read_text())
    link(config['base_url'])
    episodes = [json.loads(path.read_text()) for path in sorted((ROOT / 'episodes').glob('*.json'))]
    if not episodes:
        raise ValueError('Add at least one public episode record before building')
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
        for story in episode['stories']:
            text.extend([story['title'], story['script']])
        text.append(episode['outro'])
        write(OUT / 'transcripts' / f'{day}.txt', '\n\n'.join(text) + '\n')
    write(OUT / 'index.html', home(episodes, config))
    write(OUT / '.nojekyll', '')
    shutil.copytree(ROOT / 'assets', OUT / 'assets', dirs_exist_ok=True)
    print(json.dumps({'editions': len(episodes), 'latest': episodes[-1]['date'], 'output': 'docs'}))


if __name__ == '__main__':
    build()
