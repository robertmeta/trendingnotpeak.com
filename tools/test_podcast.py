"""Exercise feed identity, public data boundaries and podcast delivery metadata."""

import copy
import json
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime
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
        items = channel.findall('item')
        episodes = {p.stem: json.loads(p.read_text()) for p in (ROOT / 'episodes').glob('*.json')}
        playable = {day: episode for day, episode in episodes.items() if episode.get('audio')}
        self.assertEqual(len(items), len(playable))
        self.assertEqual(channel.findtext(f'{{{ITUNES}}}owner/{{{ITUNES}}}email'), 'podcasts@robertmelton.com')
        self.assertEqual(channel.find(f'{{{ATOM}}}link').get('href'), 'https://trendingnotpeak.com/feed.xml')
        license_tag = channel.find(f'{{{PODCAST}}}license')
        self.assertEqual(license_tag.text, 'CC BY 4.0')
        self.assertEqual(license_tag.get('url'), 'https://creativecommons.org/licenses/by/4.0/')
        self.assertEqual([item.findtext('link') for item in items],
                         [f'https://trendingnotpeak.com/{day.replace("-", "/")}/' for day in
                          sorted(playable, key=lambda day: self.podcast['publications'][day], reverse=True)])
        for item in items:
            day = item.findtext('link').rstrip('/').rsplit('/', 3)[-3:]
            day = '-'.join(day)
            episode = playable[day]
            self.assertEqual(item.find('enclosure').attrib,
                             {'url': episode['audio']['url'], 'length': str(episode['audio']['bytes']),
                              'type': 'audio/mpeg'})
            self.assertEqual(parsedate_to_datetime(item.findtext('pubDate')),
                             datetime.fromisoformat(self.podcast['publications'][day].replace('Z', '+00:00'))
                             .replace(microsecond=0))
            for name in ('transcript', 'chapters'):
                suffix = f'/{"transcripts" if name == "transcript" else "chapters"}/{day}.{ "txt" if name == "transcript" else "json"}'
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
        plain = self.feed([dict(self.episode, intro='This is Trending Not Peak.')])
        self.assertIn('synthetic narration', plain.findtext('channel/item/description'))

    def test_cover_and_chapters_match_the_actual_episode(self):
        self.assertEqual(validate_cover((OUT / 'assets/cover.png').read_bytes()), (3000, 3000))
        chapters = json.loads((OUT / 'chapters/2026-10-29.json').read_text())
        validate_chapters(chapters, self.episode)
        self.assertEqual(len(chapters['chapters']), 23)
        self.assertEqual(chapters['chapters'][11]['title'], 'Thanks to Intelligrit')
        self.assertEqual([c['title'] for i, c in enumerate(chapters['chapters']) if i not in (0, 11, 22)], [s['title'] for s in self.episode['stories']])
        chapters['chapters'][-1]['startTime'] = self.episode['audio']['duration_seconds'] + 1
        with self.assertRaisesRegex(ValueError, 'within the audio'):
            validate_chapters(chapters, self.episode)


if __name__ == '__main__':
    unittest.main()
