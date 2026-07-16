#!/usr/bin/env node
// generate-screenshot.ts - Capture screenshot of HTML page using Puppeteer/Playwright

import { execSync } from 'child_process';
import { existsSync } from 'fs';
import { resolve } from 'path';

/**
 * Generate screenshot from HTML file
 */
export async function generateScreenshot(htmlPath: string, outputPath: string): Promise<void> {
  if (!existsSync(htmlPath)) {
    throw new Error(`HTML file not found: ${htmlPath}`);
  }

  await generateScreenshotWithPlaywright(htmlPath, outputPath);
  console.log(`Screenshot generated: ${outputPath}`);
}

/**
 * Generate screenshot with Puppeteer
 */
export async function generateScreenshotWithPuppeteer(htmlPath: string, outputPath: string): Promise<void> {
  await generateScreenshotWithPlaywright(htmlPath, outputPath);
}

/**
 * Generate screenshot with Playwright
 */
export async function generateScreenshotWithPlaywright(htmlPath: string, outputPath: string): Promise<void> {
  const url = `file://${resolve(htmlPath)}`;
  execSync(
    `npx -y playwright screenshot --full-page --wait-for-timeout 1200 --viewport-size "1440,2200" "${url}" "${resolve(outputPath)}"`,
    { stdio: 'pipe' },
  );
}
