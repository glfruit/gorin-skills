// @bun
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
var DEFAULT_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36";
var USER_DATA_DIR = resolveUrlToMarkdownChromeProfileDir();
var DEFAULT_TIMEOUT_MS = 30000;
var CDP_CONNECT_TIMEOUT_MS = 15000;
var NETWORK_IDLE_TIMEOUT_MS = 1500;
var POST_LOAD_DELAY_MS = 800;
var SCROLL_STEP_WAIT_MS = 600;
var SCROLL_MAX_STEPS = 8;
export {
  USER_DATA_DIR,
  SCROLL_STEP_WAIT_MS,
  SCROLL_MAX_STEPS,
  POST_LOAD_DELAY_MS,
  NETWORK_IDLE_TIMEOUT_MS,
  DEFAULT_USER_AGENT,
  DEFAULT_TIMEOUT_MS,
  CDP_CONNECT_TIMEOUT_MS
};
