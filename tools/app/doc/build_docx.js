// build_docx.js - render the essay (doc/essay.docx.json + doc/fig/*.svg) to Word.
//   node build_docx.js OUT.docx
// Same source as the app's Doc tab (tools/app/doc/essay.py); figures are the same SVGs, rasterised.
// Written by Claude (Anthropic); see AI-USE.md.
const fs = require('fs');
const path = require('path');
const sharp = require('sharp');
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, ImageRun, Table, TableRow, TableCell,
  WidthType, ShadingType, AlignmentType, LevelFormat, BorderStyle, Footer, PageNumber,
} = require('docx');

const HERE = __dirname;
const blocks = JSON.parse(fs.readFileSync(path.join(HERE, 'essay.docx.json'), 'utf8'));
const OUT = process.argv[2] || path.join(HERE, 'six-engines.docx');
const TITLE = (blocks.find(b => b[0] === 'h1') || [null, 'Six Engines, One Answer'])[1];
const BODY = 'Georgia', HEAD = 'Arial', MONO = 'Consolas';
const TEXT_W = 9360; // 6.5 in in DXA

function runs(text, base = {}) {
  // **bold**, *italic*, `code`
  const out = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const t = m[0];
    if (t.startsWith('**')) out.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }));
    else if (t.startsWith('`')) out.push(new TextRun({ text: t.slice(1, -1), font: MONO, size: 19, ...base }));
    else out.push(new TextRun({ text: t.slice(1, -1), italics: true, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), ...base }));
  return out;
}

async function figure(name, caption) {
  const svg = fs.readFileSync(path.join(HERE, 'fig', name + '.svg'));
  const meta = await sharp(svg, { density: 192 }).metadata();
  const png = await sharp(svg, { density: 192 }).png().toBuffer();
  const w = 624, h = Math.round(624 * meta.height / meta.width);
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 160, after: 60 },
      children: [new ImageRun({ type: 'png', data: png, transformation: { width: w, height: h },
        altText: { title: name, description: caption, name } })] }),
    new Paragraph({ spacing: { after: 220 }, children: runs(caption, { font: HEAD, size: 18, color: '4F5D6E' }) }),
  ];
}

function table(header, rows) {
  const n = header.length;
  const widths = n === 4 ? [700, 1700, 3300, 3660] : n === 3 ? [4560, 1600, 3200] : Array(n).fill(Math.floor(TEXT_W / n));
  if (n === 4 && header[0] !== '#') widths.splice(0, 4, 2600, 2260, 2250, 2250);
  const border = { style: BorderStyle.SINGLE, size: 4, color: 'CFD8E3' };
  const borders = { top: border, bottom: border, left: border, right: border };
  const cell = (t, i, head) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA }, borders,
    shading: head ? { fill: 'EEF3F8', type: ShadingType.CLEAR, color: 'auto' } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: runs(String(t), { font: (!head && header[0] === '#' && i === 2) ? MONO : HEAD, size: head ? 18 : 17, bold: head }) })],
  });
  return new Table({
    width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: header.map((h, i) => cell(h, i, true)) }),
      ...rows.map(r => new TableRow({ children: r.map((c, i) => cell(c, i, false)) }))],
  });
}

(async () => {
  const children = [];
  for (const b of blocks) {
    const k = b[0];
    if (k === 'h1') children.push(new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun({ text: b[1], font: HEAD, bold: true, size: 48 })] }));
    else if (k === 'sub') children.push(new Paragraph({ spacing: { after: 280 }, children: runs(b[1], { font: HEAD, size: 24, color: '4F5D6E' }) }));
    else if (k === 'h2') children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, keepNext: true, keepLines: true, spacing: { before: 320, after: 120 },
      children: [new TextRun({ text: b[2], font: HEAD, bold: true, size: 30, color: '1E3A5F' })] }));
    else if (k === 'p') children.push(new Paragraph({ spacing: { after: 160, line: 300 }, children: runs(b[1], { font: BODY, size: 22 }) }));
    else if (k === 'code') children.push(new Paragraph({ spacing: { before: 80, after: 160 },
      shading: { fill: 'EEF3F8', type: ShadingType.CLEAR, color: 'auto' },
      children: [new TextRun({ text: b[1], font: MONO, size: 18 })] }));
    else if (k === 'ul') for (const it of b[1]) children.push(new Paragraph({ numbering: { reference: 'bullets', level: 0 },
      spacing: { after: 80, line: 290 }, children: runs(it, { font: BODY, size: 22 }) }));
    else if (k === 'table') { children.push(table(b[1], b[2])); children.push(new Paragraph({ spacing: { after: 160 }, children: [] })); }
    else if (k === 'fig') children.push(...await figure(b[1], b[2]));
  }
  const doc = new Document({
    creator: 'Robert Dickinson', title: TITLE,
    description: 'EPA SWMM 5.2.4 carried into Fortran, C# and Python, byte-identical; written with Claude (Anthropic), see Use of AI',
    styles: { default: { document: { run: { font: BODY, size: 22 } } } },
    numbering: { config: [{ reference: 'bullets', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•',
      alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
    sections: [{
      properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
      footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
        children: [new TextRun({ children: [TITLE + '  ·  ', PageNumber.CURRENT], font: HEAD, size: 16, color: '5F6B7A' })] })] }) },
      children,
    }],
  });
  fs.writeFileSync(OUT, await Packer.toBuffer(doc));
  console.log('wrote', OUT);
})();
