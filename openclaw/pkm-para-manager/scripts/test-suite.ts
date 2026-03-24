#!/usr/bin/env node
/**
 * A/B/C Test Suite for pkm-para-manager
 */

import { existsSync, readFileSync } from 'fs';
import { join } from 'path';

const skillPath = process.cwd();

console.log('🧪 Running A/B/C Tests for pkm-para-manager\n');

// Test A: Structure Validation
console.log('Test A: Structure Validation');
const testA = { passed: true, issues: [], recommendations: [] };

const requiredFiles = [
  'SKILL.md',
  'CHANGELOG.md',
  'scripts/para-manager.ts',
  'references/research-notes.md'
];

for (const file of requiredFiles) {
  if (!existsSync(join(skillPath, file))) {
    testA.passed = false;
    testA.issues.push(`Missing: ${file}`);
  }
}

// Check SKILL.md frontmatter
if (existsSync(join(skillPath, 'SKILL.md'))) {
  const skillMd = readFileSync(join(skillPath, 'SKILL.md'), 'utf-8');
  if (!skillMd.match(/^---\nname: pkm-para-manager/)) {
    testA.passed = false;
    testA.issues.push('SKILL.md missing valid frontmatter');
  }
  if (!skillMd.includes('user-invocable: true')) {
    testA.issues.push('SKILL.md missing user-invocable flag');
  }
  if (!skillMd.includes('command-dispatch: tool')) {
    testA.issues.push('SKILL.md missing command-dispatch');
  }
}

if (testA.passed) {
  console.log('✅ Test A PASSED');
  testA.recommendations.push('All required files present');
  testA.recommendations.push('SKILL.md has valid frontmatter');
} else {
  console.log('❌ Test A FAILED');
  for (const issue of testA.issues) console.log(`   - ${issue}`);
}

// Test B: Trigger Accuracy
console.log('\nTest B: Trigger Accuracy');
const testB = { passed: true, issues: [], recommendations: [] };

if (existsSync(join(skillPath, 'SKILL.md'))) {
  const skillMd = readFileSync(join(skillPath, 'SKILL.md'), 'utf-8');
  
  // Check triggers
  const triggers = ['para', '/para', 'PARA', 'weekly review', 'project status'];
  for (const trigger of triggers) {
    if (!skillMd.includes(trigger)) {
      testB.issues.push(`Missing trigger: ${trigger}`);
    }
  }
  
  // Check commands documented
  const commands = ['/para review', '/para status', '/para areas', '/para false-projects'];
  for (const cmd of commands) {
    if (!skillMd.includes(cmd)) {
      testB.issues.push(`Command not documented: ${cmd}`);
    }
  }
}

if (testB.issues.length === 0) {
  console.log('✅ Test B PASSED');
  testB.recommendations.push('All triggers documented');
  testB.recommendations.push('All commands documented');
} else {
  testB.passed = false;
  console.log('❌ Test B FAILED');
  for (const issue of testB.issues) console.log(`   - ${issue}`);
}

// Test C: Coverage Analysis
console.log('\nTest C: Coverage Analysis');
const testC = { passed: true, score: 0, issues: [], recommendations: [] };

let score = 0;
const checks = [
  { name: 'Research documented', weight: 15, test: () => existsSync(join(skillPath, 'references/research-notes.md')) },
  { name: 'Implementation exists', weight: 20, test: () => existsSync(join(skillPath, 'scripts/para-manager.ts')) },
  { name: 'CHANGELOG present', weight: 10, test: () => existsSync(join(skillPath, 'CHANGELOG.md')) },
  { name: 'Agent interface documented', weight: 15, test: () => {
    const md = readFileSync(join(skillPath, 'SKILL.md'), 'utf-8');
    return md.includes('Agent Interface') || md.includes('agent-usable');
  }},
  { name: 'PARA workflow covered', weight: 20, test: () => {
    const md = readFileSync(join(skillPath, 'SKILL.md'), 'utf-8');
    return md.includes('review') && md.includes('status') && md.includes('areas');
  }},
  { name: 'Git initialized', weight: 10, test: () => existsSync(join(skillPath, '.git')) },
  { name: 'Error handling', weight: 10, test: () => {
    const code = readFileSync(join(skillPath, 'scripts/para-manager.ts'), 'utf-8');
    return code.includes('try') && code.includes('catch');
  }}
];

for (const check of checks) {
  if (check.test()) {
    score += check.weight;
    testC.recommendations.push(`${check.name}: ✓`);
  } else {
    testC.issues.push(`Missing: ${check.name}`);
  }
}

testC.score = score;
if (score >= 80) {
  console.log(`✅ Test C PASSED (${score}/100)`);
} else {
  testC.passed = false;
  console.log(`❌ Test C FAILED (${score}/100, need 80)`);
}

// Overall result
const overall = testA.passed && testB.passed && testC.passed;

console.log('\n' + '='.repeat(50));
if (overall) {
  console.log('✅ ALL TESTS PASSED');
} else {
  console.log('❌ SOME TESTS FAILED');
}
console.log('='.repeat(50));

// Write results
const results = {
  a: testA,
  b: testB,
  c: testC,
  overall
};

import { writeFileSync } from 'fs';
writeFileSync(join(skillPath, '.test-results.json'), JSON.stringify(results, null, 2));

console.log('\nResults saved to .test-results.json');
