// Exercise the real MP3 in WebKit with touch input, not just a narrow viewport.
const { webkit, devices } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createHash } = require('node:crypto');
const url = process.env.TNP_TEST_URL;
if (!url) throw new Error('Set TNP_TEST_URL to the site root, including its trailing slash');
const artifacts = process.env.TNP_TEST_ARTIFACTS || path.resolve('.cache/mobile-audio');

(async () => {
  fs.mkdirSync(artifacts, { recursive: true });
  const browser = await webkit.launch({ headless: true, executablePath: process.env.TNP_WEBKIT_EXECUTABLE });
  const page = await browser.newPage(devices['iPhone 13']);
  page.setDefaultTimeout(15000);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  try {
    await page.goto(url);
    await page.locator('.archive').getByRole('link', { name: /October 29, 2026/ }).tap();
    const audio = page.locator('audio');
    // iOS may wait for a user gesture before loading metadata.
    await page.getByRole('button', { name: 'Play episode', exact: true }).tap();
    await page.waitForFunction(() => document.querySelector('audio').currentTime > 1);
    const duration = await audio.evaluate(element => element.duration);
    await page.getByRole('button', { name: 'Pause episode', exact: true }).tap();
    assert.ok(await audio.evaluate(element => element.paused));
    const seek = page.getByRole('slider', { name: 'Seek through episode' });
    const box = await seek.boundingBox();
    await seek.tap({ position: { x: box.width / 2, y: box.height / 2 } });
    await page.waitForFunction(() => document.querySelector('audio').currentTime > 20);
    const seekTime = await audio.evaluate(element => element.currentTime);
    await page.getByRole('button', { name: 'Play episode', exact: true }).tap();
    await page.waitForFunction(time => document.querySelector('audio').currentTime > time + 1, seekTime);
    await page.getByRole('button', { name: 'Pause episode', exact: true }).tap();
    await page.getByRole('button', { name: 'Mute', exact: true }).tap();
    assert.ok(await audio.evaluate(element => element.muted));
    await page.getByRole('button', { name: 'Unmute', exact: true }).tap();
    assert.ok(await audio.evaluate(element => !element.muted));
    await page.getByRole('button', { name: 'Restart episode', exact: true }).tap();
    assert.equal(await audio.evaluate(element => element.currentTime), 0);
    await page.reload();
    await page.getByRole('button', { name: 'Play episode', exact: true }).tap();
    await page.waitForFunction(() => document.querySelector('audio').currentTime > 1);
    await page.getByRole('button', { name: 'Pause episode', exact: true }).tap();
    await page.locator('.listen').screenshot({ path: path.join(artifacts, 'iphone-player.png') });
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    const pending = page.waitForEvent('download');
    await page.getByRole('link', { name: 'Download the MP3' }).tap();
    const download = await pending;
    const file = path.join(artifacts, download.suggestedFilename());
    await download.saveAs(file);
    const bytes = fs.readFileSync(file);
    await page.getByRole('link', { name: 'Story data' }).tap();
    await page.waitForURL('**/data/2026-10-29.json');
    const record = JSON.parse(await page.locator('body').innerText());
    assert.equal(bytes.length, record.audio.bytes);
    assert.equal(createHash('sha256').update(bytes).digest('hex'), record.audio.sha256);
    assert.ok(Math.abs(duration - record.audio.duration_seconds) < 0.1);
    assert.equal(record.audio.embedded_chapters, 22);
    assert.deepEqual(errors, []);
    const result = { result: 'passed', engine: 'webkit', device: 'iPhone 13 emulation', url,
      duration, checks: ['home-to-edition', 'touch-play-pause', 'touch-seek-resume', 'mute', 'restart', 'reload-play', 'mp3-download-hash', 'mobile-overflow'], errors };
    fs.writeFileSync(path.join(artifacts, 'journey.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result));
  } catch (error) {
    console.error(JSON.stringify(await page.locator('audio').evaluate(a => ({ paused: a.paused, time: a.currentTime, readyState: a.readyState, error: a.error?.code })).catch(() => ({ url: page.url() }))));
    await page.screenshot({ path: path.join(artifacts, 'failure.png') });
    throw error;
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
