// Follow the reader-facing RSS link and verify the actual feed and downloadable output.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const target = process.env.TNP_TEST_URL;
if (!target) throw new Error('Set TNP_TEST_URL to the site root, with its trailing slash');
const artifacts = process.env.TNP_TEST_ARTIFACTS || path.resolve('.cache/podcast-journey');
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
(async () => {
  fs.mkdirSync(artifacts, { recursive: true });
  const args = ['--mute-audio'];
  const dnsOverride = process.env.TNP_TEST_RESOLVE_IP || null;
  if (dnsOverride) args.push(`--host-resolver-rules=MAP ${new URL(target).hostname} ${dnsOverride}`);
  const browser = await chromium.launch({ headless: false, args });
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  page.setDefaultTimeout(15000);
  try {
    await page.goto(target);
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    const [response] = await Promise.all([
      page.waitForResponse(r => r.url() === new URL('feed.xml', target).href),
      page.getByRole('link', { name: 'Podcast RSS', exact: true }).click(),
    ]);
    assert.equal(response.status(), 200);
    const xml = await response.text();
    fs.writeFileSync(path.join(artifacts, 'feed.xml'), xml);
    const feed = await page.evaluate(xml => {
      const doc = new DOMParser().parseFromString(xml, 'application/xml');
      if (doc.querySelector('parsererror')) throw new Error('Invalid feed XML');
      const channel = doc.querySelector('channel');
      const items = [...channel.querySelectorAll('item')];
      const itunes = 'http://www.itunes.com/dtds/podcast-1.0.dtd';
      const podcast = 'https://podcastindex.org/namespace/1.0';
      return {
        owner: channel.getElementsByTagNameNS(itunes, 'email')[0].textContent,
        cover: channel.getElementsByTagNameNS(itunes, 'image')[0].getAttribute('href'),
        episodes: items.map(item => {
          const notes = new DOMParser().parseFromString(item.querySelector('description').textContent, 'text/html');
          return {
            guid: item.querySelector('guid').textContent,
            edition: item.querySelector('link').textContent,
            audio: item.querySelector('enclosure').getAttribute('url'),
            bytes: Number(item.querySelector('enclosure').getAttribute('length')),
            transcript: notes.querySelector('a[href*="/transcripts/"]')?.href,
            storyLinks: [...notes.querySelectorAll('ul li a')].map(link => ({ href: link.href, title: link.textContent })),
            chapters: item.getElementsByTagNameNS(podcast, 'chapters')[0].getAttribute('url'),
          };
        }),
      };
    }, xml);
    assert.equal(feed.owner, 'podcasts@robertmelton.com');
    assert.ok(feed.episodes.length >= 2);
    const reload = await page.reload();
    assert.equal(await reload.text(), xml, 'The public feed must persist unchanged across reloads');
    const localAsset = value => new URL(new URL(value).pathname.replace(/^\//, ''), target).href;
    await page.goto(localAsset(feed.cover));
    await page.waitForFunction(() => document.querySelector('img')?.naturalWidth === 3000);
    assert.equal(await page.locator('img').evaluate(img => img.naturalHeight), 3000);
    await page.screenshot({ path: path.join(artifacts, 'cover-mobile.png') });
    const browserJson = url => page.evaluate(async url => {
      const response = await fetch(url);
      if (!response.ok) throw new Error(`HTTP ${response.status}: ${url}`);
      return response.json();
    }, url);
    const checked = [];
    for (const episode of feed.episodes) {
      assert.match(episode.guid, /^urn:uuid:/);
      const day = new URL(episode.edition).pathname.split('/').filter(Boolean).join('-');
      const datePath = day.replaceAll('-', '/');
      const chapters = await browserJson(localAsset(episode.chapters));
      assert.equal(chapters.chapters.length, 23);
      assert.equal(chapters.chapters[0].startTime, 0);
      await page.goto(target);
      await page.locator(`.archive a[href="${datePath}/"]`).click();
      assert.equal(page.url(), localAsset(episode.edition));
      assert.equal(await page.getByRole('link', { name: /Public story archive & site source/ }).getAttribute('href'),
        'https://github.com/robertmeta/trendingnotpeak.com');
      const record = await browserJson(new URL(`data/${day}.json`, target).href);
      assert.equal(episode.storyLinks.length, 20);
      assert.equal(episode.transcript, new URL(`transcripts/${day}.txt`, target).href);
      for (const number of [1, 10, 20]) {
        const storyLink = episode.storyLinks[number - 1];
        assert.equal(storyLink.href, `${episode.edition}#${number}`);
        await page.goto(storyLink.href);
        const story = page.locator(`article.story[id="${number}"]`);
        assert.equal(await story.locator('h2').innerText(), record.stories[number - 1].title);
        assert.ok(await story.getByRole('heading', { name: 'Sources & further reading' }).isVisible());
      }
      assert.equal(await page.getByRole('link', { name: 'Download the MP3 ↗', exact: true }).getAttribute('href'), episode.audio);
      const audioResponse = await page.request.get(episode.audio);
      assert.ok(audioResponse.ok());
      const audio = await audioResponse.body();
      assert.equal(audio.length, episode.bytes);
      assert.equal(digest(audio), record.audio.sha256);
      await page.getByRole('link', { name: 'Transcript ↗', exact: true }).click();
      assert.match(await page.locator('body').innerText(), /Intelligrit/);
      const transcript = await page.locator('body').innerText();
      await page.reload();
      assert.equal(await page.locator('body').innerText(), transcript);
      checked.push({ day, guid: episode.guid, audio_sha256: digest(audio), story_links: 20 });
    }
    const result = { result: 'passed', site: target, dns_override: dnsOverride, feed: new URL('feed.xml', target).href,
      episodes: checked, checks: ['mobile-rss-navigation', 'feed-reload',
        'approved-email', '3000px-cover', '23-chapters-each', '20-story-detail-links-each',
        'actual-mp3-hash-each', 'transcript-reload-each'] };
    fs.writeFileSync(path.join(artifacts, 'journey.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
