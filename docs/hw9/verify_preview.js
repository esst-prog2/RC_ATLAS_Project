(() => {
const anchors=[...document.querySelectorAll('a[href]')];
const broken=anchors.filter(a=>a.getAttribute('href').startsWith('#')&&!document.getElementById(a.hash.slice(1))).map(a=>a.getAttribute('href'));
const elements=[...document.querySelectorAll('.site *')].filter(e=>!e.classList.contains('sr')&&!e.classList.contains('skip'));
const overflow=elements.filter(e=>{const b=e.getBoundingClientRect();return b.width>0&&(b.right>innerWidth+1||b.left < -1)}).slice(0,10).map(e=>e.tagName+'.'+e.className);
function rgb(s){return (s.match(/[\d.]+/g)||[]).slice(0,3).map(Number)}
function lum(a){return a.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0)}
const lowContrast=[];
for(const e of elements){if(![...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim()))continue;const s=getComputedStyle(e);if(s.display==='none'||s.visibility==='hidden')continue;let p=e,bg;while(p){bg=getComputedStyle(p).backgroundColor;if(bg!=='rgba(0, 0, 0, 0)'&&bg!=='transparent')break;p=p.parentElement;}const a=lum(rgb(s.color)),b=lum(rgb(bg||'rgb(255,255,255)'));const ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);const large=parseFloat(s.fontSize)>=24||(parseFloat(s.fontSize)>=18.66&&parseInt(s.fontWeight)>=700);if(ratio<(large?3:4.5))lowContrast.push({text:e.textContent.trim().slice(0,55),ratio:ratio.toFixed(2)});}
return JSON.stringify({page:location.pathname,viewport:[innerWidth,innerHeight],documentWidth:document.documentElement.scrollWidth,h1Count:document.querySelectorAll('h1').length,headline:document.querySelector('h1')?.textContent,brokenAnchors:broken,overflow,lowContrast,remoteResources:performance.getEntriesByType('resource').filter(r=>!r.name.startsWith(location.origin)).map(r=>r.name),links:[...new Set(anchors.map(a=>a.getAttribute('href')))]},null,2);
})()
