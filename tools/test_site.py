"""Check the real generated archive, source boundary and portable links."""

import json
import re
import struct
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree as ET

from build import ROOT, OUT, card, episode_path, link, shell


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()
        self.meta = {}
        self.relations = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'meta':
            self.meta[attrs.get('property') or attrs.get('name')] = attrs.get('content')
        if tag == 'link':
            self.relations.setdefault(attrs.get('rel'), []).append(attrs.get('href'))
        if 'id' in attrs:
            self.ids.add(attrs['id'])
        for key in ('href', 'src'):
            if key in attrs:
                self.links.append(attrs[key])


class Archive(unittest.TestCase):
    def test_share_metadata_icons_and_license_on_all_pages(self):
        config = json.loads((ROOT / 'site.json').read_text())
        image = (ROOT / 'assets/share-card.png').read_bytes()
        self.assertEqual(image[:8], b'\x89PNG\r\n\x1a\n')
        self.assertEqual(struct.unpack('>II', image[16:24]), (1200, 630))
        for name, size in (('mark-32.png', 32), ('mark-180.png', 180)):
            icon = (OUT / 'assets' / name).read_bytes()
            self.assertEqual(struct.unpack('>II', icon[16:24]), (size, size))
        for path in OUT.rglob('*.html'):
            page = Links()
            page.feed(path.read_text())
            with self.subTest(page=path):
                canonical = page.relations['canonical'][0]
                self.assertEqual(page.meta['og:url'], canonical)
                self.assertIn(config['base_url'] + '/assets/share-card.png?v=', page.meta['og:image'])
                self.assertEqual(page.meta['twitter:image'], page.meta['og:image'])
                self.assertEqual(page.meta['og:image:width'], '1200')
                self.assertEqual(page.meta['og:image:height'], '630')
                self.assertEqual(page.meta['twitter:card'], 'summary_large_image')
                self.assertIn('Trending Not Peak', page.meta['og:title'])
                self.assertEqual(page.meta['og:description'], page.meta['twitter:description'])
                self.assertIn('https://creativecommons.org/licenses/by/4.0/', page.relations['license'])
                self.assertIn('Search every edition with DuckDuckGo', path.read_text())
        self.assertIn('MIT License', (ROOT / 'LICENSE').read_text())
        self.assertIn('Creative Commons Attribution 4.0', (ROOT / 'LICENSE-CONTENT.md').read_text())

    def test_open_discovery_indexes_current_canonical_editions(self):
        config = json.loads((ROOT / 'site.json').read_text())
        robots = (OUT / 'robots.txt').read_text()
        self.assertIn('User-agent: *\nAllow: /', robots)
        self.assertNotIn('Disallow:', robots)
        self.assertIn(config['base_url'] + '/sitemap.xml', robots)
        sitemap = ET.parse(OUT / 'sitemap.xml')
        locations = {node.text for node in sitemap.iter() if node.tag.endswith('}loc')}
        llms = (OUT / 'llms.txt').read_text()
        self.assertIn(config['base_url'] + '/', locations)
        self.assertIn(config['repository'], llms)
        self.assertIn(config['base_url'] + '/feed.xml', llms)
        for path in (ROOT / 'episodes').glob('*.json'):
            day = path.stem
            self.assertIn(config['base_url'] + '/' + episode_path(day), locations)
            self.assertIn(config['base_url'] + '/data/' + day + '.json', llms)
            self.assertIn(config['base_url'] + '/transcripts/' + day + '.txt', llms)

    def test_public_copy_excludes_operational_status(self):
        documents = {'README.md': (ROOT / 'README.md').read_text()}
        for path in OUT.rglob('*.html'):
            documents[str(path.relative_to(ROOT))] = path.read_text().split('<footer>', 1)[1]
        operational_status = re.compile(
            r'launch checklist|launch preview|private producer|pending approval|coming soon',
            re.IGNORECASE,
        )
        for name, content in documents.items():
            with self.subTest(document=name):
                self.assertNotRegex(content, operational_status)

    def test_calendar_routes_numbered_stories_and_legacy_links(self):
        config = json.loads((ROOT / 'site.json').read_text())
        for path in (ROOT / 'episodes').glob('*.json'):
            record = json.loads(path.read_text())
            route = episode_path(record['date'])
            canonical = (OUT / route / 'index.html').read_text()
            legacy = (OUT / 'episodes' / record['date'] / 'index.html').read_text()
            for html in (canonical, legacy):
                self.assertIn(f'href="{config["base_url"]}/{route}"', html)
                for number, story in enumerate(record['stories'], 1):
                    self.assertIn(f'id="{number}"', html)
                    self.assertIn(f'href="#{number}"', html)
                    self.assertIn(f'id="{story["id"]}"', html)
                self.assertIn('Story transcript', html)
                self.assertIn('<dt>Why picked</dt>', html)
                self.assertIn('Sources &amp; further reading', html)
            self.assertIn(f'href="{route}"', (OUT / 'index.html').read_text())

    def test_followup_links_use_calendar_routes(self):
        record = json.loads(next((ROOT / 'episodes').glob('*.json')).read_text())
        story = dict(record['stories'][0], follow_up={'previous_date': '2026-10-28',
                     'what_changed': 'New release adds a documented capability.',
                     'why_revisit': 'This materially changes the prior result.'})
        self.assertIn('href="../../../2026/10/28/"', card(story, '../../../'))
        self.assertIn('href="../../2026/10/28/"', card(story, '../../'))
        with self.assertRaises(ValueError):
            episode_path('../../escape')

    def test_every_generated_local_link_and_anchor_resolves(self):
        pages = {}
        for path in OUT.rglob('*.html'):
            document = Links()
            document.feed(path.read_text())
            pages[path.resolve()] = document
        self.assertGreaterEqual(len(pages), 2)
        for page, document in pages.items():
            for value in document.links:
                url = urlsplit(value)
                if url.scheme or url.netloc:
                    self.assertIn(url.scheme, ('https', 'http'))
                    continue
                target = (page.parent / unquote(url.path)).resolve() if url.path else page
                if target.is_dir():
                    target /= 'index.html'
                self.assertTrue(target.is_relative_to(OUT.resolve()), value)
                self.assertTrue(target.is_file(), (page, value))
                if url.fragment and target in pages:
                    self.assertIn(unquote(url.fragment), pages[target].ids)

    def test_story_records_are_public_and_retained_in_built_output(self):
        allowed = {'schema_version', 'date', 'title', 'intro', 'outro', 'audio', 'stories', 'interlude'}
        for path in (ROOT / 'episodes').glob('*.json'):
            record = json.loads(path.read_text())
            self.assertEqual(allowed - {'interlude'}, set(record) - {'interlude'})
            if record.get('interlude'):
                self.assertEqual(set(record['interlude']), {'after_story', 'title', 'script'})
                self.assertEqual(record['interlude']['after_story'], len(record['stories']) // 2)
            if record['audio']:
                self.assertEqual(set(record['audio']), {'url', 'duration_seconds', 'bytes', 'embedded_chapters', 'sha256'})
            self.assertEqual(record, json.loads((OUT / 'data' / path.name).read_text()))
            self.assertTrue(6 <= len(record['stories']) <= 20)
            html = (OUT / 'episodes' / record['date'] / 'index.html').read_text()
            for story in record['stories']:
                self.assertLessEqual(set(story), {'id', 'number', 'category', 'role', 'title', 'script',
                                     'why_now', 'why_early', 'watch_next', 'sources', 'observations', 'follow_up'})
                for source in story['sources']:
                    self.assertLessEqual(set(source), {'url', 'kind'})
                if story.get('follow_up'):
                    self.assertEqual(set(story['follow_up']), {'previous_date', 'what_changed', 'why_revisit'})
                for observation in story['observations']:
                    self.assertLessEqual(set(observation), {'kind', 'published_at', 'observed_at',
                                         'url', 'metrics', 'community', 'momentum'})
                    self.assertLessEqual(set(observation.get('metrics', {})), {'stars', 'forks'})
                    self.assertLessEqual(set(observation.get('community', {})), {'family', 'score', 'comments', 'views', 'url'})
                    self.assertLessEqual(set(observation.get('momentum', {})), {'type', 'stars_gained', 'hours',
                                         'stars_per_day', 'baseline_stars', 'current_stars', 'baseline_at', 'observed_at', 'caveat'})
                self.assertIn(f'id="{story["id"]}"', html)
                self.assertTrue(story['sources'])
                self.assertNotIn('evidence_text', story)
            self.assertEqual('anchor', record['stories'][0]['role'])
            self.assertEqual('closer', record['stories'][-1]['role'])
            if record['audio'] is None:
                self.assertNotIn('<audio ', html)
                self.assertIn('reading edition is ready', html)

    def test_unsafe_links_rejected_and_page_text_escaped(self):
        for bad in ('javascript:alert(1)', 'https://user:password@example.com', '//example.com'):
            with self.assertRaises(ValueError):
                link(bad)
        config = json.loads((ROOT / 'site.json').read_text())
        result = shell('<script>alert(1)</script>', '<p>Trusted template</p>', './', config['base_url'], config)
        self.assertIn('&lt;script&gt;', result)
        self.assertNotIn('<title><script>', result)


if __name__ == '__main__':
    unittest.main()
