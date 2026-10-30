const {chromium, webkit, devices} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const url = process.env.TNP_TEST_URL;
if (!url) throw new Error('Set TNP_TEST_URL to the site root, including its trailing slash');
const artifacts = process.env.TNP_TEST_ARTIFACTS || path.resolve('.cache/reel-motion');
fs.mkdirSync(artifacts, {recursive:true});
(async()=>{
  const results=[];
  for (const [engine, type] of [['chromium',chromium],['webkit',webkit]]) {
    const browser=await type.launch({headless:false,...(engine==='webkit'?{executablePath:process.env.TNP_WEBKIT_EXECUTABLE}:{args:['--mute-audio']})});
    try {
      for (const [scenario, reducedMotion, oldPreference] of [['normal','no-preference',null],['reduced','reduce',null],['saved-off','no-preference','off']]) {
        const context=await browser.newContext({...devices['iPhone 13'],reducedMotion});
        if (oldPreference) await context.addInitScript(value=>localStorage.setItem('tnp-reel-motion',value),oldPreference);
        const page=await context.newPage();page.setDefaultTimeout(10000);
        const prefix=path.join(artifacts,`${engine}-${scenario}`);
        try {
          await page.goto(url);
          await page.locator('.archive').getByRole('link',{name:/October 29, 2026/}).tap();
          await page.locator('.cassette').scrollIntoViewIfNeeded();
          await page.getByRole('button',{name:'Play episode',exact:true}).tap();
          await page.waitForFunction(()=>document.querySelector('audio').currentTime>1);
          // Fixed inner-reel crops exclude timers, buttons, and tape-size changes.
          const clips=await page.locator('.reel').evaluateAll(els=>els.map(el=>{const r=el.getBoundingClientRect(),s=Math.floor(el.offsetWidth*.75);return {x:Math.round(r.x+r.width/2-s/2),y:Math.round(r.y+r.height/2-s/2),width:s,height:s};}));
          const first=[];
          for (let i=0;i<clips.length;i++) first.push(await page.screenshot({clip:clips[i],path:`${prefix}-reel${i}-playing1.png`}));
          const start=await page.locator('audio').evaluate(a=>a.currentTime);
          await page.waitForFunction(t=>document.querySelector('audio').currentTime>t+.13,start);
          for (let i=0;i<clips.length;i++) {
            const next=await page.screenshot({clip:clips[i],path:`${prefix}-reel${i}-playing2.png`});
            assert.ok(!first[i].equals(next),`${engine}/${scenario}: reel ${i} must visibly rotate without a setting change`);
          }
          await page.getByRole('button',{name:'Pause episode',exact:true}).tap();
          await page.getByRole('button',{name:'Play episode',exact:true}).waitFor();
          // Allow the last pause/timeupdate to settle before testing stationary pixels.
          await page.waitForFunction(()=>{const a=document.querySelector('audio');return a.paused&&document.querySelector('[data-elapsed]').textContent===`${Math.floor(a.currentTime/60)}:${String(Math.floor(a.currentTime%60)).padStart(2,'0')}`;});
          const paused=await page.screenshot({clip:clips[0],path:`${prefix}-paused1.png`});
          const now=await page.evaluate(()=>performance.now());
          await page.waitForFunction(t=>performance.now()>t+250,now,{polling:50});
          assert.ok(paused.equals(await page.screenshot({clip:clips[0],path:`${prefix}-paused2.png`})),`${engine}/${scenario}: paused reel must stay still`);
          await page.getByRole('combobox',{name:'Playback speed'}).selectOption('1.5');
          await page.reload();
          assert.equal(await page.getByRole('combobox',{name:'Playback speed'}).inputValue(),'1.5');
          await page.getByRole('button',{name:'Play episode',exact:true}).tap();
          await page.waitForFunction(()=>document.querySelector('audio').currentTime>1);
          assert.equal(await page.locator('audio').evaluate(a=>a.playbackRate),1.5);
          const before=await page.locator('.reel').first().evaluate(e=>getComputedStyle(e).transform);
          const t=await page.locator('audio').evaluate(a=>a.currentTime);
          await page.waitForFunction(t=>document.querySelector('audio').currentTime>t+.15,t);
          assert.notEqual(await page.locator('.reel').first().evaluate(e=>getComputedStyle(e).transform),before);
          await page.getByRole('button',{name:'Pause episode',exact:true}).tap();
          results.push({engine,scenario,passed:true});
        } catch(error) {
          results.push({engine,scenario,passed:false,error:error.message,state:await page.locator('audio').evaluate(a=>({time:a.currentTime,paused:a.paused,reduce:matchMedia('(prefers-reduced-motion: reduce)').matches,motion:document.querySelector('#episode-motion')?.checked})).catch(()=>null)});
        } finally {await context.close();}
      }
    } finally {await browser.close();}
  }
  fs.writeFileSync(path.join(artifacts,'journey.json'),JSON.stringify({url,results},null,2));
  console.log(JSON.stringify({url,results}));
  assert.ok(results.every(r=>r.passed),'Every default playback state must paint moving reels');
})().catch(e=>{console.error(e);process.exitCode=1;});
