"""Check the real generated archive, source boundary and portable links."""

import json
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from build import ROOT, OUT, link, shell


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.add(attrs['id'])
        for key in ('href', 'src'):
            if key in attrs:
                self.links.append(attrs[key])


class Archive(unittest.TestCase):
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
        allowed = {'schema_version', 'date', 'title', 'intro', 'outro', 'audio', 'stories'}
        for path in (ROOT / 'episodes').glob('*.json'):
            record = json.loads(path.read_text())
            self.assertEqual(allowed, set(record))
            self.assertEqual(record, json.loads((OUT / 'data' / path.name).read_text()))
            self.assertGreaterEqual(len(record['stories']), 20)
            html = (OUT / 'episodes' / record['date'] / 'index.html').read_text()
            for story in record['stories']:
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
