#!/usr/bin/env node
/**
 * problems.json 전체를 renderContent(index.html)와 동일 규칙으로 분석해
 * 파이프 표로 잡히는 줄이 본문을 깨뜨릴 가능성이 있는 항목을 나열합니다.
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, '..');
const problems = JSON.parse(fs.readFileSync(path.join(root, 'problems.json'), 'utf8'));

function preprocess(text) {
  if (!text) return '';
  let t = text.replace(/([가-힣a-zA-Z0-9])\n([가-힣a-zA-Z0-9(])/g, '$1$2');
  t = t.replace(/([가-힣])\.\n([가-힣])/g, '$1$2');
  return t;
}

function extractTables(text) {
  const lines = preprocess(text).split('\n');
  const tables = [];
  let currentRows = [];
  let prevNonPipeLine = null;

  for (const line of lines) {
    const t = line.trim();
    if (t.startsWith('|') && t.endsWith('|')) {
      currentRows.push(t.split('|').slice(1, -1).map((c) => c.trim()));
    } else {
      if (currentRows.length) {
        tables.push({ rows: currentRows, prevLine: prevNonPipeLine });
        currentRows = [];
      }
      if (t) prevNonPipeLine = t;
    }
  }
  if (currentRows.length) tables.push({ rows: currentRows, prevLine: prevNonPipeLine });

  return tables;
}

/** 의심: 짧은 조각 셀만 모인 행 (문장이 표로 쪼개진 경우) */
function suspiciousRow(cells) {
  const filtered = cells.filter((c) => c !== '<' && c !== '>');
  if (filtered.length < 4) return false;
  const short = filtered.filter((c) => c.length <= 3);
  const punctOnly = filtered.filter((c) => /^[).,·\s]+$|^[㉠-㉿]$|^[①-⑳]$/.test(c));
  if (punctOnly.length >= 2 && short.length >= filtered.length * 0.4) return 'fragment-cells';
  if (filtered.some((c) => c === '로 쓰시오' || c === ')' || (c === '.' && filtered.indexOf(c) === filtered.length - 1)))
    if (filtered.length >= 4) return 'scaffold-phrase';
  return false;
}

/** 표 첫 행이 보기/데이터가 아니라 문장 조각으로만 채워진 경우 */
function analyzeTable(rows) {
  const issues = [];
  rows.forEach((row, i) => {
    const cells = row.filter((c) => c !== '<' && c !== '>');
    const s = suspiciousRow(row);
    if (s) issues.push({ row: i + 1, kind: s, sample: cells.slice(0, 12).join(' | ') });
  });
  return issues;
}

const field = process.argv[2] || 'both'; // question | answer | both

const report = [];

for (const p of problems) {
  const parts = [];
  if (field === 'question' || field === 'both') parts.push(['question', p.question]);
  if (field === 'answer' || field === 'both') parts.push(['answer', p.answer]);

  for (const [fname, text] of parts) {
    if (!text) continue;
    const tables = extractTables(text);
    let ti = 0;
    for (const { rows } of tables) {
      ti++;
      const issues = analyzeTable(rows);
      if (issues.length) {
        report.push({
          id: p.id,
          field: fname,
          tableIndex: ti,
          rowCount: rows.length,
          issues,
        });
      }
    }
  }
}

report.sort((a, b) => a.id - b.id || String(a.field).localeCompare(b.field));

console.log(`스캔: ${problems.length}문제, 필드: ${field}`);
console.log(`의심 표 블록 수: ${report.length}\n`);

let cur = null;
for (const r of report) {
  if (cur !== r.id) {
    cur = r.id;
    console.log(`--- 문제 ${r.id} ---`);
  }
  console.log(`  [${r.field}] 표#${r.tableIndex} (${r.rowCount}행)`);
  for (const iss of r.issues) {
    console.log(`    행${iss.row} (${iss.kind}): ${iss.sample}`);
  }
}

if (!report.length) console.log('(의심 패턴 없음)');
