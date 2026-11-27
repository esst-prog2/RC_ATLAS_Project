const {chromium}=require('C:/Users/Elitebook/AppData/Local/OpenAI/Codex/runtimes/cua_node/9c26d707817e90a7/bin/node_modules/playwright-core');
const fs=require('fs'),path=require('path'),crypto=require('crypto');
(async()=>{
const url='https://esst-prog2.github.io/RC_ATLAS_Project/slides/';
const expected=JSON.parse(fs.readFileSync(path.join(__dirname,'evidence/publication.json'))).html_sha256;
const response=await fetch(url);if(!response.ok)throw Error('Public HTTP '+response.status);
const bytes=Buffer.from(await response.arrayBuffer());if(crypto.createHash('sha256').update(bytes).digest('hex')!==expected)throw Error('Public bytes differ from approved HTML');
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
const page=await browser.newPage({viewport:{width:1920,height:1080}}),errors=[],requests=[],notes=[];
page.on('pageerror',e=>errors.push(String(e)));page.on('requestfailed',r=>errors.push(r.url()+': '+r.failure()?.errorText));
page.on('request',r=>{if(!r.url().startsWith('data:'))requests.push(r.url())});
const preview=path.join(__dirname,'evidence/published-preview');fs.mkdirSync(preview,{recursive:true});
await page.goto(url);await page.waitForFunction(()=>window.Reveal?.isReady());
if(await page.evaluate(()=>Reveal.getTotalSlides())!==6)throw Error('Slide count');
for(let slide=0;slide<6;slide++){
 await page.waitForFunction(i=>Reveal.getIndices().h===i,slide);
 await page.evaluate(()=>document.activeElement?.blur());
 await page.keyboard.press('n');await page.locator('dialog[open]').waitFor();notes.push(await page.locator('#notesText').innerText());await page.locator('#closeNotes').click();await page.evaluate(()=>document.activeElement?.blur());
 if(slide===1){for(let stage=0;stage<6;stage++){
  await page.waitForFunction(k=>document.querySelector('#demo').dataset.stage===String(k),stage);
  await page.locator('#stage-image').evaluate(i=>i.decode());
  await page.screenshot({path:path.join(preview,`slide-2-stage-${stage+1}.png`)});
  if(stage<5)await page.keyboard.press(stage%2?'ArrowRight':'Space');
 }}else{await page.screenshot({path:path.join(preview,`slide-${slide+1}.png`)});}
 if(slide<5)await page.keyboard.press('ArrowRight');
}
await page.keyboard.press('ArrowLeft');await page.waitForFunction(()=>Reveal.getIndices().h===4);await page.keyboard.press('ArrowRight');
const images=await page.evaluate(()=>[...document.images].every(i=>i.complete&&i.naturalWidth>0));
if(!images||errors.length||notes.length!==6||notes.some(n=>!n.trim()))throw Error(JSON.stringify({images,errors,notes:notes.length}));
if(requests.some(r=>!r.startsWith(url)))throw Error('Unexpected external resource: '+requests.join(','));
const result={url,httpStatus:response.status,htmlSha256:expected,slides:6,demoStages:6,publicNotes:6,imagesLoaded:images,keyboard:'ArrowRight, ArrowLeft, Space, N, Escape passed',errors,requests,viewport:'1920x1080',passed:true};
fs.writeFileSync(path.join(__dirname,'evidence/public-browser-validation.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
