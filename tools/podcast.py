"""Generate a portable podcast feed from the public archive alone."""

import math
import re
import struct
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import format_datetime
from html import escape
from urllib.parse import urlsplit

ITUNES = 'http://www.itunes.com/dtds/podcast-1.0.dtd'
ATOM = 'http://www.w3.org/2005/Atom'
CONTENT = 'http://purl.org/rss/1.0/modules/content/'
PODCAST = 'https://podcastindex.org/namespace/1.0'
DISCLOSURE = 'AI-assisted writing and synthetic narration, with editorial review.'
for prefix, uri in (('itunes', ITUNES), ('atom', ATOM), ('content', CONTENT), ('podcast', PODCAST)):
    ET.register_namespace(prefix, uri)


def https_url(value):
    """Reject credentials, placeholders and non-public URL schemes."""
    parsed = urlsplit(value)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.fragment or any(c.isspace() for c in value)
            or parsed.hostname.endswith(('.example', '.test', '.invalid', '.localhost'))
            or parsed.hostname in ('localhost', 'example.com', 'example.org', 'example.net')
            or 'CHANGE_ME' in value):
        raise ValueError('Podcast URLs require real HTTPS addresses without credentials or fragments')
    return value


def published(value):
    """Keep the original public publication instant, independent of rebuilds."""
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp.tzinfo is None:
        raise ValueError('Podcast publication timestamps require a timezone')
    return stamp


def validate_cover(data):
    """Check the exact PNG submitted to podcast apps, including alpha channels."""
    if data[:8] != b'\x89PNG\r\n\x1a\n' or data[12:16] != b'IHDR':
        raise ValueError('Podcast cover must be a PNG')
    width, height, depth, color = struct.unpack('>IIBB', data[16:26])
    if width != height or not 1400 <= width <= 3000 or depth != 8 or color != 2:
        raise ValueError('Podcast cover must be a square 1400–3000px, 8-bit RGB PNG without alpha')
    return width, height


def validate_chapters(data, episode):
    """Ensure published chapter markers fit the associated audio edition."""
    chapters = data['chapters']
    if data.get('version') != '1.2.0' or len(chapters) != episode['audio']['embedded_chapters']:
        raise ValueError('Chapter file does not match the audio chapter count')
    previous = -1
    for chapter in chapters:
        start = chapter['startTime']
        if not math.isfinite(start) or not previous < start < episode['audio']['duration_seconds']:
            raise ValueError('Chapters must increase within the audio duration')
        if not chapter.get('title') or set(chapter) != {'startTime', 'title'}:
            raise ValueError('Chapter records contain only public titles and start times')
        previous = start
    if not chapters or chapters[0]['startTime'] != 0:
        raise ValueError('The first chapter must start at zero')


def notes_header(episode, url):
    """Put every story's permanent detail link near the top of the notes."""
    parsed = urlsplit(url)
    transcript_url = (f'{parsed.scheme}://{parsed.netloc}/transcripts/'
                      f'{episode["date"]}.txt')
    links = ''.join(
        f'<li><a href="{escape(url + "#" + str(number), quote=True)}">'
        f'{number:02d} · {escape(story["title"])}</a></li>'
        for number, story in enumerate(episode['stories'], 1))
    return (f'<p>{escape(episode["intro"])}</p>'
            f'<p>{len(episode["stories"])} stories. Tap one for its transcript, why we picked it, and source links:</p>'
            f'<ul>{links}</ul>'
            f'<p><a href="{escape(transcript_url, quote=True)}">Full transcript</a> · '
            f'<a href="{escape(url, quote=True)}">All story details and sources</a></p>')


def episode_description(episode, url):
    """Apple-compatible compact show notes, including the numbered story links."""
    notes = (notes_header(episode, url) + f'<p>{escape(episode["outro"])}</p>'
             f'<p>{DISCLOSURE}</p>')
    if len(notes) > 10000:
        raise ValueError('Episode description exceeds Apple Podcasts 10,000-character limit')
    return notes


def show_notes(episode, url):
    """Include useful episode context and primary-source links, never manifests."""
    parts = [notes_header(episode, url)]
    for number, story in enumerate(episode['stories'], 1):
        sources = ' '.join(f'<a href="{escape(https_url(source["url"]), quote=True)}">Source {i}</a>'
                           for i, source in enumerate(story['sources'], 1))
        parts.append(f'<h2>{escape(story["title"])}</h2><p>{escape(story["script"])}</p><p>{sources}</p>')
        interlude = episode.get('interlude')
        if interlude and number == interlude['after_story']:
            parts.append(f'<p>{escape(interlude["script"])}</p>')
    parts.extend([f'<p>{escape(episode["outro"])}</p>',
                  f'<p>{DISCLOSURE}</p>'])
    return ''.join(parts)


def build_feed(site, podcast, episodes, chapter_dates):
    """Build RSS with stable episode GUIDs and the actual hosted enclosures."""
    base = https_url(site['base_url'].rstrip('/'))
    cover = https_url(base + '/' + podcast['cover'])
    email = podcast['owner_email']
    if not re.fullmatch(r'[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+', email) or 'example.' in email or 'CHANGE_ME' in email:
        raise ValueError('Set a real public podcast owner email')
    if not podcast['id'] or not podcast['author'] or type(podcast['explicit']) is not bool:
        raise ValueError('Set stable podcast identity, author and explicit-content status')
    playable = [episode for episode in episodes if episode.get('audio')]
    if not playable:
        raise ValueError('Podcast feed requires at least one audio episode')
    if 'synthetic narration' not in site['description'].casefold():
        raise ValueError('Show metadata must disclose synthetic narration')
    playable.sort(key=lambda e: published(podcast['publications'][e['date']]), reverse=True)
    root = ET.Element('rss', version='2.0')

    def tag(parent, name, value=None, **attributes):
        node = ET.SubElement(parent, name, attributes)
        if value is not None:
            node.text = str(value)
        return node

    channel = tag(root, 'channel')
    for name, value in (('title', site['title']), ('link', base + '/'),
                        ('description', site['description']), ('language', podcast['language'])):
        tag(channel, name, value)
    tag(channel, 'copyright', '© 2026 Trending Not Peak. Original content CC BY 4.0: https://creativecommons.org/licenses/by/4.0/')
    tag(channel, f'{{{PODCAST}}}license', 'CC BY 4.0', url='https://creativecommons.org/licenses/by/4.0/')
    tag(channel, f'{{{ATOM}}}link', href=base + '/feed.xml', rel='self', type='application/rss+xml')
    tag(channel, f'{{{ITUNES}}}author', podcast['author'])
    tag(channel, f'{{{ITUNES}}}explicit', str(podcast['explicit']).lower())
    tag(channel, f'{{{ITUNES}}}type', 'episodic')
    tag(channel, f'{{{ITUNES}}}category', text=podcast['category'])
    news = tag(channel, f'{{{ITUNES}}}category', text='News')
    tag(news, f'{{{ITUNES}}}category', text='Tech News')
    tag(channel, f'{{{ITUNES}}}image', href=cover)
    owner = tag(channel, f'{{{ITUNES}}}owner')
    tag(owner, f'{{{ITUNES}}}name', podcast['author'])
    tag(owner, f'{{{ITUNES}}}email', email)
    image = tag(channel, 'image')
    for name, value in (('url', cover), ('title', site['title']), ('link', base + '/')):
        tag(image, name, value)
    seen = set()
    cdata = {}
    for episode in playable:
        day, audio = episode['date'], episode['audio']
        enclosure_url = https_url(audio['url'])
        if enclosure_url in seen or type(audio['bytes']) is not int or audio['bytes'] <= 0:
            raise ValueError('Each episode requires a unique enclosure and its positive byte count')
        if not math.isfinite(audio['duration_seconds']) or audio['duration_seconds'] <= 0:
            raise ValueError('Audio duration must be finite and positive')
        seen.add(enclosure_url)
        episode_url = base + '/' + day.replace('-', '/') + '/'
        item = tag(channel, 'item')
        tag(item, 'title', episode['title'])
        tag(item, f'{{{ITUNES}}}author', podcast['author'])
        tag(item, 'link', episode_url)
        tag(item, 'guid', 'urn:uuid:' + str(uuid.uuid5(uuid.NAMESPACE_URL, podcast['id'] + '/' + day)), isPermaLink='false')
        tag(item, 'pubDate', format_datetime(published(podcast['publications'][day])))
        for name, value in (('description', episode_description(episode, episode_url)),
                            (f'{{{CONTENT}}}encoded', show_notes(episode, episode_url))):
            marker = f'TNP_CDATA_{len(cdata)}_END'
            cdata[marker] = value
            tag(item, name, marker)
        tag(item, 'enclosure', url=enclosure_url, length=str(audio['bytes']), type='audio/mpeg')
        tag(item, f'{{{ITUNES}}}duration', round(audio['duration_seconds']))
        tag(item, f'{{{ITUNES}}}explicit', str(podcast['explicit']).lower())
        tag(item, f'{{{ITUNES}}}episodeType', 'full')
        if day in chapter_dates:
            tag(item, f'{{{PODCAST}}}chapters', url=base + '/chapters/' + day + '.json', type='application/json+chapters')
    ET.indent(root)
    xml = ET.tostring(root, encoding='utf-8', xml_declaration=True).decode()
    for marker, value in cdata.items():
        needle = f'>{marker}<'
        if xml.count(needle) != 1:
            raise ValueError('Episode notes CDATA marker was not unique')
        xml = xml.replace(needle, f'><![CDATA[{value.replace("]]>", "]]]]><![CDATA[>")}]]><')
    return xml + '\n'
