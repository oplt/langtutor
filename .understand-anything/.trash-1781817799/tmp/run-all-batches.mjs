#!/usr/bin/env node
/**
 * Deterministic batch graph builder for /understand Phase 2.
 * Runs extract-structure.mjs per batch and emits batch-<N>.json files.
 */
import { spawnSync } from 'node:child_process';
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, join, basename } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = '/home/polat/Desktop/Projects/LanguageApp';
const SKILL_DIR = '/home/polat/.agents/skills/understand';
const INTER = join(PROJECT_ROOT, '.understand-anything/intermediate');
const TMP = join(PROJECT_ROOT, '.understand-anything/tmp');

const batches = JSON.parse(readFileSync(join(INTER, 'batches.json'), 'utf8'));

function nodeTypeForCategory(cat, path) {
  if (cat === 'config') return 'config';
  if (cat === 'docs') return 'document';
  if (cat === 'infra') return 'service';
  if (cat === 'data') return 'schema';
  if (cat === 'script') return 'file';
  if (cat === 'markup') return 'file';
  return 'file';
}

function prefixForType(type) {
  const map = {
    file: 'file',
    config: 'config',
    document: 'document',
    service: 'service',
    schema: 'schema',
    function: 'function',
    class: 'class',
  };
  return map[type] || 'file';
}

function complexityFromLines(lines) {
  if (lines <= 80) return 'simple';
  if (lines <= 250) return 'moderate';
  return 'complex';
}

function tagsForFile(f, exportsList) {
  const tags = new Set();
  const p = f.path.toLowerCase();
  if (p.includes('test') || p.includes('spec')) tags.add('test');
  if (p.endsWith('main.py') || p.endsWith('main.ts') || p.endsWith('app.tsx')) tags.add('entry-point');
  if (p.includes('/api/') || p.includes('_api.')) tags.add('api-handler');
  if (p.includes('/models/') || p.includes('models.py')) tags.add('data-model');
  if (p.includes('/service') || p.endsWith('service.py')) tags.add('service');
  if (p.includes('/components/')) tags.add('component');
  if (p.includes('/hooks/')) tags.add('hook');
  if (p.includes('dockerfile')) tags.add('infrastructure');
  if (p.endsWith('readme.md')) tags.add('documentation');
  if (f.fileCategory === 'config') tags.add('configuration');
  if (f.fileCategory === 'docs') tags.add('documentation');
  if (exportsList?.length) tags.add('module');
  if (!tags.size) tags.add('module');
  return [...tags].slice(0, 5);
}

function summaryForFile(f, result, exportsList) {
  const fn = result?.functions?.length ?? 0;
  const cl = result?.classes?.length ?? 0;
  const parts = [`${f.fileCategory} file`, `${f.language}`];
  if (fn) parts.push(`${fn} function(s)`);
  if (cl) parts.push(`${cl} class(es)`);
  if (exportsList?.length) parts.push(`exports: ${exportsList.slice(0, 4).join(', ')}`);
  return parts.join('; ') + '.';
}

function isTestPath(p) {
  return /(^|\/)tests?\//.test(p) || /test_/.test(basename(p)) || /\.(test|spec)\./.test(p);
}

function productionTargetForTest(testPath) {
  const base = basename(testPath).replace(/^test_/, '').replace(/\.(py|ts|tsx)$/, '');
  if (testPath.includes('backend/tests/')) {
    const mod = base.replace(/^test_/, '');
    return `backend/app/${mod.replace(/_/g, '/')}.py`;
  }
  return null;
}

for (const batch of batches.batches) {
  const idx = batch.batchIndex;
  const inputPath = join(TMP, `ua-file-analyzer-input-${idx}.json`);
  const extractPath = join(TMP, `ua-file-extract-results-${idx}.json`);
  const outputPath = join(INTER, `batch-${idx}.json`);

  writeFileSync(
    inputPath,
    JSON.stringify(
      {
        projectRoot: PROJECT_ROOT,
        batchFiles: batch.files,
        batchImportData: batch.batchImportData,
      },
      null,
      2,
    ),
  );

  const proc = spawnSync(
    'node',
    [join(SKILL_DIR, 'extract-structure.mjs'), inputPath, extractPath],
    { encoding: 'utf8' },
  );
  if (proc.status !== 0) {
    console.error(`batch ${idx} extract failed:`, proc.stderr);
    continue;
  }

  const extracted = JSON.parse(readFileSync(extractPath, 'utf8'));
  const byPath = new Map((extracted.results || []).map((r) => [r.path, r]));

  const nodes = [];
  const edges = [];

  for (const f of batch.files) {
    const result = byPath.get(f.path);
    const exportsList = batches.exportsByPath?.[f.path] || [];
    const type = nodeTypeForCategory(f.fileCategory, f.path);
    const prefix = prefixForType(type);
    const nodeId = `${prefix}:${f.path}`;

    nodes.push({
      id: nodeId,
      type,
      name: basename(f.path),
      filePath: f.path,
      summary: summaryForFile(f, result, exportsList),
      tags: tagsForFile(f, exportsList),
      complexity: complexityFromLines(f.sizeLines || result?.totalLines || 0),
    });

    const imports = batch.batchImportData?.[f.path] || [];
    for (const imp of imports) {
      const impCat = batch.files.find((x) => x.path === imp)?.fileCategory;
      let targetPrefix = 'file';
      if (impCat === 'config') targetPrefix = 'config';
      else if (impCat === 'docs') targetPrefix = 'document';
      else if (impCat === 'infra') targetPrefix = 'service';
      else if (impCat === 'data') targetPrefix = 'schema';
      edges.push({
        source: nodeId,
        target: `${targetPrefix}:${imp}`,
        type: 'imports',
        direction: 'forward',
        weight: 0.7,
      });
    }

    if (isTestPath(f.path)) {
      const prod = productionTargetForTest(f.path);
      if (prod) {
        edges.push({
          source: `file:${prod}`,
          target: nodeId,
          type: 'tested_by',
          direction: 'forward',
          weight: 0.5,
        });
      }
    }

    if (f.fileCategory !== 'code' || !result) continue;

    for (const fn of result.functions || []) {
      const lines = (fn.endLine || 0) - (fn.startLine || 0) + 1;
      const exported = exportsList.includes(fn.name);
      if (lines < 10 && !exported) continue;
      const fnId = `function:${f.path}:${fn.name}`;
      nodes.push({
        id: fnId,
        type: 'function',
        name: fn.name,
        filePath: f.path,
        summary: `Function ${fn.name} in ${f.path}.`,
        tags: ['module'],
        complexity: complexityFromLines(lines),
      });
      edges.push({ source: nodeId, target: fnId, type: 'contains', direction: 'forward', weight: 1.0 });
      if (exported) {
        edges.push({ source: nodeId, target: fnId, type: 'exports', direction: 'forward', weight: 0.8 });
      }
    }

    for (const cl of result.classes || []) {
      const lines = (cl.endLine || 0) - (cl.startLine || 0) + 1;
      const methods = cl.methods?.length || 0;
      const exported = exportsList.includes(cl.name);
      if (lines < 20 && methods < 2 && !exported) continue;
      const clId = `class:${f.path}:${cl.name}`;
      nodes.push({
        id: clId,
        type: 'class',
        name: cl.name,
        filePath: f.path,
        summary: `Class ${cl.name} in ${f.path}.`,
        tags: ['data-model', 'module'],
        complexity: complexityFromLines(lines),
      });
      edges.push({ source: nodeId, target: clId, type: 'contains', direction: 'forward', weight: 1.0 });
      if (exported) {
        edges.push({ source: nodeId, target: clId, type: 'exports', direction: 'forward', weight: 0.8 });
      }
    }
  }

  // README documents entry points
  for (const f of batch.files) {
    if (f.path.toLowerCase().endsWith('readme.md')) {
      edges.push({
        source: `document:${f.path}`,
        target: 'file:backend/app/main.py',
        type: 'documents',
        direction: 'forward',
        weight: 0.5,
      });
      edges.push({
        source: `document:${f.path}`,
        target: 'file:frontend/src/main.tsx',
        type: 'documents',
        direction: 'forward',
        weight: 0.5,
      });
    }
    if (f.path.toLowerCase().includes('dockerfile')) {
      edges.push({
        source: `service:${f.path}`,
        target: 'file:backend/app/main.py',
        type: 'deploys',
        direction: 'forward',
        weight: 0.7,
      });
    }
  }

  writeFileSync(outputPath, JSON.stringify({ nodes, edges }, null, 2));
  console.log(`batch-${idx}.json: ${nodes.length} nodes, ${edges.length} edges`);
}
