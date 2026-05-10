import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

function loadEnvFile(filePath) {
  if (!fs.existsSync(filePath)) return;
  const lines = fs.readFileSync(filePath, "utf8").split(/\r?\n/);
  for (const line of lines) {
    if (!line || line.trim().startsWith("#")) continue;
    const eq = line.indexOf("=");
    if (eq <= 0) continue;
    const key = line.slice(0, eq).trim();
    const value = line.slice(eq + 1).trim();
    if (!process.env[key]) process.env[key] = value;
  }
}

function required(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required env var: ${name}`);
  }
  return value;
}

function extractToken(payload) {
  if (!payload || typeof payload !== "object") return "";
  return (
    payload.access_token ||
    payload.token ||
    payload?.data?.attributes?.token ||
    payload?.data?.token ||
    ""
  );
}

async function authenticateWithPassword({ apiBase, appUrl, email, password, account }) {
  const response = await fetch(`${apiBase}/authenticate`, {
    method: "POST",
    headers: {
      accept: "application/vnd.api+json",
      "content-type": "application/vnd.api+json",
      origin: appUrl,
      referer: `${appUrl}/`
    },
    body: JSON.stringify({
      username: email,
      password,
      account
    })
  });

  const raw = await response.text();
  if (!response.ok) {
    throw new Error(`Falha ao autenticar em /authenticate: HTTP ${response.status} - ${raw.slice(0, 400)}`);
  }

  let payload = null;
  try {
    payload = JSON.parse(raw);
  } catch {
    throw new Error("Resposta de /authenticate nao veio em JSON.");
  }

  const token = extractToken(payload);
  if (!token) {
    throw new Error("Nao foi possivel extrair token da resposta de /authenticate.");
  }
  return token;
}

async function seedBrowserAuth(context, token, account, email) {
  const sessionPayload = {
    authenticated: {
      access_token: token,
      token,
      account,
      username: email
    }
  };

  await context.addInitScript(
    ({ rawToken, rawAccount, payload }) => {
      const value = JSON.stringify(payload);
      const keys = [
        "ember_simple_auth-session",
        "ember_simple_auth:session",
        "session",
        "auth.token",
        "token",
        "access_token"
      ];
      for (const k of keys) {
        try {
          window.localStorage.setItem(k, value);
          window.sessionStorage.setItem(k, value);
        } catch {
          // ignore storage errors
        }
      }
      try {
        window.localStorage.setItem("access_token", rawToken);
        window.localStorage.setItem("token", rawToken);
        window.localStorage.setItem("account", rawAccount || "");
        window.sessionStorage.setItem("access_token", rawToken);
        window.sessionStorage.setItem("token", rawToken);
        window.sessionStorage.setItem("account", rawAccount || "");
      } catch {
        // ignore storage errors
      }
    },
    { rawToken: token, rawAccount: account, payload: sessionPayload }
  );
}

async function fillFirst(page, selectors, value) {
  for (const selector of selectors) {
    const locator = page.locator(selector).first();
    if ((await locator.count()) > 0) {
      await locator.fill(value);
      return selector;
    }
  }
  return null;
}

async function clickFirst(page, selectors) {
  for (const selector of selectors) {
    const locator = page.locator(selector).first();
    if ((await locator.count()) > 0) {
      await locator.click();
      return selector;
    }
  }
  return null;
}

async function fillFirstInFrames(page, selectors, value) {
  for (const frame of page.frames()) {
    for (const selector of selectors) {
      const locator = frame.locator(selector).first();
      if ((await locator.count()) > 0) {
        await locator.fill(value);
        return { frameUrl: frame.url(), selector };
      }
    }
  }
  return null;
}

async function clickFirstInFrames(page, selectors) {
  for (const frame of page.frames()) {
    for (const selector of selectors) {
      const locator = frame.locator(selector).first();
      if ((await locator.count()) > 0) {
        if (!(await locator.isEnabled().catch(() => false))) {
          continue;
        }
        await locator.click();
        return { frameUrl: frame.url(), selector };
      }
    }
  }
  return null;
}

async function fieldExistsInFrames(page, selectors) {
  for (const frame of page.frames()) {
    for (const selector of selectors) {
      const locator = frame.locator(selector).first();
      if ((await locator.count()) > 0) return true;
    }
  }
  return false;
}

function safeFileName(name) {
  return name.replace(/[^a-zA-Z0-9._-]/g, "_");
}

function buildSummaryFromMeta(outputDir, summaryPath) {
  const files = fs.readdirSync(outputDir).filter((f) => f.endsWith(".meta.json")).sort();
  const lines = [];

  for (const file of files) {
    try {
      const meta = JSON.parse(fs.readFileSync(path.join(outputDir, file), "utf8"));
      lines.push(
        JSON.stringify({
          ts: new Date().toISOString(),
          status: meta.status,
          method: meta.method,
          url: meta.url,
          contentType: meta?.responseHeaders?.["content-type"] || "",
          requestHeaders: meta.requestHeaders || {}
        })
      );
    } catch {
      // ignore malformed files
    }
  }

  fs.writeFileSync(summaryPath, lines.join("\n") + (lines.length ? "\n" : ""), "utf8");
}

function redactHeaders(headers) {
  const out = {};
  for (const [k, v] of Object.entries(headers || {})) {
    const key = k.toLowerCase();
    if (key === "authorization" || key === "cookie" || key === "x-access-token") {
      out[k] = "<redacted>";
    } else {
      out[k] = v;
    }
  }
  return out;
}

async function saveDebugArtifacts(page, debugDir) {
  fs.mkdirSync(debugDir, { recursive: true });
  await page.screenshot({ path: path.join(debugDir, "login-failure.png"), fullPage: true });
  fs.writeFileSync(path.join(debugDir, "login-failure.html"), await page.content(), "utf8");

  const framesInfo = [];
  for (const frame of page.frames()) {
    const inputs = await frame.evaluate(() =>
      Array.from(document.querySelectorAll("input")).map((i) => ({
        name: i.getAttribute("name"),
        id: i.getAttribute("id"),
        type: i.getAttribute("type"),
        placeholder: i.getAttribute("placeholder"),
        autocomplete: i.getAttribute("autocomplete")
      }))
    ).catch(() => []);

    framesInfo.push({
      url: frame.url(),
      title: await frame.title().catch(() => null),
      inputCount: inputs.length,
      inputs
    });
  }

  fs.writeFileSync(path.join(debugDir, "frames-inputs.json"), JSON.stringify(framesInfo, null, 2), "utf8");
}

async function clickByTexts(page, texts) {
  for (const rawText of texts) {
    const text = rawText.trim();
    if (!text) continue;
    const candidates = [
      page.getByRole("button", { name: new RegExp(text, "i") }).first(),
      page.getByRole("link", { name: new RegExp(text, "i") }).first(),
      page.getByText(new RegExp(text, "i")).first()
    ];

    let clicked = false;
    for (const locator of candidates) {
      if ((await locator.count()) > 0 && (await locator.isVisible().catch(() => false))) {
        await locator.click().catch(() => {});
        clicked = true;
        break;
      }
    }

    if (clicked) {
      console.log(`  clique aplicado: "${text}"`);
      await page.waitForTimeout(4000);
    } else {
      console.log(`  nao encontrou clique para: "${text}"`);
    }
  }
}

async function main() {
  loadEnvFile(path.resolve(".env"));

  const email = process.env.CELULA_EMAIL || "";
  const password = process.env.CELULA_PASSWORD || "";
  const appUrl = process.env.CELULA_APP_URL || "https://app.celula.in";
  const apiHost = process.env.CELULA_API_HOST || "api.celula.in";
  const apiBase = (process.env.CELULA_API_BASE || `https://${apiHost}`).replace(/\/+$/, "");
  const targetPath = process.env.CELULA_TARGET_PATH || "/";
  const targetPaths = (process.env.CELULA_TARGET_PATHS || "")
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean);
  const clickTexts = (process.env.CELULA_CLICK_TEXTS || "")
    .split(",")
    .map((v) => v.trim())
    .filter(Boolean);
  const account = process.env.CELULA_ACCOUNT || "";
  let token = process.env.CELULA_TOKEN || "";
  const headless = (process.env.PLAYWRIGHT_HEADLESS || "true").toLowerCase() !== "false";

  if (!token && email && password && account) {
    console.log("0/4 gerando token via /authenticate...");
    token = await authenticateWithPassword({
      apiBase,
      appUrl,
      email,
      password,
      account
    });
  }

  const outputDir = path.resolve("artifacts", "network");
  fs.mkdirSync(outputDir, { recursive: true });

  const summaryPath = path.resolve("artifacts", "network-summary.ndjson");
  fs.mkdirSync(path.dirname(summaryPath), { recursive: true });
  if (!fs.existsSync(summaryPath)) {
    fs.writeFileSync(summaryPath, "", "utf8");
  }
  const debugDir = path.resolve("artifacts", "debug");
  fs.mkdirSync(debugDir, { recursive: true });

  const browser = await chromium.launch({ headless });
  const contextHeaders = {};
  if (token) {
    contextHeaders.accept = "application/vnd.api+json";
    contextHeaders.authorization = `Bearer ${token}`;
  }
  const context = await browser.newContext({
    extraHTTPHeaders: contextHeaders
  });
  if (token) {
    await seedBrowserAuth(context, token, account, email);
  }
  const page = await context.newPage();

  let responseIndex = 0;
  page.on("response", async (response) => {
    const url = response.url();
    if (!url.includes(apiHost)) return;

    const req = response.request();
    const status = response.status();
    const headers = response.headers();
    const contentType = headers["content-type"] || "";
    const method = req.method();
    const requestHeaders = redactHeaders(await req.allHeaders().catch(() => ({})));
    const requestPostData = req.postData();

    const item = {
      ts: new Date().toISOString(),
      index: responseIndex,
      status,
      method,
      url,
      contentType,
      requestHeaders
    };

    fs.appendFileSync(summaryPath, `${JSON.stringify(item)}\n`, "utf8");

    const metaFileName = safeFileName(`${String(responseIndex).padStart(4, "0")}_${status}_${method}_${new URL(url).pathname}.meta.json`);
    fs.writeFileSync(
      path.join(outputDir, metaFileName),
      JSON.stringify(
        {
          status,
          method,
          url,
          requestHeaders,
          requestPostData,
          responseHeaders: headers
        },
        null,
        2
      ),
      "utf8"
    );

    if (contentType.includes("json")) {
      try {
        const body = await response.text();
        const fileName = safeFileName(`${String(responseIndex).padStart(4, "0")}_${status}_${method}_${new URL(url).pathname}.json`);
        fs.writeFileSync(path.join(outputDir, fileName), body, "utf8");
      } catch {
        // ignore unreadable response body
      }
    }

    responseIndex += 1;
  });

  console.log("1/4 abrindo tela de login...");
  await page.goto(appUrl, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1500);

  if (token) {
    console.log("2/4 token informado; pulando login UI.");
    console.log("3/4 abrindo rota(s) alvo...");
    const pathsToVisit = targetPaths.length > 0 ? targetPaths : [targetPath];
    for (const p of pathsToVisit) {
      const targetUrl = new URL(p, appUrl).toString();
      console.log(`- visitando ${targetUrl}`);
      await page.goto(targetUrl, { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(7000);
      if (page.url().includes("/login")) {
        console.log("  redirecionou para login; tentando recarregar com sessao semeada...");
        await page.goto(targetUrl, { waitUntil: "domcontentloaded" });
        await page.waitForTimeout(5000);
      }
      console.log(`  url atual: ${page.url()}`);
      if (clickTexts.length > 0) {
        await clickByTexts(page, clickTexts);
        console.log(`  url apos cliques: ${page.url()}`);
      }
    }

    buildSummaryFromMeta(outputDir, summaryPath);
    console.log("4/4 finalizado.");
    console.log(`Resumo salvo em: ${summaryPath}`);
    console.log(`Payloads JSON salvos em: ${outputDir}`);

    await context.close();
    await browser.close();
    return;
  }

  if (!email || !password) {
    throw new Error("Defina CELULA_EMAIL e CELULA_PASSWORD no .env para login UI ou informe CELULA_TOKEN.");
  }

  console.log("2/4 tentando login automatico...");
  const accountSelectors = [
    "input[name='account']",
    "input[name='subdomain']",
    "input[id*='account']",
    "input[id*='subdomain']",
    "input[placeholder*='conta' i]",
    "input[placeholder*='subdomain' i]"
  ];
  const emailSelectors = [
    "input[name='username']",
    "input[name='email']",
    "input[id*='email']",
    "input[id*='username']",
    "input[placeholder*='email' i]",
    "input[placeholder*='e-mail' i]",
    "input[type='email']",
    "input[autocomplete='username']"
  ];
  const passwordSelectors = [
    "input[name='password']",
    "input[id*='password']",
    "input[type='password']",
    "input[autocomplete='current-password']"
  ];
  const continueSelectors = [
    "button[type='submit']",
    "button:has-text('Continuar')",
    "button:has-text('Proximo')",
    "button:has-text('Next')",
    "button:has-text('Entrar')",
    "button:has-text('Acessar')",
    "input[type='submit']"
  ];

  // Preenche conta apenas se campo explicito existir; nao usa fallback generico
  if (account && (await fieldExistsInFrames(page, accountSelectors))) {
    const accountFill = await fillFirstInFrames(page, accountSelectors, account);
    if (accountFill) {
      console.log(`Conta preenchida com seletor: ${accountFill.selector}`);
      await clickFirstInFrames(page, continueSelectors);
      await page.waitForTimeout(1000);
    }
  }

  // Etapa 1: email/username
  const emailFill = await fillFirstInFrames(page, emailSelectors, email);
  if (!emailFill) {
    await saveDebugArtifacts(page, debugDir);
    throw new Error(
      "Nao foi possivel localizar campo de email/username. Veja artifacts/debug/login-failure.png e artifacts/debug/frames-inputs.json."
    );
  }

  await clickFirstInFrames(page, continueSelectors);
  await page.waitForTimeout(1200);

  // Em alguns fluxos, password aparece apos um pequeno delay
  for (let i = 0; i < 8; i += 1) {
    if (await fieldExistsInFrames(page, passwordSelectors)) break;
    await page.waitForTimeout(500);
  }

  const passwordFill = await fillFirstInFrames(page, passwordSelectors, password);

  if (!passwordFill) {
    await saveDebugArtifacts(page, debugDir);
    throw new Error(
      "Nao foi possivel localizar campos de login. Veja artifacts/debug/login-failure.png e artifacts/debug/frames-inputs.json."
    );
  }

  const submitClick = await clickFirstInFrames(page, continueSelectors);
  if (!submitClick) {
    await saveDebugArtifacts(page, debugDir);
    throw new Error("Nao foi possivel localizar botao de envio habilitado. Veja artifacts/debug/login-failure.png.");
  }

  await page.waitForTimeout(6000);

  console.log("3/4 abrindo rota alvo...");
  const targetUrl = new URL(targetPath, appUrl).toString();
  await page.goto(targetUrl, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(12000);

  buildSummaryFromMeta(outputDir, summaryPath);
  console.log("4/4 finalizado.");
  console.log(`Resumo salvo em: ${summaryPath}`);
  console.log(`Payloads JSON salvos em: ${outputDir}`);

  await context.close();
  await browser.close();
}

main().catch((err) => {
  console.error(err.message || err);
  process.exitCode = 1;
});
