const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const root = process.env.TNP_TEST_URL;
if (!root) throw new Error('Set TNP_TEST_URL to the site root with a trailing slash');
const artifacts = process.env.TNP_TEST_ARTIFACTS || path.resolve('.cache/discovery-journey');

(async () => {
  fs.mkdirSync(artifacts, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  try {
    const image = async () => {
      const url = await page.locator('meta[property="og:image"]').getAttribute('content');
      assert.match(url, /^https:\/\/trendingnotpeak\.com\/assets\/share-card\.png\?v=/);
      assert.equal(await page.locator('meta[name="twitter:image"]').getAttribute('content'), url);
      const asset = new URL(url);
      const response = await page.request.get(new URL(asset.pathname + asset.search, root).href);
      assert.equal(response.status(), 200);
      const bytes = await response.body();
      assert.equal(bytes.readUInt32BE(16), 1200);
      assert.equal(bytes.readUInt32BE(20), 630);
      return url;
    };

    await page.goto(root);
    await page.getByRole('heading', { name: 'Early signals. Useful details.' }).waitFor();
    assert.equal(await page.locator('meta[property="og:url"]').getAttribute('content'), 'https://trendingnotpeak.com/');
    const shareImage = await image();
    assert.match(await page.locator('footer').innerText(), /CC BY 4\.0/);
    assert.match(await page.locator('footer').innerText(), /MIT/);
    const search = page.getByRole('search', { name: 'Search every edition with DuckDuckGo' });
    assert.equal(await search.count(), 1);
    let searchUrl;
    await page.route('https://duckduckgo.com/**', route => {
      searchUrl = route.request().url();
      route.fulfill({ status: 200, contentType: 'text/html', body: '<title>Search submitted</title>' });
    });
    await search.getByRole('searchbox').fill('tinygrad');
    await search.getByRole('button', { name: 'Search' }).click();
    await page.waitForURL('https://duckduckgo.com/**');
    assert.equal(new URL(searchUrl).searchParams.get('q'), 'tinygrad site:trendingnotpeak.com');

    await page.goto(new URL('2026/10/30/#3', root).href);
    await page.locator('article[id="3"]').waitFor();
    assert.equal(await page.locator('meta[property="og:url"]').getAttribute('content'), 'https://trendingnotpeak.com/2026/10/30/');
    assert.equal(await image(), shareImage);
    assert.equal(await page.locator('link[rel="license"]').getAttribute('href'), 'https://creativecommons.org/licenses/by/4.0/');
    const license = page.getByRole('link', { name: 'Reuse details' });
    assert.match(await license.getAttribute('href'), /LICENSE-CONTENT\.md$/);

    for (const [file, pattern] of [
      ['robots.txt', /User-agent: \*\s+Allow: \/\s+Sitemap:/],
      ['llms.txt', /transcripts\/2026-10-30\.txt/],
      ['sitemap.xml', /https:\/\/trendingnotpeak\.com\/2026\/10\/30\//],
    ]) {
      const response = await page.request.get(new URL(file, root).href);
      assert.equal(response.status(), 200, file);
      assert.match(await response.text(), pattern, file);
    }

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(root);
    await search.getByRole('searchbox').fill('tinygrad');
    assert.equal(await search.getByRole('button', { name: 'Search' }).isVisible(), true);
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await page.locator('footer').screenshot({ path: path.join(artifacts, 'footer-mobile.png') });
    fs.writeFileSync(path.join(artifacts, 'result.json'), JSON.stringify({ root, shareImage, searchUrl, checked: ['share image', 'license', 'site search', 'robots', 'llms', 'sitemap', 'mobile'] }, null, 2));
    console.log(`Discovery journey passed: ${root}`);
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
