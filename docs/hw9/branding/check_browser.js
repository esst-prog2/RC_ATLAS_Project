(() => {
  const logo = document.querySelector('.brand img');
  const rect = logo.getBoundingClientRect();
  return JSON.stringify({
    url: location.href, width: innerWidth, height: innerHeight,
    overflow: document.documentElement.scrollWidth > innerWidth,
    logo: {loaded: logo.complete && logo.naturalWidth > 0, source: logo.currentSrc,
      width: rect.width, height: rect.height, ratio: rect.width / rect.height,
      objectFit: getComputedStyle(logo).objectFit, alt: logo.alt},
    brandName: document.querySelector('.brand').textContent.trim(),
    mainCount: document.querySelectorAll('main').length,
    headingCount: document.querySelectorAll('h1').length,
    navHits: [...document.querySelectorAll('header nav a')].map(a => ({
      label: a.textContent.trim(), width: a.getBoundingClientRect().width,
      height: a.getBoundingClientRect().height})),
    brokenAnchors: [...document.querySelectorAll('a[href^="#"]')]
      .filter(a => !document.getElementById(a.hash.slice(1))).map(a => a.hash),
    favicon: [...document.querySelectorAll('link[rel="icon"]')].map(a => a.href),
    heroInset: document.querySelector('.hero .wrap').getBoundingClientRect().left,
    sectionPadding: [...document.querySelectorAll('.section')].map(s => getComputedStyle(s).paddingTop),
    definitionPadding: [...document.querySelectorAll('dl > div')].map(s => getComputedStyle(s).paddingBottom)
  }, null, 2);
})()
