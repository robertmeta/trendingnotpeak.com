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
      const item = channel.querySelector('item');
      const itunes = 'http://www.itunes.com/dtds/podcast-1.0.dtd';
      const podcast = 'https://podcastindex.org/namespace/1.0';
      return {
        owner: channel.getElementsByTagNameNS(itunes, 'email')[0].textContent,
        cover: channel.getElementsByTagNameNS(itunes, 'image')[0].getAttribute('href'),
        guid: item.querySelector('guid').textContent,
        audio: item.querySelector('enclosure').getAttribute('url'),
        bytes: Number(item.querySelector('enclosure').getAttribute('length')),
        transcript: item.getElementsByTagNameNS(podcast, 'transcript')[0].getAttribute('url'),
        chapters: item.getElementsByTagNameNS(podcast, 'chapters')[0].getAttribute('url'),
      };
    }, xml);
    assert.equal(feed.owner, 'podcasts@robertmelton.com');
    assert.match(feed.guid, /^urn:uuid:/);
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
    const chapters = await browserJson(localAsset(feed.chapters));
    assert.equal(chapters.chapters.length, 23);
    assert.equal(chapters.chapters[0].startTime, 0);
    await page.goto(target);
    await page.locator('.archive').getByRole('link', { name: /October 29, 2026/ }).click();
    const record = await browserJson(new URL('data/2026-10-29.json', target).href);
    assert.equal(await page.getByRole('link', { name: 'Download the MP3 ↗', exact: true }).getAttribute('href'), feed.audio);
    const audioResponse = await page.request.get(feed.audio);
    assert.ok(audioResponse.ok());
    const audio = await audioResponse.body();
    assert.equal(audio.length, feed.bytes);
    assert.equal(digest(audio), record.audio.sha256);
    await page.getByRole('link', { name: 'Transcript ↗', exact: true }).click();
    assert.match(await page.locator('body').innerText(), /Intelligrit/);
    const transcript = await page.locator('body').innerText();
    await page.reload();
    assert.equal(await page.locator('body').innerText(), transcript);
    const result = { result: 'passed', site: target, dns_override: dnsOverride, feed: new URL('feed.xml', target).href,
      guid: feed.guid, audio_sha256: digest(audio), checks: ['mobile-rss-navigation', 'feed-reload',
        'approved-email', '3000px-cover', '23-chapters', 'actual-mp3-hash', 'transcript-reload'] };
    fs.writeFileSync(path.join(artifacts, 'journey.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
