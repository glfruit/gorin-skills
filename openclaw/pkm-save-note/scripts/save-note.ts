#!/usr/bin/env node
/**
 * PKM Save Note - Main Entry Point
 * Universal note saving interface for agents
 */

import { existsSync, mkdirSync, writeFileSync, readFileSync } from 'fs';
import { dirname, join, basename } from 'path';
import { homedir } from 'os';

// Configuration loading
interface PkmConfig {
  version: number;
  vault_path: string;
  vault_structure: {
    zettels: {
      fleeting: string;
      literature: string;
      permanent: string;
      structure: string;
    };
    para: {
      projects: string;
      areas: string;
      works?: string;
    };
  };
  file_naming: {
    format: string;
    id_format: string;
    separator: string;
  };
  type_mapping: Record<string, { dir: string; template: string }>;
  auto_create_dirs: boolean;
  similarity_threshold: number;
  auto_link_threshold: number;
}

function expandHome(pathValue: string): string {
  return pathValue.startsWith('~/') ? join(homedir(), pathValue.slice(2)) : pathValue;
}

function loadConfig(): PkmConfig {
  const coreConfigPath = join(homedir(), '.openclaw/pkm/config.json');
  const legacyConfigPath = join(homedir(), '.openclaw/pkm-save-note.json');
  const defaultConfig: PkmConfig = {
    version: 1,
    vault_path: process.env.OBSIDIAN_VAULT_PATH ||
      `${homedir()}/Library/Mobile Documents/iCloud~md~obsidian/Documents/Vault`,
    vault_structure: {
      zettels: {
        fleeting: 'Zettels/1-Fleeting',
        literature: 'Zettels/2-Literature',
        permanent: 'Zettels/3-Permanent',
        structure: 'Zettels/4-Structure'
      },
      para: {
        projects: 'Efforts/1-Projects',
        areas: 'Efforts/2-Areas',
        works: 'Efforts/3-Works'
      }
    },
    file_naming: {
      format: 'id-title',
      id_format: 'YYYYMMDDHHMM',
      separator: '-'
    },
    type_mapping: {
      log: { dir: 'Zettels/1-Fleeting', template: 'fleeting' },
      thought: { dir: 'Zettels/1-Fleeting', template: 'fleeting' },
      meeting: { dir: 'Efforts/1-Projects/{{project}}', template: 'meeting' },
      plan: { dir: 'Efforts/1-Projects/{{project}}', template: 'plan' },
      summary: { dir: 'Zettels/3-Permanent', template: 'zettel' },
      review: { dir: 'Efforts/2-Areas/{{area}}', template: 'review' },
      decision: { dir: 'Zettels/3-Permanent', template: 'zettel' }
    },
    auto_create_dirs: true,
    similarity_threshold: 0.5,
    auto_link_threshold: 0.7
  };

  try {
    if (existsSync(coreConfigPath)) {
      const coreConfig = JSON.parse(readFileSync(coreConfigPath, 'utf-8'));
      return {
        ...defaultConfig,
        vault_path: expandHome(process.env.OBSIDIAN_VAULT_PATH || coreConfig.vault?.default_path || defaultConfig.vault_path),
        vault_structure: coreConfig.vault?.structure || defaultConfig.vault_structure,
        type_mapping: coreConfig.classification?.type_mapping || defaultConfig.type_mapping,
        auto_create_dirs: coreConfig.classification?.auto_create_dirs ?? defaultConfig.auto_create_dirs,
        similarity_threshold: coreConfig.deduplication?.threshold || defaultConfig.similarity_threshold,
        auto_link_threshold: defaultConfig.auto_link_threshold
      };
    }

    if (existsSync(legacyConfigPath)) {
      const configContent = readFileSync(legacyConfigPath, 'utf-8');
      const userConfig = JSON.parse(configContent);
      return { ...defaultConfig, ...userConfig, vault_path: expandHome(userConfig.vault_path || defaultConfig.vault_path) };
    }
  } catch (error) {
    console.warn('Warning: Could not load config file, using defaults');
  }

  return defaultConfig;
}

const CONFIG = loadConfig();
const VAULT_PATH = CONFIG.vault_path;
const SIMILARITY_THRESHOLD = CONFIG.similarity_threshold;
const AUTO_LINK_THRESHOLD = CONFIG.auto_link_threshold;
const TYPE_LOCATIONS = CONFIG.type_mapping;

// Auto-tagging keywords
const TOPIC_KEYWORDS: Record<string, string[]> = {
  ai: ['AI', 'agent', 'Claude', 'GPT', '模型', 'LLM', '大模型'],
  openclaw: ['OpenClaw', 'skill', 'agent', 'Open Claw'],
  learning: ['学习', '笔记', '阅读', '总结', '知识'],
  work: ['工作', '项目', '任务', '会议', '进度'],
  productivity: ['效率', '流程', '自动化', '工具'],
  coding: ['代码', '编程', '开发', 'bug', 'feature'],
};

interface SaveNoteInput {
  content: string;
  title?: string;
  type?: string;
  project?: string;
  area?: string;
  tags?: string[];
  links?: string[];
  template?: string;
  source_url?: string;
  author?: string;
  auto_link?: boolean;
  para_classify?: boolean;
  dry_run?: boolean;
  up?: string;
  tldr?: string;
}

interface SaveNoteOutput {
  success: boolean;
  file_path?: string;
  para_location?: string;
  links_created?: string[];
  tags_assigned?: string[];
  related_notes?: Array<{ id: string; title: string; score: number }>;
  warnings?: string[];
  error?: string;
}

/**
 * Main function - parse input and save note
 */
async function main(): Promise<void> {
  try {
    // Parse input from command line or stdin
    const input = parseInput();

    if (!input.content) {
      console.error('Error: content is required');
      process.exit(1);
    }

    const result = await saveNote(input);
    console.log(JSON.stringify(result, null, 2));
    process.exit(result.success ? 0 : 1);
  } catch (error) {
    console.error('Error:', error);
    process.exit(1);
  }
}

/**
 * Parse input from arguments or stdin
 */
function parseInput(): SaveNoteInput {
  const args = process.argv.slice(2);

  // Check if JSON input provided
  if (args.length === 1 && args[0].startsWith('{')) {
    return JSON.parse(args[0]);
  }

  // Parse named arguments
  const input: Partial<SaveNoteInput> = {};
  for (let i = 0; i < args.length; i += 2) {
    const key = args[i].replace(/^--/, '');
    const value = args[i + 1];
    if (key && value) {
      if (key === 'tags' || key === 'links') {
        (input as any)[key] = value.split(',');
      } else if (key === 'auto_link' || key === 'para_classify' || key === 'dry_run') {
        (input as any)[key] = value === 'true';
      } else {
        (input as any)[key] = value;
      }
    }
  }

  // If no content from args, try stdin
  if (!input.content && !process.stdin.isTTY) {
    const stdin = readFileSync(0, 'utf-8');
    if (stdin) {
      try {
        return JSON.parse(stdin);
      } catch {
        input.content = stdin.trim();
      }
    }
  }

  return input as SaveNoteInput;
}

/**
 * Main save note logic
 */
async function saveNote(input: SaveNoteInput): Promise<SaveNoteOutput> {
  const warnings: string[] = [];

  // 1. Validate and prepare
  const type = (input.type || 'log').toLowerCase();
  const title = input.title || generateTitle(input.content);
  const id = generateId();

  // 2. Determine target location
  let targetDir = determineLocation(type, input.project, input.area, input.content);

  // 3. Check vault exists
  if (!existsSync(VAULT_PATH)) {
    return {
      success: false,
      error: `Vault not found at: ${VAULT_PATH}. Set OBSIDIAN_VAULT_PATH environment variable.`
    };
  }

  // 4. Generate tags
  const autoTags = generateTags(input.content, type, input.tags);

  // 5. Find related notes
  let relatedNotes: Array<{ id: string; title: string; score: number }> = [];
  let linksToCreate: string[] = [];

  if (input.auto_link !== false) {
    relatedNotes = findRelatedNotes(input.content, VAULT_PATH);
    linksToCreate = relatedNotes
      .filter(n => n.score >= AUTO_LINK_THRESHOLD)
      .map(n => n.id);
  }

  // 6. Build PARA links
  const paraLinks: string[] = [];
  if (input.project) paraLinks.push(`[[Project: ${input.project}]]`);
  if (input.area) paraLinks.push(`[[Area: ${input.area}]]`);

  // 7. Apply template
  const template = input.template || TYPE_LOCATIONS[type]?.template || 'standard';
  const noteContent = applyTemplate(template, {
    id,
    title,
    content: input.content,
    type,
    tags: autoTags,
    created: new Date().toISOString().split('T')[0],
    modified: new Date().toISOString().split('T')[0],
    project: input.project,
    area: input.area,
    up: input.up || 'Zettel Index',
    tldr: input.tldr,
    source_url: input.source_url,
    author: input.author,
    links: [...paraLinks, ...linksToCreate, ...(input.links || [])],
    relatedNotes: relatedNotes.filter(n => n.score >= 0.4)
  });

  // 8. Determine file path
  const safeTitle = title.replace(/[^\w\s-]/g, '').replace(/\s+/g, '-').slice(0, 50);
  const filename = `${id}-${safeTitle}.md`;
  const fullPath = join(VAULT_PATH, targetDir, filename);

  // 9. Create directory if needed (respect auto_create_dirs config)
  const dirPath = dirname(fullPath);
  if (!existsSync(dirPath)) {
    if (!CONFIG.auto_create_dirs) {
      return {
        success: false,
        error: `Directory does not exist: ${dirPath}. Set auto_create_dirs to true in config to auto-create directories.`
      };
    }
    if (input.dry_run) {
      warnings.push(`Would create directory: ${dirPath}`);
    } else {
      mkdirSync(dirPath, { recursive: true });
    }
  }

  // 10. Write file
  if (input.dry_run) {
    warnings.push(`Would write to: ${fullPath}`);
    return {
      success: true,
      file_path: fullPath,
      para_location: targetDir,
      links_created: linksToCreate,
      tags_assigned: autoTags,
      related_notes: relatedNotes.slice(0, 5),
      warnings
    };
  }

  writeFileSync(fullPath, noteContent, 'utf-8');

  // 11. Update indices (simplified - can be enhanced)
  updateIndices(targetDir, title, id, VAULT_PATH);

  return {
    success: true,
    file_path: fullPath,
    para_location: targetDir,
    links_created: linksToCreate,
    tags_assigned: autoTags,
    related_notes: relatedNotes.slice(0, 5),
    warnings: warnings.length > 0 ? warnings : undefined
  };
}

/**
 * Generate unique ID (YYYYMMDDHHMM format)
 */
function generateId(): string {
  const now = new Date();
  return now.getFullYear().toString() +
    String(now.getMonth() + 1).padStart(2, '0') +
    String(now.getDate()).padStart(2, '0') +
    String(now.getHours()).padStart(2, '0') +
    String(now.getMinutes()).padStart(2, '0');
}

/**
 * Generate title from content
 */
function generateTitle(content: string): string {
  // Try first line
  const firstLine = content.split('\n')[0].trim();
  if (firstLine && firstLine.length < 100) {
    return firstLine.replace(/^#+\s*/, '');
  }

  // Try to extract key phrase
  const words = content.slice(0, 200).split(/\s+/);
  const keyWords = words.filter(w => w.length > 3).slice(0, 5);
  return keyWords.join(' ') || 'Note';
}

/**
 * Determine target location based on type and content
 * Follows zk-para-zettel directory structure
 * 
 * Rules:
 * 1. If project specified -> create Efforts/1-Projects/{project}/ if not exists
 * 2. If area specified -> create Efforts/2-Areas/{area}/ if not exists  
 * 3. Auto-detect from content if type matches
 * 4. Type-based defaults without falling back to Unsorted
 */
function determineLocation(
  type: string,
  project?: string,
  area?: string,
  content?: string
): string {
  // Priority 1: Explicit project - create if not exists
  if (project) {
    const projectPath = `${CONFIG.vault_structure.para.projects}/${project}`;
    const fullProjectPath = join(VAULT_PATH, projectPath);
    
    if (!existsSync(fullProjectPath) && CONFIG.auto_create_dirs) {
      // Create the project directory
      try {
        mkdirSync(fullProjectPath, { recursive: true });
        console.log(`Created project directory: ${projectPath}`);
        
        // Create a project index file
        const indexContent = `---
id: ${project.toLowerCase().replace(/\s+/g, '-')}
title: "Project: ${project}"
type: project
created: ${new Date().toISOString().split('T')[0]}
---

# Project: ${project}

## Overview

## Goals

## Timeline

## Notes

## Related
- [[Projects MOC]]
`;
        writeFileSync(join(fullProjectPath, 'README.md'), indexContent, 'utf-8');
      } catch (error) {
        console.warn(`Warning: Could not create project directory: ${error}`);
      }
    }
    
    return projectPath;
  }

  // Priority 2: Explicit area - create if not exists
  if (area) {
    const areaPath = `${CONFIG.vault_structure.para.areas}/${area}`;
    const fullAreaPath = join(VAULT_PATH, areaPath);
    
    if (!existsSync(fullAreaPath) && CONFIG.auto_create_dirs) {
      // Create the area directory
      try {
        mkdirSync(fullAreaPath, { recursive: true });
        console.log(`Created area directory: ${areaPath}`);
        
        // Create an area index file
        const indexContent = `---
id: ${area.toLowerCase().replace(/\s+/g, '-')}
title: "Area: ${area}"
type: area
created: ${new Date().toISOString().split('T')[0]}
---

# Area: ${area}

## Overview

## Responsibilities

## Standards

## Notes

## Related
- [[Areas MOC]]
`;
        writeFileSync(join(fullAreaPath, 'README.md'), indexContent, 'utf-8');
      } catch (error) {
        console.warn(`Warning: Could not create area directory: ${error}`);
      }
    }
    
    return areaPath;
  }

  // Priority 3: Auto-detect project from content
  if (content && (type === 'meeting' || type === 'plan')) {
    const projects = listProjects(VAULT_PATH);
    for (const proj of projects) {
      if (content.toLowerCase().includes(proj.toLowerCase())) {
        return `${CONFIG.vault_structure.para.projects}/${proj}`;
      }
    }
  }

  // Priority 4: Auto-detect area from content
  if (content && (type === 'review' || type === 'summary')) {
    const areas = listAreas(VAULT_PATH);
    for (const a of areas) {
      if (content.toLowerCase().includes(a.toLowerCase())) {
        return `${CONFIG.vault_structure.para.areas}/${a}`;
      }
    }
  }

  // Priority 5: Type-based default from config
  // Use base paths without project/area placeholders
  const typeConfig = TYPE_LOCATIONS[type];
  if (typeConfig) {
    // For types that expect project/area but none provided, use appropriate base
    if (type === 'meeting' || type === 'plan') {
      return CONFIG.vault_structure.para.projects;  // Save to Projects root
    }
    if (type === 'review') {
      return CONFIG.vault_structure.para.areas;  // Save to Areas root
    }
    // For other types, use the configured directory
    return typeConfig.dir;
  }

  // Default to Zettels/1-Fleeting
  return CONFIG.vault_structure.zettels.fleeting;
}

/**
 * List existing projects from Efforts/1-Projects/
 */
function listProjects(vaultPath: string): string[] {
  try {
    const { readdirSync } = require('fs');
    const projectsPath = join(vaultPath, CONFIG.vault_structure.para.projects);
    if (!existsSync(projectsPath)) return [];
    return readdirSync(projectsPath, { withFileTypes: true })
      .filter((d: any) => d.isDirectory())
      .map((d: any) => d.name);
  } catch {
    return [];
  }
}

/**
 * List existing areas from Efforts/2-Areas/
 */
function listAreas(vaultPath: string): string[] {
  try {
    const { readdirSync } = require('fs');
    const areasPath = join(vaultPath, CONFIG.vault_structure.para.areas);
    if (!existsSync(areasPath)) return [];
    return readdirSync(areasPath, { withFileTypes: true })
      .filter((d: any) => d.isDirectory())
      .map((d: any) => d.name);
  } catch {
    return [];
  }
}

/**
 * Generate tags based on content
 */
function generateTags(content: string, type: string, extraTags?: string[]): string[] {
  const tags = new Set<string>([type]);
  const lowerContent = content.toLowerCase();

  // Add topic tags
  for (const [topic, keywords] of Object.entries(TOPIC_KEYWORDS)) {
    for (const keyword of keywords) {
      if (lowerContent.includes(keyword.toLowerCase())) {
        tags.add(topic);
        break;
      }
    }
  }

  // Add extra tags
  if (extraTags) {
    extraTags.forEach(t => tags.add(t));
  }

  return Array.from(tags);
}

/**
 * Find related notes from Zettels/3-Permanent/
 * Follows zk-para-zettel structure
 */
function findRelatedNotes(content: string, vaultPath: string): Array<{ id: string; title: string; score: number }> {
  const related: Array<{ id: string; title: string; score: number }> = [];

  try {
    const { readdirSync } = require('fs');
    const zettelsPath = join(vaultPath, CONFIG.vault_structure.zettels.permanent);

    if (!existsSync(zettelsPath)) return related;

    const files = readdirSync(zettelsPath)
      .filter((f: string) => f.endsWith('.md'))
      .slice(0, 20); // Limit for performance

    const contentWords = new Set(content.toLowerCase().split(/\s+/));

    for (const file of files) {
      try {
        const filePath = join(zettelsPath, file);
        const fileContent = readFileSync(filePath, 'utf-8');
        const fileWords = new Set(fileContent.toLowerCase().split(/\s+/));

        // Simple Jaccard similarity
        const intersection = new Set([...contentWords].filter(x => fileWords.has(x)));
        const union = new Set([...contentWords, ...fileWords]);
        const score = intersection.size / union.size;

        if (score > SIMILARITY_THRESHOLD) {
          // Extract title from frontmatter or filename
          const titleMatch = fileContent.match(/title:\s*["']?([^"'\n]+)["']?/);
          const title = titleMatch ? titleMatch[1] : file.replace('.md', '');

          related.push({
            id: file.replace('.md', ''),
            title,
            score: Math.round(score * 100) / 100
          });
        }
      } catch {
        // Skip problematic files
      }
    }

    return related.sort((a, b) => b.score - a.score).slice(0, 5);
  } catch {
    return related;
  }
}

/**
 * Apply template with variables
 */
function applyTemplate(template: string, vars: Record<string, any>): string {
  const templates: Record<string, string> = {
    fleeting: `---
id: {{id}}
title: "{{title}}"
type: {{type}}
tags:
{{#tags}}  - {{.}}
{{/tags}}created: {{created}}
modified: {{modified}}
{{#up}}up: "[[{{up}}]]"
{{/up}}---

# {{title}}

{{content}}

{{#relatedNotes}}
## Related Notes
{{#relatedNotes}}
- [[{{id}}]] - {{title}} ({{score}})
{{/relatedNotes}}
{{/relatedNotes}}
`,

    zettel: `---
id: {{id}}
title: "{{title}}"
type: {{type}}
tags:
{{#tags}}  - {{.}}
{{/tags}}created: {{created}}
modified: {{modified}}
{{#project}}
project: "{{project}}"
{{/project}}
{{#area}}
area: "{{area}}"
{{/area}}
up: "[[{{up}}]]"
related:
{{#links}}  - "{{.}}"
{{/links}}---

# {{title}}

{{#tldr}}
## TL;DR
> {{tldr}}

{{/tldr}}
## 核心观点

{{content}}

## 思考



{{#relatedNotes}}
## 相关笔记
{{#relatedNotes}}
- [[{{id}}]] - {{title}}
{{/relatedNotes}}
{{/relatedNotes}}
`,

    meeting: `---
id: {{id}}
title: "会议: {{title}}"
type: meeting
date: {{created}}
{{#project}}
project: "[[Project: {{project}}]]"
{{/project}}
participants: []
tags:
  - meeting
{{#tags}}  - {{.}}
{{/tags}}---

# 会议: {{title}}

**日期**: {{created}}
{{#project}}
**项目**: [[Project: {{project}}]]
{{/project}}
**参与者**:

## 议程



## 讨论要点

{{content}}

## 行动项

- [ ]

{{#links}}
## 相关
{{#links}}
- {{.}}
{{/links}}
{{/links}}
`,

    plan: `---
id: {{id}}
title: "{{title}}"
type: plan
date: {{created}}
{{#project}}
project: "[[Project: {{project}}]]"
{{/project}}
status: draft
tags:
  - plan
{{#tags}}  - {{.}}
{{/tags}}---

# {{title}}

## 目标



## 方案

{{content}}

## 时间表



## 资源



{{#links}}
## 相关
{{#links}}
- {{.}}
{{/links}}
{{/links}}
`,

    review: `---
id: {{id}}
title: "{{title}}"
type: review
period: {{created}}
{{#area}}
area: "[[Area: {{area}}]]"
{{/area}}
tags:
  - review
{{#tags}}  - {{.}}
{{/tags}}---

# {{title}}

## 总结

{{content}}

## 亮点



## 改进



## 下一步



{{#links}}
## 相关
{{#links}}
- {{.}}
{{/links}}
{{/links}}
`,

    standard: `---
id: {{id}}
title: "{{title}}"
type: {{type}}
tags:
{{#tags}}  - {{.}}
{{/tags}}created: {{created}}
modified: {{modified}}
---

# {{title}}

{{content}}
`,

    literature: `---
id: {{id}}
title: "{{title}}"
type: literature
tags:
{{#tags}}  - {{.}}
{{/tags}}created: {{created}}
modified: {{modified}}
{{#source_url}}source_url: {{source_url}}
{{/source_url}}{{#author}}author: {{author}}
{{/author}}---

# {{title}}

{{#source_url}}**原文链接**: {{source_url}}
{{/source_url}}{{#author}}**作者**: {{author}}
{{/author}}**抓取时间**: {{created}}

---

## 文献摘要

{{content}}

{{#relatedNotes}}
## Related Notes
{{#relatedNotes}}
- [[{{id}}]] - {{title}} ({{score}})
{{/relatedNotes}}
{{/relatedNotes}}

---
*源文献笔记，用于追溯知识来源*
`
  };

  let templateStr = templates[template] || templates.standard;

  // Simple template substitution
  templateStr = templateStr.replace(/\{\{\{(\w+)\}\}\}/g, (match, key) => {
    const value = vars[key];
    if (Array.isArray(value)) {
      return value.map(v => `  - ${v}`).join('\n');
    }
    return value !== undefined ? String(value) : '';
  });

  templateStr = templateStr.replace(/\{\{(\w+)\}\}/g, (match, key) => {
    const value = vars[key];
    return value !== undefined ? String(value) : '';
  });

  // Handle conditionals {{#key}}...{{/key}}
  templateStr = templateStr.replace(/\{\{#(\w+)\}\}([\s\S]*?)\{\{\/\1\}\}/g, (match, key, content) => {
    const value = vars[key];
    if (!value || (Array.isArray(value) && value.length === 0)) {
      return '';
    }
    if (Array.isArray(value)) {
      return value.map(item => {
        if (typeof item === 'object') {
          let itemContent = content;
          for (const [k, v] of Object.entries(item)) {
            itemContent = itemContent.replace(new RegExp(`\\{\\{${k}\\}\\}`, 'g'), String(v));
          }
          return itemContent;
        }
        return content.replace(/\{\{\.\}\}/g, String(item));
      }).join('');
    }
    return content;
  });

  return templateStr;
}

/**
 * Update index files (simplified)
 */
function updateIndices(targetDir: string, title: string, id: string, vaultPath: string): void {
  // This can be enhanced to update:
  // - Daily notes index
  // - Project/Area indices
  // - Tag indices
  // For now, we just ensure the basic structure exists
}

// Run main function
main();
