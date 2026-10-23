const fs = require("fs");
const path = require("path");

const playwrightRoot = process.env.PLAYWRIGHT_CORE_PATH;
if (!playwrightRoot) throw new Error("PLAYWRIGHT_CORE_PATH is required.");
const { chromium } = require(playwrightRoot);

const baseUrl = process.env.RCATLAS_BASE_URL || "http://127.0.0.1:8871";
const chromePath = process.env.RCATLAS_CHROME_PATH;
const evidenceDir = process.env.RCATLAS_EVIDENCE_DIR;
if (!chromePath || !evidenceDir) throw new Error("RCATLAS_CHROME_PATH and RCATLAS_EVIDENCE_DIR are required.");

fs.mkdirSync(evidenceDir, { recursive: true });

const results = [];
function record(id, status, actual, evidence = []) {
  results.push({ id, status, actual, evidence });
}
function assert(condition, message) {
  if (!condition) throw new Error(message);
}
async function screenshot(page, name) {
  const target = path.join(evidenceDir, name);
  await page.screenshot({ path: target, fullPage: true });
  return target;
}
async function waitForText(locator, pattern, timeout = 10000) {
  await locator.waitFor({ state: "visible", timeout });
  const started = Date.now();
  while (Date.now() - started < timeout) {
    const text = (await locator.textContent()) || "";
    if (pattern.test(text)) return text;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw new Error(`Expected ${pattern} in locator text.`);
}
async function fillProject(page, suffix) {
  await page.locator("#projectNameInput").fill(`Synthetic Acceptance ${suffix}`);
  await page.locator("#projectCodeInput").fill(`W1-${suffix}`);
  await page.locator("#projectProgrammeInput").fill("Synthetic Programme");
  await page.locator("#projectDonorInput").fill("Synthetic Donor");
  await page.locator("#projectPartnerInput").fill("Synthetic Partner");
  await page.locator("#projectSectorInput").fill("Education");
  await page.locator("#projectDescriptionInput").fill("Disposable browser acceptance project.");
  await page.locator("#projectStepNextBtn").click();
  await page.locator("#projectStepCoverage").waitFor({ state: "visible" });
  await page.locator("#projectCountryInput").fill("Testland");
  await page.locator("#projectStartDateInput").fill("2026-01-01");
  await page.locator("#projectEndDateInput").fill("2026-12-31");
}

(async () => {
  const browser = await chromium.launch({
    executablePath: chromePath,
    headless: true,
    args: ["--no-first-run", "--disable-default-apps"],
  });
  const browserVersion = browser.version();
  const context = await browser.newContext({ viewport: { width: 1366, height: 768 } });
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", message => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  try {
    await page.goto(`${baseUrl}/studio`, { waitUntil: "networkidle" });
    await page.locator("#splashScreen").waitFor({ state: "hidden", timeout: 10000 });
    assert(await page.locator("#trustedSetupTools").getAttribute("data-trusted-setup") === "enabled", "Trusted setup UI was not enabled.");
    await page.locator("#developerToolsSummary").click();
    await page.locator("#bootstrapUsername").fill("browser.admin@example.test");
    await page.locator("#bootstrapPassword").fill("SyntheticBrowserPassword!123");
    await page.locator("#bootstrapFullName").fill("Browser Acceptance Admin");
    await page.locator("#bootstrapEmail").fill("browser.admin@example.test");
    await page.locator("#setupToken").fill("wrong-synthetic-token");
    await page.locator("#bootstrapBtn").click();
    const unauthorizedText = await waitForText(page.locator("#flash > div"), /authorization failed/i);
    const unauthorizedShot = await screenshot(page, "01-unauthorized-setup-rejected.png");
    record("BROWSER-SETUP-UNAUTHORIZED", "PASS", unauthorizedText, [unauthorizedShot]);

    await page.locator("#setupToken").fill("synthetic-browser-setup-token");
    await page.locator("#bootstrapBtn").click();
    const setupText = await waitForText(page.locator("#loginBanner"), /initial setup completed/i);
    const setupShot = await screenshot(page, "02-trusted-setup-complete.png");
    record("BROWSER-SETUP-AUTHORIZED", "PASS", setupText, [setupShot]);

    await page.locator("#bootstrapUsername").fill("browser.admin@example.test");
    await page.locator("#bootstrapPassword").fill("WrongSyntheticPassword!123");
    await page.locator("#loginBtn").click();
    const invalidText = await waitForText(page.locator("#flash > div"), /invalid email or password/i);
    const invalidShot = await screenshot(page, "03-invalid-login-feedback.png");
    record("BROWSER-LOGIN-INVALID", "PASS", invalidText, [invalidShot]);

    await page.locator("#bootstrapPassword").fill("SyntheticBrowserPassword!123");
    await page.locator("#loginBtn").click();
    await page.locator("#appShell").waitFor({ state: "visible", timeout: 20000 });
    const browserStorage = await page.evaluate(() => ({
      authToken: window.localStorage.getItem("rcatlas.authToken"),
      sessionUser: window.localStorage.getItem("rcatlas.sessionUser"),
      visibleCookies: document.cookie,
    }));
    assert(browserStorage.authToken === null, "A bearer token remained in localStorage.");
    assert(browserStorage.sessionUser === null, "Prior actor data remained in localStorage.");
    assert(!browserStorage.visibleCookies.includes("rcatlas_session"), "The session cookie was visible to JavaScript.");
    const sessionCookie = (await context.cookies()).find(cookie => cookie.name === "rcatlas_session_dev");
    assert(Boolean(sessionCookie), "The browser session cookie was not established.");
    assert(sessionCookie.httpOnly, "The browser session cookie was not HttpOnly.");
    assert(sessionCookie.sameSite === "Lax", `Unexpected SameSite value: ${sessionCookie.sameSite}.`);
    const copiedRevocationCookie = { ...sessionCookie };
    const loginShot = await screenshot(page, "04-authorized-login.png");
    record("BROWSER-LOGIN-AUTHORIZED", "PASS", "Authorized Studio shell became visible with an HttpOnly SameSite=Lax session and no persistent browser bearer token.", [loginShot]);

    await page.reload({ waitUntil: "networkidle" });
    await page.locator("#appShell").waitFor({ state: "visible", timeout: 20000 });
    record("BROWSER-SESSION-RESTORE", "PASS", "Reload restored the cookie-backed session without exposing credentials to JavaScript.");

    const secondTab = await context.newPage();
    await secondTab.goto(`${baseUrl}/studio`, { waitUntil: "networkidle" });
    await secondTab.locator("#appShell").waitFor({ state: "visible", timeout: 20000 });
    await page.locator("#logoutBtn").click();
    await page.locator("#loginShell").waitFor({ state: "visible", timeout: 10000 });
    await secondTab.locator("#loginShell").waitFor({ state: "visible", timeout: 10000 });
    const replayContext = await browser.newContext({ viewport: { width: 1366, height: 768 } });
    await replayContext.addCookies([copiedRevocationCookie]);
    const rejected = await replayContext.request.get(`${baseUrl}/v1/auth/me`);
    assert(rejected.status() === 401, `Logged-out token returned ${rejected.status()}, expected 401.`);
    await replayContext.close();
    const crossTabShot = await screenshot(secondTab, "05-cross-tab-logout.png");
    record("BROWSER-LOGOUT-REUSE", "PASS", "Both tabs returned to login; replay of the copied revoked cookie received 401.", [crossTabShot]);
    await secondTab.close();

    await page.locator("#bootstrapUsername").fill("browser.admin@example.test");
    await page.locator("#bootstrapPassword").fill("SyntheticBrowserPassword!123");
    await page.locator("#loginBtn").click();
    await page.locator("#appShell").waitFor({ state: "visible", timeout: 20000 });
    await page.locator('.nav-link[data-view="project-config"]').click();
    // Wait for the asynchronous registry load before editing this test's form.
    await page.waitForLoadState("networkidle");
    await page.locator('#projectRegistryNewBtn').click();
    let releaseRefresh;
    const refreshGate = new Promise(resolve => { releaseRefresh = resolve; });
    const refreshRoute = async route => {
      if (route.request().method() === "GET") await refreshGate;
      await route.continue();
    };
    await page.route("**/v1/admin/projects", refreshRoute);
    const refreshRequest = page.waitForRequest(request => request.method() === "GET" && new URL(request.url()).pathname === "/v1/admin/projects");
    await page.locator("#projectRegistryRefreshBtn").click();
    await refreshRequest;
    await fillProject(page, "DUPLICATE");
    releaseRefresh();
    await waitForText(page.locator("#flash > div"), /project registry refreshed/i);
    await page.unroute("**/v1/admin/projects", refreshRoute);
    assert(await page.locator("#projectNameInput").inputValue() === "Synthetic Acceptance DUPLICATE", "Registry refresh erased an in-flight draft edit.");
    record("BROWSER-DRAFT-REFRESH", "PASS", "A deliberately delayed registry response preserved edits entered while the request was in flight.");

    let createRequests = 0;
    page.on("request", request => {
      if (request.method() === "POST" && new URL(request.url()).pathname === "/v1/admin/projects") createRequests += 1;
    });
    const delayedRoute = async route => {
      if (route.request().method() === "POST") await new Promise(resolve => setTimeout(resolve, 500));
      await route.continue();
    };
    await page.route("**/v1/admin/projects", delayedRoute);
    const createResponse = page.waitForResponse(
      response => response.request().method() === "POST" && new URL(response.url()).pathname === "/v1/admin/projects"
    ).then(response => ({ response }), error => ({ error }));
    const pending = await page.locator("#saveProjectBtn").evaluate(button => {
      button.click();
      button.click();
      return { disabled: button.disabled, busy: button.getAttribute("aria-busy") };
    });
    if (!(pending.disabled && pending.busy === "true")) {
      const validation = await page.locator("#projectStudioState").textContent();
      await screenshot(page, "failure-project-pending.png");
      throw new Error(`Save control did not enter its pending state: ${validation}`);
    }
    const pendingText = await waitForText(page.locator("#flash > div"), /saving project/i);
    const responseResult = await createResponse;
    if (responseResult.error) throw responseResult.error;
    const response = responseResult.response;
    assert(response.status() === 200, `Project create returned ${response.status()}.`);
    await page.locator("#saveProjectBtn").waitFor({ state: "visible" });
    await page.waitForFunction(() => !document.getElementById("saveProjectBtn").disabled);
    await page.unroute("**/v1/admin/projects", delayedRoute);
    assert(createRequests === 1, `Double activation produced ${createRequests} create requests.`);
    const projectsResponse = await context.request.get(`${baseUrl}/v1/admin/projects`);
    assert(projectsResponse.status() === 200, "Unable to verify project registry after create.");
    const projectsBody = await projectsResponse.json();
    const duplicateCount = projectsBody.items.filter(item => item.project_name === "Synthetic Acceptance DUPLICATE").length;
    assert(duplicateCount === 1, `Expected one project, found ${duplicateCount}.`);
    const duplicateShot = await screenshot(page, "06-duplicate-submit-prevented.png");
    record("BROWSER-PROJECT-DUPLICATE", "PASS", `${pendingText}; one POST and one project persisted.`, [duplicateShot]);

    await page.locator("#projectRegistryNewBtn").click();
    await fillProject(page, "ERROR");
    const errorRoute = async route => route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Synthetic acceptance save failure." }),
    });
    await page.route("**/v1/admin/projects", errorRoute);
    await page.locator("#saveProjectBtn").click();
    const saveError = await waitForText(page.locator("#flash > div"), /synthetic acceptance save failure/i);
    await page.waitForFunction(() => !document.getElementById("saveProjectBtn").disabled);
    assert(await page.locator("#projectNameInput").inputValue() === "Synthetic Acceptance ERROR", "Failed save did not preserve the draft.");
    const errorShot = await screenshot(page, "07-project-save-error-feedback.png");
    record("BROWSER-PROJECT-ERROR", "PASS", `${saveError}; draft preserved and Save re-enabled.`, [errorShot]);
    await page.unroute("**/v1/admin/projects", errorRoute);

    const expectedConsoleError = /status of (401|403|500) \((Unauthorized|Forbidden|Internal Server Error)\)/;
    const unexpectedConsoleErrors = consoleErrors.filter(message => !expectedConsoleError.test(message));
    if (unexpectedConsoleErrors.length) {
      record("BROWSER-CONSOLE", "FAIL", unexpectedConsoleErrors.join(" | "));
    } else {
      record(
        "BROWSER-CONSOLE",
        "PASS",
        consoleErrors.length
          ? "Only expected negative-path 401, 403, and synthetic 500 resource errors were captured."
          : "No browser console errors captured."
      );
    }
  } catch (error) {
    await screenshot(page, "failure-browser-state.png").catch(() => {});
    record("BROWSER-RUNNER", "FAIL", error.stack || String(error));
  } finally {
    await browser.close();
  }

  const output = {
    backend: "postgresql",
    browser: "Google Chrome",
    browser_version: browserVersion,
    base_url: baseUrl,
    results,
  };
  fs.writeFileSync(path.join(evidenceDir, "browser-results.json"), JSON.stringify(output, null, 2));
  console.log(JSON.stringify(output));
  if (results.some(item => item.status === "FAIL")) process.exitCode = 1;
})();
