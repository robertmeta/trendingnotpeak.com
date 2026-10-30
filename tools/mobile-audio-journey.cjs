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
  const browser = await webkit.launch({ headless: false, executablePath: process.env.TNP_WEBKIT_EXECUTABLE });
  const page = await browser.newPage(devices['iPhone 13']);
  page.setDefaultTimeout(15000);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  try {
    await page.goto(url);
    await page.locator('.archive').getByRole('link', { name: /October 29, 2026/ }).tap();
    const audio = page.locator('audio');
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    const speed = page.getByRole('combobox', { name: 'Playback speed' });
    await speed.selectOption('1.5');
    assert.equal(await audio.evaluate(a => a.playbackRate), 1.5);
    // iOS may wait for a user gesture before loading metadata.
    await page.getByRole('button', { name: 'Play episode', exact: true }).tap();
    await page.waitForFunction(() => document.querySelector('audio').currentTime > 1);
    const duration = await audio.evaluate(element => element.duration);
    const pacing = await page.evaluate(() => ({ time: document.querySelector('audio').currentTime, clock: performance.now() }));
    await page.waitForFunction(t => document.querySelector('audio').currentTime > t + 1.5, pacing.time);
    const actualRate = await page.evaluate(before => (document.querySelector('audio').currentTime - before.time) / ((performance.now() - before.clock) / 1000), pacing);
    assert.ok(actualRate > 1.25 && actualRate < 1.75, `Expected actual 1.5× playback, observed ${actualRate}`);
    for (const value of ['0.75', '1', '1.25', '1.75', '2', '1.5']) {
      await speed.selectOption(value);
      assert.equal(await audio.evaluate(a => a.playbackRate), Number(value));
    }
    const rotation = await page.locator('.reel').first().evaluate(el => getComputedStyle(el).transform);
    const start = await audio.evaluate(a => a.currentTime);
    await page.waitForFunction(t => document.querySelector('audio').currentTime > t + .6, start);
    assert.notEqual(await page.locator('.reel').first().evaluate(el => getComputedStyle(el).transform), rotation);
    await page.getByRole('button', { name: 'Pause episode', exact: true }).tap();
    assert.ok(await audio.evaluate(element => element.paused));
    // Wait for the pause event to update the UI and WebKit's final media clock.
    await page.waitForFunction(() => document.querySelector('[data-play]').getAttribute('aria-label') === 'Play episode' && document.querySelector('.cassette').style.getPropertyValue('--rotation') === `${(document.querySelector('audio').currentTime * 300) % 360}deg`);
    const pausedRotation = await page.locator('.reel').first().evaluate(el => getComputedStyle(el).transform);
    await page.evaluate(() => new Promise(resolve => { let frames = 0; const tick = () => ++frames === 8 ? resolve() : requestAnimationFrame(tick); requestAnimationFrame(tick); }));
    assert.equal(await page.locator('.reel').first().evaluate(el => getComputedStyle(el).transform), pausedRotation);

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
    assert.equal(await speed.inputValue(), '1.5');
    assert.equal(await audio.evaluate(a => a.playbackRate), 1.5);
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
    assert.equal(record.audio.embedded_chapters, 23);
    assert.deepEqual(errors, []);
    const result = { result: 'passed', engine: 'webkit', device: 'iPhone 13 emulation', url,
      duration, checks: ['home-to-edition', 'touch-play-pause', 'touch-seek-resume', 'mute', 'restart', 'reload-play', 'reel-rotation', 'speed-persistence', 'mp3-download-hash', 'mobile-overflow'], errors };
    fs.writeFileSync(path.join(artifacts, 'journey.json'), JSON.stringify(result, null, 2));
    console.log(JSON.stringify(result));
  } catch (error) {
    console.error(JSON.stringify(await page.locator('audio').evaluate(a => ({ paused: a.paused, time: a.currentTime, readyState: a.readyState, error: a.error?.code })).catch(() => ({ url: page.url() }))));
    await page.screenshot({ path: path.join(artifacts, 'failure.png') });
    throw error;
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
