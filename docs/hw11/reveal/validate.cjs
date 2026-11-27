const {chromium}=require('C:/Users/Elitebook/AppData/Local/OpenAI/Codex/runtimes/cua_node/9c26d707817e90a7/bin/node_modules/playwright-core');
const fs=require('fs'),path=require('path');
(async()=>{
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
const ctx=await browser.newContext({viewport:{width:1920,height:1080}});
const errors=[],requests=[];
const page=await ctx.newPage();page.on('pageerror',e=>errors.push(String(e)));page.on('request',r=>{if(!r.url().startsWith('data:'))requests.push(r.url())});
await page.goto('http://127.0.0.1:8871/RC_ATLAS_Project/slides/');
await page.waitForFunction(()=>window.Reveal?.isReady());
if(await page.evaluate(()=>Reveal.getTotalSlides())!==6)throw Error('Wrong slide count');
await page.screenshot({path:path.join(__dirname,'preview/01-for-whom.png')});
await page.keyboard.press('ArrowRight');
for(let i=0;i<6;i++){
await page.waitForFunction(k=>document.querySelector('#demo').dataset.stage===String(k),i);
await page.locator('#stage-image').evaluate(img=>img.decode());
await page.screenshot({path:path.join(__dirname,`preview/02-demo-${i+1}.png`)});
if(await page.evaluate(()=>Reveal.getIndices().h)!==1)throw Error('Demo escaped slide 2');
await page.keyboard.press('ArrowRight');
}
for(let i=2;i<6;i++){
await page.waitForFunction(k=>Reveal.getIndices().h===k,i);
await page.screenshot({path:path.join(__dirname,`preview/0${i+1}-slide.png`)});
if(i<5)await page.keyboard.press('ArrowRight');
}
await page.keyboard.press('ArrowLeft');if(await page.evaluate(()=>Reveal.getIndices().h)!==4)throw Error('Back navigation');
await page.keyboard.press('n');await page.locator('dialog[open]').waitFor();
const notes=await page.locator('#notesText').innerText();if(!notes.includes('future work'))throw Error('Wrong notes');
await page.keyboard.press('Escape');
await page.goto('file:///'+path.join(__dirname,'slides/index.html').replaceAll('\\','/'));
await page.waitForFunction(()=>window.Reveal?.isReady());
await page.keyboard.press('ArrowRight');await page.keyboard.press('Space');
await page.waitForFunction(()=>document.querySelector('#demo').dataset.stage==='1');
const checks=await page.evaluate(()=>({slideCount:Reveal.getTotalSlides(),embeddedImages:[...document.images].every(i=>i.complete&&i.naturalWidth>0),timings:[...document.querySelectorAll('.slides>section[data-timing]')].map(s=>Number(s.dataset.timing)),externalResources:[...document.querySelectorAll('script[src],link[rel=stylesheet]')].length}));
if(errors.length||checks.externalResources||!checks.embeddedImages)throw Error(JSON.stringify({errors,checks}));
fs.writeFileSync(path.join(__dirname,'evidence/browser-validation.json'),JSON.stringify({checks,errors,requests:requests.filter(r=>!r.startsWith('file:')),keyboard:'ArrowRight, ArrowLeft, Space, N and Escape checked',demo:'six stages on one substantive slide',offline:'file:// load and fragment progression passed',viewport:'1920x1080'},null,2));
console.log(JSON.stringify(checks));await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
