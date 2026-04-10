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
function resolveUrlToMarkdownDataDir() {
  const override = process.env.URL_DATA_DIR?.trim();
  if (override)
    return path.resolve(override);
  return path.join(process.cwd(), URL_TO_MARKDOWN_DATA_DIR);
}
function resolveUrlToMarkdownChromeProfileDir() {
  const override = process.env.URL_CHROME_PROFILE_DIR?.trim();
  if (override)
    return path.resolve(override);
  return path.join(resolveUserDataRoot(), APP_DATA_DIR, URL_TO_MARKDOWN_DATA_DIR, PROFILE_DIR_NAME);
}
export {
  resolveUserDataRoot,
  resolveUrlToMarkdownDataDir,
  resolveUrlToMarkdownChromeProfileDir
};
