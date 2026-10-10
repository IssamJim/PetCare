const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

(async () => {
  const base = process.argv[2];
  assert(base && new URL(base).hostname === "localhost", "Use Django's isolated local test server.");
  const browser = await chromium.launch({
    headless: true,
    ...(process.env.PETCARE_BROWSER_CHANNEL ? { channel: process.env.PETCARE_BROWSER_CHANNEL } : {}),
  });
  try {
    const context = await browser.newContext({ viewport: { width: 1366, height: 1100 } });
    // Registration only uses bundled assets; avoid external requests from the old login page.
    await context.route("**/*", route => new URL(route.request().url()).origin === base ? route.continue() : route.abort());
    const page = await context.newPage();
    const registrationErrors = [];
    page.on("pageerror", error => {
      if (new URL(page.url()).pathname.startsWith("/registro/")) registrationErrors.push(error.message);
    });
    let posts = 0;
    page.on("request", request => {
      if (request.method() === "POST" && request.url() === `${base}/registro/`) posts++;
    });
    const artifacts = path.join(process.cwd(), "artifacts");
    fs.mkdirSync(artifacts, { recursive: true });
    const submit = page.getByRole("button", { name: "Registrarse", exact: true });
    const dismiss = async () => {
      await page.getByRole("button", { name: "Corregir datos", exact: true }).click();
      await page.locator(".swal2-container").waitFor({ state: "detached" });
    };
    const fill = async (username, email, password = "Sierra!Camino-6814", confirmation = password) => {
      await page.getByLabel("Nombre", { exact: false }).first().fill("Elena");
      await page.locator('[name="last_name"]').fill("Del Río");
      await page.locator('[name="username"]').fill(username);
      await page.locator('[name="email"]').fill(email);
      await page.locator('[name="password1"]').fill(password);
      await page.locator('[name="password2"]').fill(confirmation);
    };

    await page.goto(`${base}/loguearse`);
    await page.getByRole("link", { name: "Regístrate", exact: true }).click();
    await page.waitForURL(`${base}/registro/`);
    await page.locator("#registration-form").waitFor();
    await page.screenshot({ path: path.join(artifacts, "registration-desktop.png"), fullPage: true });
    assert.equal(await page.locator('input[required]').count(), 6);
    assert.equal(await page.locator('input[type="password"]').count(), 2);
    assert.equal(await page.locator("select").count(), 0);
    await page.setViewportSize({ width: 390, height: 844 });
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await page.screenshot({ path: path.join(artifacts, "registration-mobile.png"), fullPage: true });

    await submit.click();
    await page.getByRole("dialog").waitFor();
    assert.equal(posts, 0);
    assert.equal(await page.getByRole("dialog").count(), 1);
    assert.equal(await page.locator('input[aria-invalid="true"]').count(), 6);
    assert.match(await page.getByRole("dialog").innerText(), /Completa el campo/);
    await dismiss();
    assert.equal(await page.evaluate(() => document.activeElement.name), "first_name");

    await fill("browser_client", "invalid", "First!password84", "Other!password93");
    await submit.click();
    await page.getByRole("dialog").waitFor();
    const invalidText = await page.getByRole("dialog").innerText();
    assert.match(invalidText, /correo electrónico válido/);
    assert.match(invalidText, /contraseñas no coinciden/);
    assert.equal(posts, 0);
    await dismiss();

    await fill("browser_client", "browser@example.com", "123");
    await submit.click();
    await page.waitForLoadState("load");
    await page.getByRole("dialog").waitFor();
    assert.equal(posts, 1);
    assert.match(await page.getByRole("dialog").innerText(), /contraseña/i);
    assert.equal(await page.locator('[name="first_name"]').inputValue(), "Elena");
    assert.equal(await page.locator('[name="password1"]').inputValue(), "");
    assert.equal(await page.locator('[name="password2"]').inputValue(), "");
    await page.screenshot({ path: path.join(artifacts, "registration-errors-mobile.png"), fullPage: true });
    await dismiss();

    await fill("browser_client", "browser@example.com");
    // Hold the actual request so the pending state and double-submit guard can be inspected.
    let release;
    const gate = new Promise(resolve => { release = resolve; });
    await page.route(`${base}/registro/`, async route => {
      if (route.request().method() === "POST") await gate;
      await route.continue();
    });
    const pendingRequest = page.waitForRequest(request => request.method() === "POST" && request.url() === `${base}/registro/`);
    // Inspect synchronously before navigation begins; locators intentionally
    // wait for navigation and cannot be used while this request is held.
    const pendingState = await page.evaluate(() => {
      const form = document.getElementById("registration-form");
      form.requestSubmit();
      const duplicate = new SubmitEvent("submit", { bubbles: true, cancelable: true });
      form.dispatchEvent(duplicate);
      return {
        disabled: document.getElementById("registration-submit").disabled,
        status: document.getElementById("registration-status").textContent,
        prevented: duplicate.defaultPrevented,
      };
    });
    await pendingRequest;
    assert.equal(pendingState.disabled, true);
    assert.match(pendingState.status, /procesando/);
    assert.equal(pendingState.prevented, true);
    assert.equal(posts, 2);
    release();
    await page.waitForURL(`${base}/registro/exitoso/`);
    await page.getByRole("dialog").waitFor();
    assert.match(await page.getByRole("dialog").innerText(), /¡Registro exitoso!/);
    assert.match(await page.getByRole("dialog").innerText(), /Tu cuenta ha sido creada correctamente/);
    await page.screenshot({ path: path.join(artifacts, "registration-success-mobile.png"), fullPage: true });
    await page.getByRole("dialog").getByRole("button", { name: "Iniciar sesión" }).click();
    await page.waitForURL(`${base}/loguearse`);
    await page.locator('[name="username"]').fill("browser_client");
    await page.locator('[name="password"]').fill("Sierra!Camino-6814");
    await page.getByRole("button", { name: "Iniciar sesión", exact: true }).click();
    await page.waitForURL(`${base}/home/`);

    await page.goto(`${base}/registro/`);
    await fill("another_client", "BROWSER@EXAMPLE.COM");
    await submit.click();
    await page.getByRole("dialog").waitFor();
    assert.match(await page.getByRole("dialog").innerText(), /Este correo electrónico ya está registrado/);
    assert.equal(await page.getByRole("dialog").count(), 1);
    await dismiss();

    const noJs = await browser.newContext({ javaScriptEnabled: false });
    const fallback = await noJs.newPage();
    await fallback.goto(`${base}/registro/`);
    await fallback.locator('[name="first_name"]').fill("Ana");
    await fallback.locator('[name="last_name"]').fill("López");
    await fallback.locator('[name="username"]').fill("no_js_invalid");
    await fallback.locator('[name="email"]').fill("fallback@example.com");
    await fallback.locator('[name="password1"]').fill("123");
    await fallback.locator('[name="password2"]').fill("123");
    await fallback.getByRole("button", { name: "Registrarse" }).click();
    await fallback.locator("#registration-summary").waitFor();
    assert.match(await fallback.locator("#registration-summary").innerText(), /No se pudo completar el registro/);
    assert.equal(await fallback.locator('[name="password1"]').inputValue(), "");
    assert.deepEqual(registrationErrors, []);
    console.log("Browser checks passed: mobile/desktop, inline errors and popups, pending state, duplicate prevention, registration, existing login, and no-JS fallback.");
  } finally {
    await browser.close();
  }
})().catch(error => {
  console.error(error.message);
  process.exitCode = 1;
});
