const fs = require("fs");
const path = require("path");

const { chromium } = require(process.env.PLAYWRIGHT_CORE_PATH);
const baseUrl = process.env.RCATLAS_BASE_URL || "http://127.0.0.1:8872";
const evidenceDir = process.env.RCATLAS_EVIDENCE_DIR;
const chromePath = process.env.RCATLAS_CHROME_PATH;
if (!evidenceDir || !chromePath) throw new Error("Browser acceptance environment is incomplete.");
fs.mkdirSync(evidenceDir, { recursive: true });

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function login(page, username) {
  await page.locator("#bootstrapUsername").fill(username);
  await page.locator("#bootstrapPassword").fill("SyntheticRestartPassword!123");
  await page.locator("#loginBtn").click();
  await page.locator("#appShell").waitFor({ state: "visible", timeout: 20000 });
  await page.locator('.nav-link[data-view="project-config"]').click();
  await page.locator("#projectRegistryTable").waitFor({ state: "visible", timeout: 10000 });
}

async function waitForRegistryProject(page, projectName) {
  await page.waitForFunction(
    expected => (document.getElementById("projectRegistryTable")?.textContent || "").includes(expected),
    projectName,
    { timeout: 15000 }
  );
}

(async () => {
  const output = {
    browser: "Google Chrome",
    browser_version: "154.0.8037.98",
    base_url: baseUrl,
    results: [],
  };
  const browser = await chromium.launch({
    executablePath: chromePath,
    headless: true,
    args: ["--no-first-run", "--disable-default-apps"],
  });
  const page = await (await browser.newContext({ viewport: { width: 1366, height: 768 } })).newPage();
  try {
    await page.goto(`${baseUrl}/studio`, { waitUntil: "networkidle" });
    await page.locator("#splashScreen").waitFor({ state: "hidden", timeout: 10000 });

    await login(page, "restart.admin.a@example.test");
    await waitForRegistryProject(page, "Restart Persistence Project");
    const tenantAText = (await page.locator("#projectRegistryTable").textContent()) || "";
    assert(tenantAText.includes("Restart Persistence Project"), "Tenant A project was not visible.");
    assert(!tenantAText.includes("Foreign Restart Project"), "Tenant A could see Tenant B project.");
    const tenantAShot = path.join(evidenceDir, "08-tenant-a-project-isolation.png");
    await page.screenshot({ path: tenantAShot, fullPage: true });
    output.results.push({
      id: "BROWSER-TENANT-A-ISOLATION",
      status: "PASS",
      actual: "Tenant A registry showed only its own synthetic project.",
      evidence: [tenantAShot],
    });

    await page.locator("#logoutBtn").click();
    await page.locator("#loginShell").waitFor({ state: "visible", timeout: 10000 });
    await login(page, "restart.admin.b@example.test");
    await waitForRegistryProject(page, "Foreign Restart Project");
    const tenantBText = (await page.locator("#projectRegistryTable").textContent()) || "";
    assert(tenantBText.includes("Foreign Restart Project"), "Tenant B project was not visible.");
    assert(!tenantBText.includes("Restart Persistence Project"), "Tenant B could see Tenant A project.");
    const tenantBShot = path.join(evidenceDir, "09-tenant-b-project-isolation.png");
    await page.screenshot({ path: tenantBShot, fullPage: true });
    output.results.push({
      id: "BROWSER-TENANT-B-ISOLATION",
      status: "PASS",
      actual: "Tenant B registry showed only its own synthetic project.",
      evidence: [tenantBShot],
    });
  } catch (error) {
    output.results.push({ id: "BROWSER-TENANT-ISOLATION-RUNNER", status: "FAIL", actual: error.stack || String(error), evidence: [] });
  } finally {
    await browser.close();
  }
  fs.writeFileSync(
    path.join(evidenceDir, "browser-tenant-isolation-results.json"),
    JSON.stringify(output, null, 2)
  );
  console.log(JSON.stringify(output));
  if (output.results.some(result => result.status === "FAIL")) process.exitCode = 1;
})();
