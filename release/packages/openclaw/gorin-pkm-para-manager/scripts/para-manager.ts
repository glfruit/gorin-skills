#!/usr/bin/env node
/**
 * PKM PARA Manager - Main Implementation
 * PARA method workflow for Obsidian vaults
 */

import { existsSync, readdirSync, readFileSync, statSync, writeFileSync, mkdirSync, renameSync } from 'fs';
import { join, dirname, basename } from 'path';
import { homedir } from 'os';

const VAULT_PATH = process.env.OBSIDIAN_VAULT_PATH || `${homedir()}/Workspace/PKM/octopus`;
const EFFORTS_PATH = join(VAULT_PATH, 'Efforts');
const PROJECTS_PATH = join(EFFORTS_PATH, '1-Projects');
const AREAS_PATH = join(EFFORTS_PATH, '2-Areas');
const ZETTELS_PATH = join(VAULT_PATH, 'Zettels');
const STRUCTURE_PATH = join(ZETTELS_PATH, '4-Structure');

interface Project {
  name: string;
  path: string;
  status: 'active' | 'simmering' | 'sleeping' | 'done';
  deadline?: string;
  progress?: number;
  area?: string;
  lastModified: Date;
}

interface Area {
  name: string;
  path: string;
  standard?: string;
  lastReviewed?: string;
}

interface AreaHealth {
  name: string;
  standard?: string;
  status: 'good' | 'warning' | 'critical';
  projectCount: number;
  issues: string[];
}

async function main(): Promise<void> {
  try {
    const args = process.argv.slice(2);
    const command = args[0] || 'review';
    
    if (!existsSync(VAULT_PATH)) {
      console.error(JSON.stringify({ success: false, error: `Vault not found: ${VAULT_PATH}` }));
      process.exit(1);
    }
    
    let result: any;
    switch (command) {
      case 'review':
        result = await weeklyReview();
        break;
      case 'status':
        const projectName = args[1];
        const newStatus = args[2] as Project['status'];
        if (!projectName || !newStatus) {
          console.error(JSON.stringify({ success: false, error: 'Usage: para status [project] [active|simmering|sleeping|done]' }));
          process.exit(1);
        }
        result = await updateStatus(projectName, newStatus);
        break;
      case 'areas':
        result = await checkAreas();
        break;
      case 'false-projects':
        result = await detectFalseProjects();
        break;
      default:
        console.error(JSON.stringify({ success: false, error: `Unknown: ${command}` }));
        process.exit(1);
    }
    
    console.log(JSON.stringify(result, null, 2));
    process.exit(result.success ? 0 : 1);
  } catch (error) {
    console.error(JSON.stringify({ success: false, error: String(error) }));
    process.exit(1);
  }
}

async function weeklyReview(): Promise<any> {
  const projects = await scanProjects();
  const areas = await scanAreas();
  
  const active = projects.filter(p => p.status === 'active');
  const simmering = projects.filter(p => p.status === 'simmering');
  const sleeping = projects.filter(p => p.status === 'sleeping');
  const done = projects.filter(p => p.status === 'done');
  
  const falseProjects = projects.filter(p => {
    if (!p.deadline && p.status === 'active') return true;
    const threeMonthsAgo = new Date();
    threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);
    if (p.lastModified < threeMonthsAgo && p.status === 'active') return true;
    return false;
  });
  
  const areasHealth = areas.map(area => checkAreaHealth(area, projects));
  
  const now = new Date();
  const id = generateId();
  const weekNum = getWeekNumber(now);
  const report = generateWeeklyReport({ active, simmering, sleeping, done, falseProjects, areasHealth, id, weekNum, year: now.getFullYear() });
  
  // Save to Zettels/4-Structure/ per zk-para-zettel convention
  const safeTitle = `PARA-Weekly-Review-W${weekNum}`;
  const filename = `${id}-${safeTitle}.md`;
  const reportPath = join(STRUCTURE_PATH, filename);
  
  if (!existsSync(STRUCTURE_PATH)) mkdirSync(STRUCTURE_PATH, { recursive: true });
  writeFileSync(reportPath, report, 'utf-8');
  
  return {
    success: true,
    action: 'weekly-review',
    summary: {
      activeCount: active.length,
      simmeringCount: simmering.length,
      sleepingCount: sleeping.length,
      doneCount: done.length,
      falseProjectsCount: falseProjects.length,
      areasNeedAttention: areasHealth.filter(a => a.status !== 'good').length
    },
    active: active.map(p => ({ name: p.name, progress: p.progress, deadline: p.deadline })),
    falseProjects: falseProjects.map(p => ({ name: p.name, issue: !p.deadline ? 'no-deadline' : 'stalled' })),
    areasHealth: areasHealth.map(a => ({ name: a.name, status: a.status, issues: a.issues })),
    reportPath
  };
}

async function updateStatus(projectName: string, newStatus: Project['status']): Promise<any> {
  const projects = await scanProjects();
  const project = projects.find(p => p.name.toLowerCase().includes(projectName.toLowerCase()));
  
  if (!project) return { success: false, error: `Project not found: ${projectName}` };
  
  const oldPath = project.path;
  const newDir = join(PROJECTS_PATH, capitalize(newStatus));
  const newPath = join(newDir, basename(oldPath));
  
  if (!existsSync(newDir)) mkdirSync(newDir, { recursive: true });
  if (oldPath !== newPath) renameSync(oldPath, newPath);
  
  let content = readFileSync(newPath, 'utf-8');
  content = content.replace(/status:\s*\w+/, `status: ${newStatus}`);
  writeFileSync(newPath, content, 'utf-8');
  
  return { success: true, action: 'status-update', project: project.name, from: project.status, to: newStatus };
}

async function checkAreas(): Promise<any> {
  const areas = await scanAreas();
  const projects = await scanProjects();
  const areasHealth = areas.map(area => checkAreaHealth(area, projects));
  
  const now = new Date();
  const reportPath = join(VAULT_PATH, 'Areas/Review', `Areas-${now.toISOString().split('T')[0]}.md`);
  const report = generateAreasReport(areasHealth);
  
  if (!existsSync(dirname(reportPath))) mkdirSync(dirname(reportPath), { recursive: true });
  writeFileSync(reportPath, report, 'utf-8');
  
  return {
    success: true,
    action: 'areas-check',
    areasCount: areas.length,
    healthy: areasHealth.filter(a => a.status === 'good').length,
    warning: areasHealth.filter(a => a.status === 'warning').length,
    critical: areasHealth.filter(a => a.status === 'critical').length,
    reportPath
  };
}

async function detectFalseProjects(): Promise<any> {
  const projects = await scanProjects();
  const falseProjects = projects.filter(p => {
    if (!p.deadline && p.status === 'active') return true;
    const threeMonthsAgo = new Date();
    threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);
    if (p.lastModified < threeMonthsAgo && p.status === 'active') return true;
    return false;
  });
  
  return {
    success: true,
    action: 'false-projects',
    count: falseProjects.length,
    projects: falseProjects.map(p => ({
      name: p.name,
      issue: !p.deadline ? 'no-deadline' : 'stalled',
      suggestion: !p.deadline ? 'Move to Areas' : 'Move to Simmering/Sleeping'
    }))
  };
}

async function scanProjects(): Promise<Project[]> {
  const projects: Project[] = [];
  const statuses = ['Active', 'Simmering', 'Sleeping', 'Done'];
  
  for (const status of statuses) {
    const statusPath = join(PROJECTS_PATH, status);
    if (!existsSync(statusPath)) continue;
    
    const files = readdirSync(statusPath).filter(f => f.endsWith('.md')).map(f => join(statusPath, f));
    
    for (const filePath of files) {
      try {
        const content = readFileSync(filePath, 'utf-8');
        const stats = statSync(filePath);
        const fm = parseFrontmatter(content);
        
        projects.push({
          name: fm.title || basename(filePath, '.md'),
          path: filePath,
          status: status.toLowerCase() as Project['status'],
          deadline: fm.deadline,
          progress: parseInt(fm.progress) || undefined,
          area: fm.area,
          lastModified: stats.mtime
        });
      } catch {}
    }
  }
  return projects;
}

async function scanAreas(): Promise<Area[]> {
  const areas: Area[] = [];
  if (!existsSync(AREAS_PATH)) return areas;
  
  const dirs = readdirSync(AREAS_PATH, { withFileTypes: true }).filter(d => d.isDirectory()).map(d => d.name);
  
  for (const dir of dirs) {
    const areaPath = join(AREAS_PATH, dir);
    const indexPath = join(areaPath, `${dir}.md`);
    let standard: string | undefined;
    let lastReviewed: string | undefined;
    
    if (existsSync(indexPath)) {
      try {
        const content = readFileSync(indexPath, 'utf-8');
        const fm = parseFrontmatter(content);
        standard = fm.standard;
        lastReviewed = fm.lastReviewed;
      } catch {}
    }
    areas.push({ name: dir, path: areaPath, standard, lastReviewed });
  }
  return areas;
}

function checkAreaHealth(area: Area, projects: Project[]): AreaHealth {
  const areaProjects = projects.filter(p => p.area?.toLowerCase() === area.name.toLowerCase());
  const issues: string[] = [];
  
  if (area.lastReviewed) {
    const lastReview = new Date(area.lastReviewed);
    const monthAgo = new Date();
    monthAgo.setMonth(monthAgo.getMonth() - 1);
    if (lastReview < monthAgo) issues.push('Not reviewed in last month');
  } else issues.push('Never reviewed');
  
  const activeProjects = areaProjects.filter(p => p.status === 'active');
  if (activeProjects.length > 5) issues.push(`High load: ${activeProjects.length} active projects`);
  
  let status: AreaHealth['status'] = 'good';
  if (issues.length >= 2) status = 'critical';
  else if (issues.length === 1) status = 'warning';
  
  return { name: area.name, standard: area.standard, status, projectCount: areaProjects.length, issues };
}

function parseFrontmatter(content: string): Record<string, string> {
  const fm: Record<string, string> = {};
  const match = content.match(/^---\n([\s\S]*?)\n---/);
  if (match) {
    const lines = match[1].split('\n');
    for (const line of lines) {
      const colonIndex = line.indexOf(':');
      if (colonIndex > 0) {
        const key = line.slice(0, colonIndex).trim();
        const value = line.slice(colonIndex + 1).trim().replace(/^["']|["']$/g, '');
        fm[key] = value;
      }
    }
  }
  return fm;
}


function generateWeeklyReport(result: any): string {
  const now = new Date();
  const id = result.id;
  const weekNum = result.weekNum;
  const year = result.year;
  
  // Build related links for Areas
  const relatedLinks = result.areasHealth
    .filter((a: any) => a.status !== 'good')
    .map((a: any) => `  - "[[Area: ${a.name}]]" — ${a.issues.join(', ')}`)
    .join('\n');
  
  let report = `---
id: ${id}
title: "PARA Weekly Review — W${weekNum}"
type: moc
tags:
  - moc
  - para
  - review
  - weekly
created: ${now.toISOString().split('T')[0]}
modified: ${now.toISOString().split('T')[0]}
up: "[[MOC Index]]"
related:
  - "[[PARA Method]]" — PARA methodology overview
${relatedLinks}
---

# PARA Weekly Review — ${year}-W${weekNum}

## 📊 Overview

- **Active Projects**: ${result.active.length}
- **Simmering**: ${result.simmering.length}
- **Sleeping**: ${result.sleeping.length}
- **Completed**: ${result.done.length}
- **False Projects**: ${result.falseProjects.length}
- **Areas Need Attention**: ${result.areasHealth.filter((a: any) => a.status !== 'good').length}

`;

  if (result.active.length > 0) {
    report += `## 🚀 Active Projects

| Project | Progress | Deadline | Status |
|---------|----------|----------|--------|
`;
    for (const p of result.active) {
      report += `| ${p.name} | ${p.progress || 'N/A'} | ${p.deadline || 'N/A'} | ${p.progress >= 80 ? '🎯' : '✅'} |\n`;
    }
    report += `\n`;
  }

  if (result.falseProjects.length > 0) {
    report += `## ⚠️ False Projects\n\n`;
    for (const p of result.falseProjects) {
      report += `- **${p.name}** — ${p.issue === 'no-deadline' ? 'No deadline' : 'Stalled'}\n`;
    }
    report += `\n`;
  }

  report += `## 🌱 Areas Health

| Area | Status | Projects | Issues |
|------|--------|----------|--------|
`;
  for (const a of result.areasHealth) {
    const emoji = a.status === 'good' ? '✅' : a.status === 'warning' ? '⚠️' : '🔴';
    report += `| ${a.name} | ${emoji} | ${a.projectCount} | ${a.issues.join(', ') || 'None'} |\n`;
  }
  report += `\n## 📋 Next Actions\n\n`;
  
  let actionNum = 1;
  for (const p of result.active.filter((p: any) => p.progress >= 80)) {
    report += `${actionNum++}. [ ] Complete "${p.name}"\n`;
  }
  for (const p of result.falseProjects) {
    report += `${actionNum++}. [ ] Reclassify "${p.name}"\n`;
  }
  for (const a of result.areasHealth.filter((a: any) => a.status !== 'good')) {
    report += `${actionNum++}. [ ] Review Area: ${a.name}\n`;
  }
  
  return report;
}

function generateAreasReport(areasHealth: AreaHealth[]): string {
  const now = new Date();
  let report = `---
date: ${now.toISOString().split('T')[0]}
type: areas-check
tags:
  - review
  - areas
---

# Areas Health Check — ${now.toISOString().split('T')[0]}

## Summary

- **Healthy**: ${areasHealth.filter(a => a.status === 'good').length}
- **Warning**: ${areasHealth.filter(a => a.status === 'warning').length}
- **Critical**: ${areasHealth.filter(a => a.status === 'critical').length}

## Details

`;

  for (const area of areasHealth) {
    const emoji = area.status === 'good' ? '✅' : area.status === 'warning' ? '⚠️' : '🔴';
    report += `### ${emoji} ${area.name}\n\n`;
    if (area.standard) report += `- **Standard**: ${area.standard}\n`;
    report += `- **Active Projects**: ${area.projectCount}\n`;
    if (area.issues.length > 0) {
      report += `- **Issues**:\n`;
      for (const issue of area.issues) report += `  - ${issue}\n`;
    }
    report += `\n`;
  }
  return report;
}

function getWeekNumber(date: Date): string {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const weekNum = Math.ceil(((d.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
  return String(weekNum).padStart(2, '0');
}

function generateId(): string {
  const now = new Date();
  return now.getFullYear().toString() +
    String(now.getMonth() + 1).padStart(2, '0') +
    String(now.getDate()).padStart(2, '0') +
    String(now.getHours()).padStart(2, '0') +
    String(now.getMinutes()).padStart(2, '0');
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
}

main();
