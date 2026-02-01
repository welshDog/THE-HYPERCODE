#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

function gzipSizeSync(content) {
  return zlib.gzipSync(content).length;
}

function walk(dir) {
  const files = [];
  for (const entry of fs.readdirSync(dir)) {
    const p = path.join(dir, entry);
    const stat = fs.statSync(p);
    if (stat.isDirectory()) files.push(...walk(p));
    else files.push(p);
  }
  return files;
}

function manifest(dir) {
  const files = walk(dir);
  const items = files.map(f => {
    const buf = fs.readFileSync(f);
    return { file: path.relative(dir, f).replace(/\\/g, '/'), gzipBytes: gzipSizeSync(buf) };
  });
  return { generatedAt: Date.now(), items };
}

function diff(prev, curr) {
  const prevMap = new Map(prev.items.map(i => [i.file, i.gzipBytes]));
  const rows = curr.items.map(i => {
    const old = prevMap.get(i.file) || 0;
    const delta = i.gzipBytes - old;
    const pct = old > 0 ? ((i.gzipBytes - old) / old) * 100 : 100;
    return { file: i.file, old, now: i.gzipBytes, delta, pct };
  });
  return rows;
}

function htmlReport(rows) {
  const lines = [];
  lines.push('<!doctype html><meta charset="utf-8"><title>Bundle Diff</title>');
  lines.push('<style>table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:6px} .up{color:#b00} .down{color:#0b0}</style>');
  lines.push('<table><tr><th>File</th><th>Prev</th><th>Now</th><th>Delta</th><th>%</th></tr>');
  for (const r of rows) {
    const cls = r.delta > 0 ? 'up' : 'down';
    lines.push(`<tr><td>${r.file}</td><td>${r.old}</td><td>${r.now}</td><td class="${cls}">${r.delta}</td><td class="${cls}">${r.pct.toFixed(2)}%</td></tr>`);
  }
  lines.push('</table>');
  return lines.join('\n');
}

function main() {
  const dist = process.env.DIST_DIR || 'hyperflow-editor/dist';
  const prevPath = process.env.PREV_MANIFEST || '';
  const outDir = process.env.OUT_DIR || '.';
  const allowOverride = /bundle-override/i.test(process.env.COMMIT_MSG || '');

  const curr = manifest(dist);
  const currPath = path.join(outDir, 'bundle-manifest.json');
  fs.writeFileSync(currPath, JSON.stringify(curr));

  let prev = { items: [] };
  if (prevPath && fs.existsSync(prevPath)) prev = JSON.parse(fs.readFileSync(prevPath, 'utf-8'));
  const rows = diff(prev, curr);
  const html = htmlReport(rows);
  const htmlPath = path.join(outDir, 'bundle-diff.html');
  fs.writeFileSync(htmlPath, html);
  const jsonPath = path.join(outDir, 'bundle-diff.json');
  fs.writeFileSync(jsonPath, JSON.stringify(rows));

  const violations = rows.filter(r => r.pct > 10);
  if (violations.length && !allowOverride) {
    console.log('Bundle growth violations:');
    for (const v of violations) console.log(`${v.file} +${v.pct.toFixed(2)}%`);
    process.exit(1);
  }
}

main();
