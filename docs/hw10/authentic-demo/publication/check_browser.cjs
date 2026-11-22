const {chromium}=require(process.env.PLAYWRIGHT_CORE_PATH);
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const live=process.argv.includes('--live'),label=live?'public':'local';
const base=live?'https://esst-prog2.github.io/RC_ATLAS_Project/':'http://127.0.0.1:8790/';
async function main(){
 const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
 try{
  const context=await browser.newContext({viewport:{width:1440,height:1000}}),page=await context.newPage();
  const result={url:base,errors:[],layouts:[],navigation:[]};page.on('pageerror',e=>result.errors.push(e.message));
  await page.goto(base,{waitUntil:'networkidle'});
  const source=await page.locator('video source').getAttribute('src');assert.ok(source.includes('authentic-cc8dbe3276a7'));
  const response=await context.request.get(new URL(source,base).href);
  result.video_sha256=crypto.createHash('sha256').update(await response.body()).digest('hex');
  assert.equal(result.video_sha256,'cc8dbe3276a7c4ca8dc580e683b0a85852a99342f95327cb4b85a67452efc574');
  await page.keyboard.press('Tab');await page.keyboard.press('Enter');
  assert.equal(await page.evaluate(()=>document.activeElement.id),'main');result.skip_link=true;
  for(const href of ['#capabilities','#workflow','#explore']){
   await page.locator(`header nav a[href="${href}"]`).click();assert.equal(new URL(page.url()).hash,href);result.navigation.push(href);
  }
  await page.locator('a[href="#video"]').click();assert.equal(new URL(page.url()).hash,'#video');
  await page.locator('video').evaluate(async v=>{v.load();await v.play()});
  await page.waitForFunction(()=>document.querySelector('video').currentTime>0.2);
  result.media=await page.locator('video').evaluate(v=>({duration:v.duration,width:v.videoWidth,height:v.videoHeight,currentSrc:v.currentSrc,controls:v.controls,playsinline:v.playsInline}));
  assert.equal(result.media.duration,29.8);assert.equal(result.media.width,1920);assert.equal(result.media.height,1080);
  await page.locator('video').evaluate(v=>{v.pause();v.currentTime=17.5});
  await page.waitForFunction(()=>{const v=document.querySelector('video');return !v.seeking&&Math.abs(v.currentTime-17.5)<.1});result.seeking=true;
  await page.locator('video').focus();await page.keyboard.press('Space');await page.waitForFunction(()=>!document.querySelector('video').paused);
  await page.keyboard.press('Space');await page.waitForFunction(()=>document.querySelector('video').paused);result.keyboard_controls=true;
  await page.locator('.video-transcript summary').focus();await page.keyboard.press('Enter');
  assert.equal(await page.locator('.video-transcript').evaluate(e=>e.open),true);result.transcript_keyboard=true;
  assert.ok((await page.locator('.transcript-content').innerText()).includes('Task completion does not establish indicator outcomes.'));
  await page.keyboard.press('Enter');
  for(const width of [1440,390,320]){
   await page.setViewportSize({width,height:1000});await page.locator('video').scrollIntoViewIfNeeded();
   const layout=await page.evaluate(()=>({width:innerWidth,document:document.documentElement.scrollWidth,video:document.querySelector('video').getBoundingClientRect().width,logoLoaded:document.querySelector('.brand img').naturalWidth>0,cssLoaded:!!document.querySelector('link[rel="stylesheet"]').sheet}));
   assert.ok(layout.document<=width&&layout.video<=width&&layout.logoLoaded&&layout.cssLoaded);result.layouts.push(layout);
   if(width!==320)await page.screenshot({path:path.join(__dirname,`${label}-${width}.png`)});
  }
  await page.setViewportSize({width:1440,height:1000});
  await page.locator('video').evaluate(async v=>{v.currentTime=0;await v.play()});
  await page.waitForFunction(()=>document.querySelector('video').ended,{},{timeout:45000});
  result.playback=await page.locator('video').evaluate(v=>({ended:v.ended,time:v.currentTime,error:v.error}));assert.equal(result.playback.error,null);
  const poster=await page.locator('video').getAttribute('poster');assert.equal((await context.request.get(new URL(poster,base).href)).status(),200);
  const range=await context.request.get(new URL(source,base).href,{headers:{Range:'bytes=0-1023'}});assert.equal(range.status(),206);assert.equal((await range.body()).length,1024);result.range_206=true;
  assert.equal(result.errors.length,0);result.status='PASS';
  fs.writeFileSync(path.join(__dirname,`${label}-browser.json`),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{await browser.close();}
}
main().catch(e=>{console.error(e);process.exitCode=1});
