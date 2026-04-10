// @bun
// cdp.ts
import { spawn } from "child_process";
import fs from "fs";
import { mkdir } from "fs/promises";
import net from "net";
import process2 from "process";

// paths.ts
import os from "os";
import path from "path";
import process from "process";
var APP_DATA_DIR = "baoyu-skills";
var URL_TO_MARKDOWN_DATA_DIR = "url-to-markdown";
var PROFILE_DIR_NAME = "chrome-profile";
function resolveUserDataRoot() {
  if (process.platform === "win32") {
    return process.env.APPDATA ?? path.join(os.homedir(), "AppData", "Roaming");
  }
  if (process.platform === "darwin") {
    return path.join(os.homedir(), "Library", "Application Support");
  }
  return process.env.XDG_DATA_HOME ?? path.join(os.homedir(), ".local", "share");
}
function resolveUrlToMarkdownChromeProfileDir() {
  const override = process.env.URL_CHROME_PROFILE_DIR?.trim();
  if (override)
    return path.resolve(override);
  return path.join(resolveUserDataRoot(), APP_DATA_DIR, URL_TO_MARKDOWN_DATA_DIR, PROFILE_DIR_NAME);
}

// constants.ts
var USER_DATA_DIR = resolveUrlToMarkdownChromeProfileDir();
var NETWORK_IDLE_TIMEOUT_MS = 1500;

// cdp.ts
function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
async function fetchWithTimeout(url, init = {}) {
  const { timeoutMs, ...rest } = init;
  if (!timeoutMs || timeoutMs <= 0)
    return fetch(url, rest);
  const ctl = new AbortController;
  const t = setTimeout(() => ctl.abort(), timeoutMs);
  try {
    return await fetch(url, { ...rest, signal: ctl.signal });
  } finally {
    clearTimeout(t);
  }
}

class CdpConnection {
  ws;
  nextId = 0;
  pending = new Map;
  eventHandlers = new Map;
  constructor(ws) {
    this.ws = ws;
    this.ws.addEventListener("message", (event) => {
      try {
        const data = typeof event.data === "string" ? event.data : new TextDecoder().decode(event.data);
        const msg = JSON.parse(data);
        if (msg.id) {
          const p = this.pending.get(msg.id);
          if (p) {
            this.pending.delete(msg.id);
            if (p.timer)
              clearTimeout(p.timer);
            if (msg.error?.message)
              p.reject(new Error(msg.error.message));
            else
              p.resolve(msg.result);
          }
        } else if (msg.method) {
          const handlers = this.eventHandlers.get(msg.method);
          if (handlers) {
            for (const h of handlers)
              h(msg.params);
          }
        }
      } catch {}
    });
    this.ws.addEventListener("close", () => {
      for (const [id, p] of this.pending.entries()) {
        this.pending.delete(id);
        if (p.timer)
          clearTimeout(p.timer);
        p.reject(new Error("CDP connection closed."));
      }
    });
  }
  static async connect(url, timeoutMs) {
    const ws = new WebSocket(url);
    await new Promise((resolve, reject) => {
      const t = setTimeout(() => reject(new Error("CDP connection timeout.")), timeoutMs);
      ws.addEventListener("open", () => {
        clearTimeout(t);
        resolve();
      });
      ws.addEventListener("error", () => {
        clearTimeout(t);
        reject(new Error("CDP connection failed."));
      });
    });
    return new CdpConnection(ws);
  }
  on(event, handler) {
    let handlers = this.eventHandlers.get(event);
    if (!handlers) {
      handlers = new Set;
      this.eventHandlers.set(event, handlers);
    }
    handlers.add(handler);
  }
  off(event, handler) {
    this.eventHandlers.get(event)?.delete(handler);
  }
  async send(method, params, opts) {
    const id = ++this.nextId;
    const msg = { id, method };
    if (params)
      msg.params = params;
    if (opts?.sessionId)
      msg.sessionId = opts.sessionId;
    const timeoutMs = opts?.timeoutMs ?? 15000;
    const out = await new Promise((resolve, reject) => {
      const t = timeoutMs > 0 ? setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`CDP timeout: ${method}`));
      }, timeoutMs) : null;
      this.pending.set(id, { resolve, reject, timer: t });
      this.ws.send(JSON.stringify(msg));
    });
    return out;
  }
  close() {
    try {
      this.ws.close();
    } catch {}
  }
}
async function getFreePort() {
  return await new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.unref();
    srv.on("error", reject);
    srv.listen(0, "127.0.0.1", () => {
      const addr = srv.address();
      if (!addr || typeof addr === "string") {
        srv.close(() => reject(new Error("Unable to allocate a free TCP port.")));
        return;
      }
      const port = addr.port;
      srv.close((err) => err ? reject(err) : resolve(port));
    });
  });
}
function findChromeExecutable() {
  const override = process2.env.URL_CHROME_PATH?.trim();
  if (override && fs.existsSync(override))
    return override;
  const candidates = [];
  switch (process2.platform) {
    case "darwin":
      candidates.push("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary", "/Applications/Google Chrome Beta.app/Contents/MacOS/Google Chrome Beta", "/Applications/Chromium.app/Contents/MacOS/Chromium", "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge");
      break;
    case "win32":
      candidates.push("C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe", "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe", "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe");
      break;
    default:
      candidates.push("/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium", "/usr/bin/chromium-browser", "/snap/bin/chromium", "/usr/bin/microsoft-edge");
      break;
  }
  for (const p of candidates) {
    if (fs.existsSync(p))
      return p;
  }
  return null;
}
async function waitForChromeDebugPort(port, timeoutMs) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetchWithTimeout(`http://127.0.0.1:${port}/json/version`, { timeoutMs: 5000 });
      if (!res.ok)
        throw new Error(`status=${res.status}`);
      const j = await res.json();
      if (j.webSocketDebuggerUrl)
        return j.webSocketDebuggerUrl;
    } catch {}
    await sleep(200);
  }
  throw new Error("Chrome debug port not ready");
}
async function launchChrome(url, port, headless = false) {
  const chrome = findChromeExecutable();
  if (!chrome)
    throw new Error("Chrome executable not found. Install Chrome or set URL_CHROME_PATH env.");
  const profileDir = resolveUrlToMarkdownChromeProfileDir();
  await mkdir(profileDir, { recursive: true });
  const args = [
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profileDir}`,
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-popup-blocking"
  ];
  if (headless)
    args.push("--headless=new");
  args.push(url);
  return spawn(chrome, args, { stdio: "ignore" });
}
async function waitForNetworkIdle(cdp, sessionId, timeoutMs = NETWORK_IDLE_TIMEOUT_MS) {
  return new Promise((resolve) => {
    let timer = null;
    let pending = 0;
    const cleanup = () => {
      if (timer)
        clearTimeout(timer);
      cdp.off("Network.requestWillBeSent", onRequest);
      cdp.off("Network.loadingFinished", onFinish);
      cdp.off("Network.loadingFailed", onFinish);
    };
    const done = () => {
      cleanup();
      resolve();
    };
    const resetTimer = () => {
      if (timer)
        clearTimeout(timer);
      timer = setTimeout(done, timeoutMs);
    };
    const onRequest = () => {
      pending++;
      resetTimer();
    };
    const onFinish = () => {
      pending = Math.max(0, pending - 1);
      if (pending <= 2)
        resetTimer();
    };
    cdp.on("Network.requestWillBeSent", onRequest);
    cdp.on("Network.loadingFinished", onFinish);
    cdp.on("Network.loadingFailed", onFinish);
    resetTimer();
  });
}
async function waitForPageLoad(cdp, sessionId, timeoutMs = 30000) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      cdp.off("Page.loadEventFired", handler);
      resolve();
    }, timeoutMs);
    const handler = () => {
      clearTimeout(timer);
      cdp.off("Page.loadEventFired", handler);
      resolve();
    };
    cdp.on("Page.loadEventFired", handler);
  });
}
async function createTargetAndAttach(cdp, url) {
  const { targetId } = await cdp.send("Target.createTarget", { url });
  const { sessionId } = await cdp.send("Target.attachToTarget", { targetId, flatten: true });
  await cdp.send("Network.enable", {}, { sessionId });
  await cdp.send("Page.enable", {}, { sessionId });
  return { targetId, sessionId };
}
async function navigateAndWait(cdp, sessionId, url, timeoutMs) {
  const loadPromise = new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("Page load timeout")), timeoutMs);
    const handler = (params) => {
      const p = params;
      if (p.name === "load" || p.name === "DOMContentLoaded") {
        clearTimeout(timer);
        cdp.off("Page.lifecycleEvent", handler);
        resolve();
      }
    };
    cdp.on("Page.lifecycleEvent", handler);
  });
  await cdp.send("Page.navigate", { url }, { sessionId });
  await loadPromise;
}
async function evaluateScript(cdp, sessionId, expression, timeoutMs = 30000) {
  const result = await cdp.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true }, { sessionId, timeoutMs });
  return result.result.value;
}
async function autoScroll(cdp, sessionId, steps = 8, waitMs = 600) {
  let lastHeight = await evaluateScript(cdp, sessionId, "document.body.scrollHeight");
  for (let i = 0;i < steps; i++) {
    await evaluateScript(cdp, sessionId, "window.scrollTo(0, document.body.scrollHeight)");
    await sleep(waitMs);
    const newHeight = await evaluateScript(cdp, sessionId, "document.body.scrollHeight");
    if (newHeight === lastHeight)
      break;
    lastHeight = newHeight;
  }
  await evaluateScript(cdp, sessionId, "window.scrollTo(0, 0)");
}
function killChrome(chrome) {
  try {
    chrome.kill("SIGTERM");
  } catch {}
  setTimeout(() => {
    if (!chrome.killed) {
      try {
        chrome.kill("SIGKILL");
      } catch {}
    }
  }, 2000).unref?.();
}
export {
  waitForPageLoad,
  waitForNetworkIdle,
  waitForChromeDebugPort,
  navigateAndWait,
  launchChrome,
  killChrome,
  getFreePort,
  findChromeExecutable,
  evaluateScript,
  createTargetAndAttach,
  autoScroll,
  CdpConnection
};
