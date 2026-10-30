"""Exercise feed identity, public data boundaries and podcast delivery metadata."""

import copy
import json
import unittest
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from build import ROOT, OUT
from podcast import ATOM, CONTENT, ITUNES, PODCAST, build_feed, validate_chapters, validate_cover


class Podcast(unittest.TestCase):
    def setUp(self):
        self.site = json.loads((ROOT / 'site.json').read_text())
        self.podcast = json.loads((ROOT / 'podcast.json').read_text())
        self.episode = json.loads((ROOT / 'episodes/2026-10-29.json').read_text())

    def feed(self, episodes=None, site=None, podcast=None):
        return ET.fromstring(build_feed(site or self.site, podcast or self.podcast,
                                       episodes or [self.episode], {'2026-10-29'}))

    def test_published_feed_has_real_resources_and_contact(self):
        root = ET.parse(OUT / 'feed.xml').getroot()
        channel = root.find('channel')
        item = channel.find('item')
        self.assertEqual(channel.findtext(f'{{{ITUNES}}}owner/{{{ITUNES}}}email'), 'podcasts@robertmelton.com')
        self.assertEqual(channel.find(f'{{{ATOM}}}link').get('href'), 'https://trendingnotpeak.com/feed.xml')
        self.assertEqual(item.find('enclosure').attrib, {'url': self.episode['audio']['url'],
                         'length': str(self.episode['audio']['bytes']), 'type': 'audio/mpeg'})
        self.assertEqual(parsedate_to_datetime(item.findtext('pubDate')).isoformat(), '2026-10-30T02:05:59+00:00')
        self.assertEqual(item.findtext('link'), 'https://trendingnotpeak.com/2026/10/29/')
        for name, suffix in (('transcript', '/transcripts/2026-10-29.txt'), ('chapters', '/chapters/2026-10-29.json')):
            self.assertEqual(item.find(f'{{{PODCAST}}}{name}').get('url'), self.site['base_url'] + suffix)
            self.assertTrue((OUT / suffix.lstrip('/')).is_file())
        for page in OUT.rglob('*.html'):
            self.assertIn('rel="alternate" type="application/rss+xml"', page.read_text())
            self.assertIn('>Podcast RSS</a>', page.read_text())

    def test_guid_and_publication_time_survive_rebuild_and_host_move(self):
        old = self.feed().find('channel/item')
        migrated = dict(self.site, base_url='https://new.trendingnotpeak.com')
        changed = copy.deepcopy(self.episode)
        changed['title'] = 'A corrected title & an updated audio file'
        changed['audio']['url'] = 'https://media.trendingnotpeak.com/revision.mp3'
        new = self.feed([changed], site=migrated).find('channel/item')
        self.assertEqual(old.findtext('guid'), new.findtext('guid'))
        self.assertEqual(old.findtext('pubDate'), new.findtext('pubDate'))
        self.assertEqual(old.find('guid').get('isPermaLink'), 'false')

    def test_notes_keep_sources_and_exclude_unknown_private_fields(self):
        self.episode['internal_notes'] = 'DO_NOT_PUBLISH_SENTINEL'
        self.episode['stories'][0]['raw_article'] = 'DO_NOT_PUBLISH_SENTINEL'
        self.episode['title'] = 'AI & tools <today>'
        root = self.feed()
        xml = ET.tostring(root).decode()
        self.assertNotIn('DO_NOT_PUBLISH_SENTINEL', xml)
        self.assertEqual(root.findtext('channel/item/title'), 'AI & tools <today>')
        notes = root.findtext(f'channel/item/{{{CONTENT}}}encoded')
        self.assertIn('https://odysseysbench.com/v2', notes)
        self.assertIn('synthetic narration', notes)

    def test_reading_editions_are_omitted_and_empty_feed_is_rejected(self):
        reading = dict(self.episode, audio=None, date='2026-10-28')
        self.assertEqual(len(self.feed([self.episode, reading]).findall('channel/item')), 1)
        with self.assertRaisesRegex(ValueError, 'at least one audio'):
            self.feed([reading])

    def test_bad_publication_and_enclosure_cannot_build(self):
        for value in ('2026-10-30T02:05:59', 'not-a-date'):
            with self.subTest(publication=value), self.assertRaises(ValueError):
                self.feed(podcast=dict(self.podcast, publications={'2026-10-29': value}))
        for field, value in (('url', 'https://user:secret@example.com/audio.mp3'), ('url', 'http://media.test/audio.mp3'),
                             ('bytes', 0), ('duration_seconds', float('nan'))):
            changed = copy.deepcopy(self.episode)
            changed['audio'][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.feed([changed])
        with self.assertRaisesRegex(ValueError, 'unique enclosure'):
            self.feed([self.episode, self.episode])

    def test_synthetic_narration_is_disclosed_in_show_and_episode(self):
        root = self.feed()
        self.assertIn('synthetic narration', root.findtext('channel/description'))
        self.assertIn('synthetic narration', root.findtext('channel/item/description'))
        with self.assertRaisesRegex(ValueError, 'Show metadata'):
            self.feed(site=dict(self.site, description='A daily technology show.'))
        with self.assertRaisesRegex(ValueError, 'Audio introduction'):
            self.feed([dict(self.episode, intro='This is Trending Not Peak.')])

    def test_cover_and_chapters_match_the_actual_episode(self):
        self.assertEqual(validate_cover((OUT / 'assets/cover.png').read_bytes()), (3000, 3000))
        chapters = json.loads((OUT / 'chapters/2026-10-29.json').read_text())
        validate_chapters(chapters, self.episode)
        self.assertEqual(len(chapters['chapters']), 22)
        self.assertEqual([c['title'] for c in chapters['chapters'][1:-1]], [s['title'] for s in self.episode['stories']])
        chapters['chapters'][-1]['startTime'] = self.episode['audio']['duration_seconds'] + 1
        with self.assertRaisesRegex(ValueError, 'within the audio'):
            validate_chapters(chapters, self.episode)


if __name__ == '__main__':
    unittest.main()
