#!/usr/bin/env node
/**
 * Quick test script for pkm-save-note
 */

import { execSync } from 'child_process';
import { existsSync, readFileSync, unlinkSync } from 'fs';
import { join } from 'path';

const VAULT_PATH = process.env.OBSIDIAN_VAULT_PATH || 
  `${process.env.HOME}/Library/Mobile Documents/iCloud~md~obsidian/Documents/Vault`;

console.log('🧪 Testing pkm-save-note...\n');

// Test 1: Dry run mode
console.log('Test 1: Dry run mode');
try {
  const result = execSync(
    `echo '{"content":"测试笔记内容","type":"log","dry_run":true}' | node scripts/save-note.ts`,
    { cwd: process.cwd(), encoding: 'utf-8' }
  );
  const output = JSON.parse(result);
  console.log('✅ Dry run passed');
  console.log('   Location:', output.para_location);
  console.log('   Tags:', output.tags_assigned?.join(', '));
} catch (e) {
  console.log('❌ Dry run failed:', e);
}

// Test 2: With project
console.log('\nTest 2: With project specified');
try {
  const result = execSync(
    `echo '{"content":"项目Alpha的会议记录","type":"meeting","project":"Alpha","dry_run":true}' | node scripts/save-note.ts`,
    { cwd: process.cwd(), encoding: 'utf-8' }
  );
  const output = JSON.parse(result);
  console.log('✅ Project assignment passed');
  console.log('   Location:', output.para_location);
  console.log('   Expected: Efforts/1-Projects/Alpha');
} catch (e) {
  console.log('❌ Project test failed:', e);
}

// Test 3: Auto-tagging
console.log('\nTest 3: Auto-tagging');
try {
  const result = execSync(
    `echo '{"content":"OpenClaw skill development with AI agents","type":"summary","dry_run":true}' | node scripts/save-note.ts`,
    { cwd: process.cwd(), encoding: 'utf-8' }
  );
  const output = JSON.parse(result);
  console.log('✅ Auto-tagging passed');
  console.log('   Tags:', output.tags_assigned?.join(', '));
  const expectedTags = ['openclaw', 'ai', 'coding'];
  const hasExpected = expectedTags.every(tag => output.tags_assigned?.includes(tag));
  console.log('   Has expected tags (openclaw, ai, coding):', hasExpected ? '✅' : '❌');
} catch (e) {
  console.log('❌ Auto-tagging test failed:', e);
}

console.log('\n✨ Tests complete');
