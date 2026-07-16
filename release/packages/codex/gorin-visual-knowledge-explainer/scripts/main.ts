#!/usr/bin/env node
/**
 * main.ts - Visual Knowledge Explainer
 *
 * Minimal production entrypoint:
 * 1. Read markdown-like input
 * 2. Detect content type (unless overridden)
 * 3. Select template + theme
 * 4. Render a single-file HTML explainer
 * 5. Optionally try screenshot generation
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { resolve, dirname, basename, extname, join } from 'path';
import { fileURLToPath } from 'url';
import { detectContentType } from './detect-content-type.ts';
import { recommendRenderStrategy } from './select-template.ts';
import {
  loadTemplate,
  renderHtml,
  generateMetadataHtml,
  generateLearningObjectivesHtml,
  generateSummaryHtml,
  generateReferenceHtml,
  generateModuleHtml,
  generateWorkflowStepsHtml,
  generateSlideHtml,
} from './render-html.ts';
import { generateScreenshot } from './generate-screenshot.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT_DIR = dirname(__dirname);

type ParsedDoc = {
  title: string;
  subtitle: string;
  sections: Array<{ heading: string; level: number; lines: string[] }>;
  metadata: Record<string, string>;
  learningObjectives: string[];
  prerequisites: string[];
  references: string[];
  summary: string;
  keyTakeaways: string[];
};

const args = process.argv.slice(2);
let contentFile = '';
let themeArg = '';
let outputDir = join(process.env.HOME || '.', 'Downloads/visual-explainer');
let screenshot = false;
let contentTypeArg = '';

for (let i = 0; i < args.length; i++) {
  const arg = args[i];
  if (arg === '--theme' && args[i + 1]) {
    themeArg = args[++i];
  } else if (arg === '--output-dir' && args[i + 1]) {
    outputDir = args[++i];
  } else if (arg === '--screenshot') {
    screenshot = true;
  } else if (arg === '--type' && args[i + 1]) {
    contentTypeArg = args[++i];
  } else if (!arg.startsWith('-')) {
    contentFile = arg;
  }
}

if (!contentFile) {
  console.error('Usage: visual-knowledge-explainer <content.md> [options]');
  process.exit(1);
}

const inputPath = resolve(contentFile);
if (!existsSync(inputPath)) {
  console.error(`Error: File not found: ${inputPath}`);
  process.exit(1);
}

mkdirSync(outputDir, { recursive: true });

const source = readFileSync(inputPath, 'utf-8');
const parsed = parseDocument(source, inputPath);
const detectedType = contentTypeArg || detectContentType(source);
const strategy = recommendRenderStrategy(detectedType);
const theme = themeArg || strategy.theme;
const templateFile = strategy.template;
const templatePath = join(ROOT_DIR, 'templates', templateFile);

if (!existsSync(templatePath)) {
  console.error(`Error: Template not found: ${templatePath}`);
  process.exit(1);
}

const template = loadTemplate(templatePath);
const html = renderForTemplate(templateFile, template, parsed, theme, detectedType);
const timestamp = formatTimestamp(new Date());
const slug = slugify(parsed.title || basename(inputPath, extname(inputPath)));
const outputPath = join(outputDir, `${slug}-${timestamp}.html`);

writeFileSync(outputPath, html, 'utf-8');

console.log(`✅ Generated HTML: ${outputPath}`);
console.log(`   Content type: ${detectedType}`);
console.log(`   Template: ${templateFile}`);
console.log(`   Theme: ${theme}`);

if (screenshot) {
  const pngPath = join(outputDir, `${slug}-${timestamp}.png`);
  try {
    await generateScreenshot(outputPath, pngPath);
  } catch (error) {
    console.warn(`⚠️ Screenshot generation failed: ${String(error)}`);
  }
}

function renderForTemplate(
  templateFile: string,
  template: string,
  parsed: ParsedDoc,
  theme: string,
  detectedType: string,
): string {
  const themedTemplate = applyThemeOverride(template, theme);
  const baseParams = {
    title: escapeHtml(parsed.title),
    subtitle: escapeHtml(parsed.subtitle || defaultSubtitle(detectedType)),
    metadata_html: generateMetadataHtml(parsed.metadata),
    learning_objectives_html: wrapSection(
      'learning-objectives',
      'Learning Objectives',
      parsed.learningObjectives,
    ),
    prerequisites_html: wrapSection('prerequisites', 'Prerequisites', parsed.prerequisites),
    summary_html: generateSummaryHtml(escapeHtml(parsed.summary)),
    reference_html: generateReferenceHtml(parsed.references.map(escapeHtml)),
    modules_html: buildModulesHtml(parsed.sections),
    review_html: buildReviewHtml(parsed.keyTakeaways),
    key_takeaways_html: buildTakeawayHtml(parsed.keyTakeaways),
  };

  if (templateFile === 'workflow-page.html') {
    const workflowSteps = parsed.sections.map((section) => ({
      title: escapeHtml(section.heading),
      content: markdownToHtml(section.lines.join('\n')),
    }));
    return renderHtml(themedTemplate, {
      ...baseParams,
      workflow_steps_html: generateWorkflowStepsHtml(workflowSteps),
      mermaid_code: buildFallbackMermaid(parsed.sections),
      visual_aids_html: '',
      variations_html: baseParams.key_takeaways_html,
    });
  }

  if (templateFile === 'comparison-table.html') {
    const table = buildComparisonTable(parsed.sections);
    return renderHtml(themedTemplate, {
      ...baseParams,
      table_headers_html: table.headersHtml,
      table_rows_html: table.rowsHtml,
      key_takeaways_html: buildTakeawayHtml(parsed.keyTakeaways),
    });
  }

  if (templateFile === 'slide-deck.html') {
    return renderHtml(themedTemplate, {
      ...baseParams,
      slides_html: buildSlidesHtml(parsed),
    });
  }

  return renderHtml(themedTemplate, baseParams);
}

function parseDocument(source: string, inputPath: string): ParsedDoc {
  const lines = source.replace(/\r\n/g, '\n').split('\n');
  const title =
    lines.find((line) => line.startsWith('# '))?.replace(/^# /, '').trim() ||
    basename(inputPath, extname(inputPath));

  const sections: ParsedDoc['sections'] = [];
  let currentSection: ParsedDoc['sections'][number] | null = null;

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    const h2 = line.match(/^##\s+(.+)$/);
    const h3 = line.match(/^###\s+(.+)$/);

    if (h2) {
      currentSection = { heading: h2[1].trim(), level: 2, lines: [] };
      sections.push(currentSection);
      continue;
    }

    if (h3) {
      currentSection = { heading: h3[1].trim(), level: 3, lines: [] };
      sections.push(currentSection);
      continue;
    }

    if (line.startsWith('# ')) {
      continue;
    }

    if (!currentSection) {
      currentSection = { heading: 'Overview', level: 2, lines: [] };
      sections.push(currentSection);
    }

    currentSection.lines.push(line);
  }

  const parsed: ParsedDoc = {
    title,
    subtitle: '',
    sections: [],
    metadata: {},
    learningObjectives: [],
    prerequisites: [],
    references: [],
    summary: '',
    keyTakeaways: [],
  };

  for (const section of sections) {
    const heading = normalizeHeading(section.heading);
    const items = extractListItems(section.lines);
    const plain = section.lines.join('\n').trim();

    if (isSummaryHeading(heading)) {
      parsed.summary = plain || items.join('；');
      continue;
    }

    if (isObjectivesHeading(heading)) {
      parsed.learningObjectives.push(...(items.length ? items : splitSentences(plain)));
      continue;
    }

    if (isReferenceHeading(heading)) {
      parsed.references.push(...(items.length ? items : splitSentences(plain)));
      continue;
    }

    if (isPrereqHeading(heading)) {
      parsed.prerequisites.push(...(items.length ? items : splitSentences(plain)));
      continue;
    }

    if (isAuthorHeading(heading)) {
      parsed.metadata['Author'] = items[0] || compactText(plain);
      continue;
    }

    if (heading.includes('作者') && !parsed.metadata['Author']) {
      parsed.metadata['Author'] = compactText(plain);
      continue;
    }

    if (heading.includes('常见误解') || heading.includes('关键结论') || heading.includes('要点')) {
      parsed.keyTakeaways.push(...(items.length ? items : splitSentences(plain)));
    }

    parsed.sections.push(section);
  }

  parsed.subtitle = buildSubtitle(parsed);
  if (parsed.keyTakeaways.length === 0) {
    parsed.keyTakeaways = parsed.learningObjectives.slice(0, 5);
  }

  return parsed;
}

function buildSubtitle(parsed: ParsedDoc): string {
  if (parsed.summary) return compactText(parsed.summary).slice(0, 80);
  const firstSection = parsed.sections.find((section) => section.lines.join('').trim().length > 0);
  if (!firstSection) return '结构化讲解页';
  return compactText(firstSection.lines.join(' ')).slice(0, 80);
}

function buildModulesHtml(sections: ParsedDoc['sections']): string {
  const filtered = sections.filter((section) => section.lines.join('').trim().length > 0);
  return filtered
    .map((section) =>
      generateModuleHtml(escapeHtml(section.heading), markdownToHtml(section.lines.join('\n'))),
    )
    .join('\n');
}

function buildReviewHtml(items: string[]): string {
  if (items.length === 0) return '';
  const lis = items.map((item) => `<li>${escapeHtml(item)}</li>`).join('');
  return `
    <section class="summary">
      <h2>Review</h2>
      <ul>${lis}</ul>
    </section>
  `;
}

function buildTakeawayHtml(items: string[]): string {
  if (items.length === 0) return '';
  const lis = items.map((item) => `<li>${escapeHtml(item)}</li>`).join('');
  return `
    <section class="key-takeaways">
      <h2>Key Takeaways</h2>
      <ul>${lis}</ul>
    </section>
  `;
}

function buildSlidesHtml(parsed: ParsedDoc): string {
  const slides: string[] = [];
  for (const section of parsed.sections) {
    const content = compactText(section.lines.join(' '));
    slides.push(generateSlideHtml(escapeHtml(section.heading), escapeHtml(content)));
  }
  return slides.join('\n');
}

function buildFallbackMermaid(sections: ParsedDoc['sections']): string {
  if (sections.length === 0) {
    return 'graph TD\n  A[Start] --> B[Review]';
  }
  const nodes = sections
    .slice(0, 6)
    .map((section, index) => `${String.fromCharCode(65 + index)}[${escapeMermaid(section.heading)}]`);
  const edges = sections
    .slice(0, 5)
    .map((_, index) => `${String.fromCharCode(65 + index)} --> ${String.fromCharCode(66 + index)}`);
  return `graph TD\n  ${nodes.join('\n  ')}\n  ${edges.join('\n  ')}`;
}

function buildComparisonTable(sections: ParsedDoc['sections']): { headersHtml: string; rowsHtml: string } {
  const headers = ['维度', '说明'];
  const rows = sections.map((section) => [
    escapeHtml(section.heading),
    compactText(section.lines.join(' ')) || '—',
  ]);
  return {
    headersHtml: `<tr>${headers.map((header) => `<th>${header}</th>`).join('')}</tr>`,
    rowsHtml: rows.map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join('')}</tr>`).join('\n'),
  };
}

function wrapSection(className: string, heading: string, items: string[]): string {
  if (items.length === 0) return '';
  return `
    <section class="${className}">
      <h2>${heading}</h2>
      <ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
    </section>
  `;
}

function markdownToHtml(markdown: string): string {
  const blocks = markdown
    .split(/\n\s*\n/)
    .map((block) => block.trim())
    .filter(Boolean);

  return blocks
    .map((block) => {
      const lines = block.split('\n').map((line) => line.trim());

      if (lines.every((line) => /^[-*]\s+/.test(line) || /^\d+\.\s+/.test(line))) {
        const items = lines
          .map((line) => line.replace(/^[-*]\s+/, '').replace(/^\d+\.\s+/, '').trim())
          .filter(Boolean)
          .map((item) => `<li>${inlineMarkdownToHtml(item)}</li>`)
          .join('');
        return `<ul>${items}</ul>`;
      }

      return lines
        .filter(Boolean)
        .map((line) => `<p>${inlineMarkdownToHtml(line)}</p>`)
        .join('\n');
    })
    .join('\n');
}

function inlineMarkdownToHtml(text: string): string {
  let html = escapeHtml(text);
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
  html = html.replace(/`(.+?)`/g, '<code>$1</code>');
  return html;
}

function extractListItems(lines: string[]): string[] {
  return lines
    .map((line) => line.trim())
    .filter((line) => /^[-*]\s+/.test(line) || /^\d+\.\s+/.test(line))
    .map((line) => line.replace(/^[-*]\s+/, '').replace(/^\d+\.\s+/, '').trim())
    .filter(Boolean);
}

function splitSentences(text: string): string[] {
  return text
    .split(/[。；;\n]/)
    .map((part) => part.trim())
    .filter(Boolean);
}

function compactText(text: string): string {
  return text.replace(/\s+/g, ' ').trim();
}

function defaultSubtitle(contentType: string): string {
  return `${contentType} · 结构化讲解页`;
}

function applyThemeOverride(template: string, theme: string): string {
  const overrides = themeCssOverrides(theme);
  if (!overrides) return template;
  return template.replace('</style>', `${overrides}\n  </style>`);
}

function themeCssOverrides(theme: string): string {
  const presets: Record<string, string> = {
    default: `
    :root {
      --theme-primary: #2563eb;
      --theme-secondary: #60a5fa;
      --theme-text: #1e293b;
      --theme-background: #f8fafc;
      --theme-card-bg: #ffffff;
      --theme-card-border: #e2e8f0;
      --theme-heading-text: #0f172a;
      --border-radius: 8px;
      --shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }`,
    grace: `
    :root {
      --theme-primary: #4f46e5;
      --theme-secondary: #818cf8;
      --theme-text: #1f2937;
      --theme-background: #f3f4f6;
      --theme-card-bg: #ffffff;
      --theme-card-border: #e5e7eb;
      --theme-heading-text: #111827;
      --border-radius: 12px;
      --shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06);
    }`,
    simple: `
    :root {
      --theme-primary: #0f766e;
      --theme-secondary: #5eead4;
      --theme-text: #111827;
      --theme-background: #ffffff;
      --theme-card-bg: #ffffff;
      --theme-card-border: #d1d5db;
      --theme-heading-text: #111827;
      --border-radius: 6px;
      --shadow: none;
    }
    .hero-section, .module, .learning-objectives, .prerequisites, .summary, .reference, .comparison-table, .step, .slide {
      box-shadow: none !important;
      border-radius: 6px !important;
    }`,
    modern: `
    :root {
      --theme-primary: #0ea5e9;
      --theme-secondary: #38bdf8;
      --theme-text: #0f172a;
      --theme-background: #e2e8f0;
      --theme-card-bg: #ffffff;
      --theme-card-border: #cbd5e1;
      --theme-heading-text: #020617;
      --border-radius: 18px;
      --shadow: 0 14px 30px rgba(15,23,42,0.08);
    }
    .hero-section, .module, .learning-objectives, .prerequisites, .summary, .reference, .comparison-table, .step, .slide {
      border-radius: 18px !important;
      box-shadow: var(--shadow) !important;
    }
    .metadata span {
      border-radius: 999px !important;
    }`,
  };

  return presets[theme] || '';
}

function normalizeHeading(heading: string): string {
  return heading.replace(/\s+/g, '').toLowerCase();
}

function isSummaryHeading(heading: string): boolean {
  return ['内容概要', '概要', '摘要', '总结', '小结', 'summary'].some((key) => heading.includes(key));
}

function isObjectivesHeading(heading: string): boolean {
  return ['学习目标', '目标', 'objectives'].some((key) => heading.includes(key));
}

function isReferenceHeading(heading: string): boolean {
  return ['参考', '推荐阅读', '相关阅读', 'references'].some((key) => heading.includes(key));
}

function isPrereqHeading(heading: string): boolean {
  return ['前置要求', '先修', 'prerequisite'].some((key) => heading.includes(key));
}

function isAuthorHeading(heading: string): boolean {
  return ['作者简介', '作者', 'author'].some((key) => heading.includes(key));
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function escapeMermaid(text: string): string {
  return text.replace(/[[\]()"']/g, '').trim();
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\u4e00-\u9fa5]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .replace(/-+/g, '-');
}

function formatTimestamp(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, '0');
  return `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}-${pad(date.getHours())}${pad(date.getMinutes())}${pad(date.getSeconds())}`;
}
