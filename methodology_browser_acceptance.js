// Installed Chrome against the independently verified disposable PostgreSQL API.
const fs = require('fs');
const path = require('path');
const {chromium} = require(process.env.PLAYWRIGHT_CORE_PATH);
const base = process.env.RCATLAS_BASE_URL;
const evidence = process.env.RCATLAS_EVIDENCE_DIR;
if (!base || !evidence || !process.env.RCATLAS_CHROME_PATH) throw new Error('Explicit disposable browser settings required.');
fs.mkdirSync(evidence, {recursive: true});
const checks = [];
function assert(condition, message) { if (!condition) throw new Error(message); }
function passed(id, detail) { checks.push({id, status:'PASS', detail}); }

(async () => {
  const browser = await chromium.launch({executablePath:process.env.RCATLAS_CHROME_PATH, headless:true,
    args:['--no-first-run', '--disable-default-apps']});
  const context = await browser.newContext({viewport:{width:1366, height:768}});
  const page = await context.newPage();
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  const report = {browser:browser.version(), synthetic_only:true, checks, status:'RUNNING'};
  async function waitReady() {
    await page.waitForFunction(() => !document.getElementById('methodologyExplainBtn').disabled &&
      !document.getElementById('methodologyFeedback').textContent.includes('Loading'), {timeout:15000});
  }
  async function period() {
    await page.locator('#methodologyStart').fill('2026-09-01');
    await page.locator('#methodologyEnd').fill('2026-09-30');
    await page.locator('#methodologyAsOf').fill('2026-09-30T23:59:59');
  }
  async function inspect() {
    const response = page.waitForResponse(r => r.url().includes('/calculation?') && r.request().method() === 'GET');
    await page.locator('#methodologyExplainBtn').focus();
    await page.keyboard.press('Enter');
    const actual = await response;
    assert(actual.status() === 200, 'Calculation request failed.');
    const body = await actual.json();
    await page.waitForFunction(() => document.getElementById('methodologyResult').textContent.length > 0);
    return body.result;
  }
  async function shot(name) {
    await page.locator('#methodologyPanel').screenshot({path:path.join(evidence,name)});
  }
  try {
    await page.goto(base + '/studio', {waitUntil:'networkidle'});
    await page.locator('#splashScreen').waitFor({state:'hidden'});
    await page.locator('#bootstrapUsername').fill('method.meal@example.test');
    await page.locator('#bootstrapPassword').fill('Synthetic-Methodology-Only-2026!');
    await page.locator('#loginBtn').click();
    await page.locator('#appShell').waitFor({state:'visible',timeout:20000});
    const cookies = await context.cookies();
    assert(cookies.some(c => c.name === 'rcatlas_session_dev' && c.httpOnly), 'HttpOnly session missing.');
    assert(await page.evaluate(() => localStorage.getItem('rcatlas.authToken')) === null, 'Persistent bearer token found.');
    passed('CHROME_COOKIE_LOGIN', 'Studio login with HttpOnly session and no localStorage bearer token.');
    await page.locator('button[data-view="indicator-intelligence"]').first().click();
    await page.locator('#methodologyPanel').waitFor({state:'visible'});
    await page.waitForFunction(() => document.querySelectorAll('#methodologySelect option').length === 2);
    await waitReady();
    await period();
    const final = await inspect();
    assert(final.display_value === '50.00', 'Expected OC-A02 50% final-target achievement.');
    const text = await page.locator('#methodologyResult').textContent();
    assert(text.includes('50.00 %') && text.includes('2026-09-30') && text.includes('1.0.0') && text.includes('(A-B)/(T-B)'), 'Explanation is incomplete.');
    assert(final.numerator.numerator === '40' && final.denominator.numerator === '80', 'Incorrect intermediates.');
    await shot('01-final-achievement.png');
    passed('CHROME_KEYBOARD_FINAL_ACHIEVEMENT', 'Persisted source actual=60, baseline=20, target=100 gives 50.00%; formula, period and version visible.');
    await page.locator('#methodologyResult summary').click();
    const details = await page.locator('#methodologyResult details').textContent();
    assert(details.includes('100.00% (2/2)') && details.includes('NOT_ASSESSED') && details.includes('FITNESS_NOT_CONFIGURED'), 'Quality profile is misleading.');
    passed('CHROME_QUALITY_DETAILS', 'Completeness 2/2; unconfigured dimensions and fitness remain explicitly unavailable.');
    await page.locator('#methodologySelect').selectOption('1');
    assert((await page.locator('#methodologyResult').textContent()) === '', 'Old result not cleared on method change.');
    const schedule = await inspect();
    assert(schedule.display_value === '100.00' && schedule.metric_kind === 'schedule_attainment', 'Schedule result not separated.');
    await shot('02-schedule-attainment.png');
    passed('CHROME_SEPARATE_SCHEDULE_ATTAINMENT', 'Approved planned target=60 yields 100.00% schedule attainment, separately labelled.');
    await page.locator('#methodologyStart').fill('2026-10-01');
    await page.locator('#methodologyExplainBtn').click();
    await page.waitForFunction(() => document.getElementById('methodologyFeedback').textContent.includes('unavailable'));
    assert((await page.locator('#methodologyResult').textContent()) === '', 'Error left stale result visible.');
    assert(await page.locator('#methodologyStart').inputValue() === '2026-10-01', 'Error lost input.');
    passed('CHROME_ERROR_AND_STALE_RESULT', 'Invalid period shows safe error, clears previous value and preserves input.');
    await period();
    await page.locator('#indicatorPicker').selectOption('indicator_unconfigured');
    await page.waitForFunction(() => document.getElementById('methodologyFeedback').textContent.includes('UNCONFIGURED'));
    const unavailable = await inspect();
    assert(unavailable.state === 'UNCONFIGURED' && unavailable.display_value === null, 'Unconfigured indicator invented a value.');
    await shot('03-unconfigured.png');
    passed('CHROME_UNCONFIGURED', 'Missing method/target shows UNCONFIGURED with no numeric result.');
    await page.locator('#indicatorPicker').selectOption('indicator_method');
    await page.waitForFunction(() => document.querySelectorAll('#methodologySelect option').length === 2);
    const labels = {EN:'How is this calculated?', PT:'Como é calculado?', FR:'Comment est-ce calculé ?'};
    for (const language of ['PT','FR','EN']) {
      await page.locator('#uiLanguagePicker').selectOption(language);
      await page.waitForFunction(expected => document.getElementById('methodologyExplainBtn').textContent === expected, labels[language]);
      await waitReady();
      await page.locator('#methodologySelect').selectOption('0');
      const result = await inspect();
      assert(result.display_value === '50.00' && result.context.locale === language, 'Locale changed formula meaning.');
      await shot(`04-locale-${language}.png`);
    }
    passed('CHROME_LOCALIZED_CONTROLS', 'EN/PT/FR explanation labels and the same 50.00% arithmetic; approved source prose retains its recorded language.');
    for (const [width,height] of [[360,800],[768,1024],[1366,768],[1920,1080]]) {
      await page.setViewportSize({width,height});
      await page.locator('#methodologyPanel').scrollIntoViewIfNeeded();
      const bounds = await page.locator('#methodologyPanel').boundingBox();
      assert(bounds && bounds.width <= width && bounds.x >= -1, 'Explanation panel clips horizontally.');
      const overflow = await page.locator('#methodologyPanel').evaluate(el => el.scrollWidth > el.clientWidth + 1);
      assert(!overflow, 'Explanation panel has horizontal overflow.');
      await shot(`05-viewport-${width}.png`);
    }
    passed('CHROME_FOUR_VIEWPORTS', 'Explanation panel and controls fit 360x800, 768x1024, 1366x768 and 1920x1080; no full accessibility claim.');
    await page.setViewportSize({width:1366,height:768});
    const second = await context.newPage();
    await second.goto(base + '/studio', {waitUntil:'networkidle'});
    await second.locator('#appShell').waitFor({state:'visible',timeout:20000});
    await second.locator('#logoutBtn').click();
    await page.waitForFunction(() => document.getElementById('methodologyResult').textContent === '');
    assert(await page.locator('#methodologySelect option').count() === 0, 'Method definitions remained after logout.');
    passed('CHROME_CROSS_TAB_LOGOUT_CLEARING', 'Logout in another tab clears the explanation and method definitions.');
    assert(pageErrors.length === 0, 'Unexpected JavaScript page errors: ' + pageErrors.join(';'));
    passed('CHROME_NO_SCRIPT_ERRORS', 'No pageerror events during the workflow.');
    report.status = 'PASS';
  } catch (error) {
    report.status = 'FAIL';
    report.failure = error.message;
    report.failure_stack = error.stack;
    report.diagnostic = await page.evaluate(() => ({
      flash: document.getElementById('flash')?.textContent,
      current_view: state.currentView, project_id: state.projectId, indicator_id: state.indicatorId,
      snapshot_present: Boolean(state.projectSnapshot), indicator_count: state.projectSnapshot?.indicators?.length,
      request_audit: state.requestAudit?.map(r => ({route:r.route,status:r.status,ok:r.ok})),
      feedback: document.getElementById('methodologyFeedback')?.textContent,
    })).catch(() => null);
    await page.screenshot({path:path.join(evidence,'failure.png'),fullPage:true}).catch(() => {});
    throw error;
  } finally {
    report.page_errors = pageErrors;
    fs.writeFileSync(path.join(evidence,'browser-results.json'), JSON.stringify(report,null,2));
    await browser.close();
  }
})().catch(error => { console.error(error.message); process.exitCode = 1; });
