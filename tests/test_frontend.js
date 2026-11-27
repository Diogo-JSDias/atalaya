const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const template = fs.readFileSync("templates/index.html", "utf8");

// Test the exact helper used by both subgroup enumeration and card selection.
const helper = template.match(/const subfieldFor = o => o\.subfield \|\| "Geral";/);
assert.ok(helper, "template must define one shared fallback for empty subfields");
assert.ok(template.includes("inField.map(subfieldFor)"),
  "subgroup enumeration must use the shared fallback");
assert.ok(template.includes("subfieldFor(o) === s"),
  "subgroup filtering must use the same shared fallback");

const result = vm.runInNewContext(
  `${helper[0]}; JSON.stringify([
    subfieldFor({ subfield: "Biologia" }),
    subfieldFor({ subfield: "" }),
    subfieldFor({ subfield: null }),
    subfieldFor({})
  ])`
);
assert.equal(result, JSON.stringify(["Biologia", "Geral", "Geral", "Geral"]));

// Extract the main <script> block from templates/index.html for vm-based unit tests.
const scriptMatch = template.match(/<script>\s*([\s\S]*?)<\/script>\s*<\/body>/);
assert.ok(scriptMatch, "template must contain the main inline <script>");
const scriptBody = scriptMatch[1];

// 1. parseLocalDate / days(iso) timezone-safe calendar comparison
const parseLocalDateMatch = scriptBody.match(/const parseLocalDate = iso => \{[\s\S]*?\};/);
const daysMatch = scriptBody.match(/const days = iso => .*?;/);
assert.ok(parseLocalDateMatch && daysMatch, "template must define parseLocalDate and days");

const dateResults = vm.runInNewContext(`
  const TODAY = "2026-03-29";
  ${parseLocalDateMatch[0]}
  ${daysMatch[0]}
  const d = parseLocalDate("2026-03-29");
  JSON.stringify({
    year: d.getFullYear(),
    month: d.getMonth() + 1,
    day: d.getDate(),
    hours: d.getHours(),
    sameDay: days("2026-03-29"),
    nextDay: days("2026-03-30"),
    prevDay: days("2026-03-28"),
    twoWeeks: days("2026-04-12")
  });
`);
assert.equal(
  dateResults,
  JSON.stringify({
    year: 2026,
    month: 3,
    day: 29,
    hours: 0,
    sameDay: 0,
    nextDay: 1,
    prevDay: -1,
    twoWeeks: 14
  })
);

// 2. PT-PT pluralization in #stats
const statsMatch = scriptBody.match(/\$\("stats"\)\.innerHTML = (\[[\s\S]*?\]\.map\([\s\S]*?\)\.join\(""\));/);
assert.ok(statsMatch, "template must render #stats pluralization");

const pluralize = (n, s, p) =>
  vm.runInNewContext(`(([n, s, p]) => \`<div class="stat"><b>\${n}</b><span>\${n === 1 ? s : p}</span></div>\`)(${JSON.stringify([n, s, p])})`);

assert.ok(statsMatch[1].includes("n === 1 ? s : p"), "#stats must use n === 1 for singular");
assert.equal(pluralize(1, "vaga aberta", "vagas abertas"), '<div class="stat"><b>1</b><span>vaga aberta</span></div>');
assert.equal(pluralize(0, "vaga aberta", "vagas abertas"), '<div class="stat"><b>0</b><span>vagas abertas</span></div>');
assert.equal(pluralize(2, "concurso", "concursos"), '<div class="stat"><b>2</b><span>concursos</span></div>');
assert.equal(pluralize(1, "instituição", "instituições"), '<div class="stat"><b>1</b><span>instituição</span></div>');
assert.equal(pluralize(3, "instituição", "instituições"), '<div class="stat"><b>3</b><span>instituições</span></div>');
assert.equal(pluralize(1, "termina em 14 dias", "terminam em 14 dias"), '<div class="stat"><b>1</b><span>termina em 14 dias</span></div>');
assert.equal(pluralize(5, "termina em 14 dias", "terminam em 14 dias"), '<div class="stat"><b>5</b><span>terminam em 14 dias</span></div>');

// 3. Search matching translated fieldLabel / stageLabel terms
const fieldLabelMap = scriptBody.match(/const FIELD_LABEL = \{.*?\};/);
const stageLabelMap = scriptBody.match(/const STAGE_LABEL = \{.*?\};/);
const fieldLabelFn = scriptBody.match(/const fieldLabel = .*?;/);
const stageLabelFn = scriptBody.match(/const stageLabel = .*?;/);
const matchesFn = scriptBody.match(/function matches\(o, ignoreField\) \{[\s\S]*?\n\}/);
assert.ok(fieldLabelMap && stageLabelMap && fieldLabelFn && stageLabelFn && matchesFn,
  "template must define label maps, helpers, and matches()");

const searchResults = vm.runInNewContext(`
  const TODAY = "2026-04-01";
  ${parseLocalDateMatch[0]}
  ${daysMatch[0]}
  ${fieldLabelMap[0]}
  ${stageLabelMap[0]}
  ${fieldLabelFn[0]}
  ${stageLabelFn[0]}
  const state = { field: "", kind: "", stage: "", subfield: "", region: "", inst: "", q: "", soon: false, fresh: false };
  ${matchesFn[0]}
  const offer = {
    title: "Bolsa de Investigação",
    area_raw: "Física",
    institution: "IST",
    field: "Physical Sciences & Engineering",
    subfield: "Física",
    stage: "Postdoc",
    region: "Lisboa",
    notes: "",
    position_type: "",
    first_seen: "2026-04-01"
  };
  state.q = "ciências físicas engenharia";
  const byFieldPt = matches(offer, false);
  state.q = "pós-doutoramento";
  const byStagePt = matches(offer, false);
  state.q = "humanidades";
  const byOtherFieldPt = matches(offer, false);
  JSON.stringify({ byFieldPt, byStagePt, byOtherFieldPt });
`);
assert.equal(
  searchResults,
  JSON.stringify({ byFieldPt: true, byStagePt: true, byOtherFieldPt: false })
);

console.log("Frontend tests passed.");
