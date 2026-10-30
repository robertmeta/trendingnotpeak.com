// Render the editable SVG with the bundled font. Uses an existing Playwright install.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const source = process.env.TNP_COVER_URL;
if (!source) throw new Error('Set TNP_COVER_URL to the served assets/cover.svg');
(async () => {
  const browser = await chromium.launch({ headless: false });
  try {
    const page = await browser.newPage({ viewport: { width: 3000, height: 3000 }, deviceScaleFactor: 1 });
    await page.goto(source);
    await page.evaluate(() => document.fonts.ready);
    assert.ok(await page.evaluate(() => [...document.fonts].some(f => f.family === 'Pixelify' && f.status === 'loaded')));
    await page.screenshot({ path: path.resolve(__dirname, '../assets/cover.png'), omitBackground: false });
    console.log('Rendered 3000×3000 cover.png with the bundled Pixelify font.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
