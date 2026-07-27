"use strict";

// Must match frontend/build.py's COMPILER_MODULES + webapi.py, and must be
// flat (no subfolder) because these modules use unqualified sibling
// imports (e.g. `from tokenizer import ...`).
const PY_FILES = [
  "tokenizer.py",
  "datatypes.py",
  "intrinsics.py",
  "ir.py",
  "astree.py",
  "parser.py",
  "ir_generator.py",
  "assembly_generator.py",
  "webapi.py",
];

const STAGES = ["tokens", "ast", "ir", "assembly"];

const EXAMPLES = [
  {
    name: "Collatz sequence",
    source:
      "var n: Int = 6;\n" +
      "print_int(n);\n" +
      "while n > 1 do {\n" +
      "    if n % 2 == 0 then {\n" +
      "        n = n / 2;\n" +
      "    } else {\n" +
      "        n = 3*n + 1;\n" +
      "    }\n" +
      "    print_int(n);\n" +
      "}\n",
  },
  {
    name: "Arithmetic precedence",
    source: "print_int(1 + 2 * 3);\nprint_int((1 + 2) * 3);\n",
  },
  {
    name: "If/else as an expression",
    source: "var x = if 3 < 5 then 1 else 2;\nprint_int(x);\n",
  },
  {
    name: "While loop",
    source: "var i = 0;\nwhile i < 3 do {\n    print_int(i);\n    i = i + 1;\n}\n",
  },
  {
    name: "read_int",
    source: "var n = read_int();\nprint_int(n + 1);\n",
  },
  {
    name: "Broken program (missing ';')",
    source: "var x = 5\nprint_int(x);\n",
  },
];

const STORAGE_KEY = "compiler-frontend-source";

const sourceEl = document.getElementById("source");
const compileBtn = document.getElementById("compile-btn");
const statusEl = document.getElementById("status");
const exampleSelect = document.getElementById("example-select");

let webapi = null;

function panelBody(stage) {
  return document.querySelector(`.panel[data-stage="${stage}"] .panel-body`);
}

function clearPanels() {
  for (const stage of STAGES) {
    panelBody(stage).innerHTML = "";
  }
}

function parseLocation(message) {
  const m = message.match(/Location\(line=(\d+), column=(\d+)\)/);
  if (!m) return null;
  return { line: parseInt(m[1], 10), column: parseInt(m[2], 10), raw: m[0] };
}

function cleanErrorMessage(message) {
  const loc = parseLocation(message);
  if (!loc) return message;
  return message.replace(loc.raw, `Line ${loc.line}, Col ${loc.column}`);
}

function jumpToLocation(line, column) {
  const lines = sourceEl.value.split("\n");
  let offset = 0;
  for (let i = 0; i < line - 1 && i < lines.length; i++) {
    offset += lines[i].length + 1;
  }
  offset += column - 1;
  sourceEl.focus();
  sourceEl.setSelectionRange(offset, offset);
}

function renderError(stage, message) {
  const el = panelBody(stage);
  const loc = parseLocation(message);
  const banner = document.createElement("div");
  banner.className = "error-banner";
  const text = document.createElement("span");
  text.textContent = cleanErrorMessage(message);
  banner.appendChild(text);
  if (loc) {
    const link = document.createElement("button");
    link.className = "error-jump";
    link.type = "button";
    link.textContent = "Jump to location";
    link.addEventListener("click", () => jumpToLocation(loc.line, loc.column));
    banner.appendChild(link);
  }
  el.appendChild(banner);
}

function renderNotReached(stage) {
  const el = panelBody(stage);
  const p = document.createElement("p");
  p.className = "not-reached";
  p.textContent = "Not reached — fix the error above first.";
  el.appendChild(p);
}

function renderTokens(tokens) {
  const el = panelBody("tokens");
  const table = document.createElement("table");
  table.innerHTML = "<thead><tr><th>text</th><th>type</th><th>line:col</th></tr></thead>";
  const tbody = document.createElement("tbody");
  for (const t of tokens) {
    const tr = document.createElement("tr");
    tr.innerHTML =
      `<td class="mono">${escapeHtml(t.text)}</td>` +
      `<td>${escapeHtml(t.type)}</td>` +
      `<td>${t.location.line}:${t.location.column}</td>`;
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  el.appendChild(table);
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

function astNodeLabel(node) {
  const skip = new Set(["node", "location", "type"]);
  const scalarParts = [];
  for (const [key, value] of Object.entries(node)) {
    if (skip.has(key)) continue;
    if (value === null || typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
      scalarParts.push(`${key}=${value}`);
    }
  }
  let label = node.node;
  if (scalarParts.length) label += ` (${scalarParts.join(", ")})`;
  if (node.type !== undefined) label += ` : ${node.type}`;
  return label;
}

function renderAstNode(node) {
  if (node === null || typeof node !== "object" || Array.isArray(node) || !node.node) {
    const span = document.createElement("span");
    span.className = "ast-scalar";
    span.textContent = JSON.stringify(node);
    return span;
  }

  const details = document.createElement("details");
  details.open = true;
  const summary = document.createElement("summary");
  summary.textContent = astNodeLabel(node);
  summary.title = `line ${node.location.line}, col ${node.location.column}`;
  details.appendChild(summary);

  const skip = new Set(["node", "location", "type"]);
  for (const [key, value] of Object.entries(node)) {
    if (skip.has(key)) continue;
    if (value === null || typeof value !== "object") continue;

    const field = document.createElement("div");
    field.className = "ast-field";
    const fieldLabel = document.createElement("span");
    fieldLabel.className = "ast-field-label";
    fieldLabel.textContent = key + ":";
    field.appendChild(fieldLabel);

    if (Array.isArray(value)) {
      if (value.length === 0) {
        const empty = document.createElement("span");
        empty.className = "ast-scalar";
        empty.textContent = "[]";
        field.appendChild(empty);
      } else {
        for (const item of value) field.appendChild(renderAstNode(item));
      }
    } else {
      field.appendChild(renderAstNode(value));
    }
    details.appendChild(field);
  }
  return details;
}

function renderAst(tree) {
  panelBody("ast").appendChild(renderAstNode(tree));
}

function renderIr(lines) {
  const el = panelBody("ir");
  const pre = document.createElement("pre");
  pre.textContent = lines.join("\n");
  el.appendChild(pre);
}

function renderAssembly(text) {
  const el = panelBody("assembly");
  const pre = document.createElement("pre");
  for (const line of text.split("\n")) {
    const div = document.createElement("div");
    div.textContent = line;
    if (line.trim().startsWith("#")) div.className = "asm-comment";
    pre.appendChild(div);
  }
  el.appendChild(pre);
}

function renderResult(result) {
  clearPanels();
  const stages = result.stages;
  let reached = true;
  for (const stage of STAGES) {
    if (!reached) {
      renderNotReached(stage);
      continue;
    }
    const s = stages[stage];
    if (!s) {
      renderNotReached(stage);
      continue;
    }
    if (!s.ok) {
      renderError(stage, s.error);
      reached = false;
      continue;
    }
    if (stage === "tokens") renderTokens(s.data);
    else if (stage === "ast") renderAst(s.data);
    else if (stage === "ir") renderIr(s.data);
    else if (stage === "assembly") renderAssembly(s.data);
  }
}

function compile() {
  if (!webapi) return;
  const source = sourceEl.value;
  localStorage.setItem(STORAGE_KEY, source);
  const resultJson = webapi.compile_all(source);
  const result = JSON.parse(resultJson);
  renderResult(result);
}

function populateExamples() {
  for (const ex of EXAMPLES) {
    const opt = document.createElement("option");
    opt.textContent = ex.name;
    opt.value = ex.name;
    exampleSelect.appendChild(opt);
  }
  exampleSelect.addEventListener("change", () => {
    const ex = EXAMPLES.find((e) => e.name === exampleSelect.value);
    if (ex) {
      sourceEl.value = ex.source;
      compile();
    }
  });
}

function initTabs() {
  const panels = document.querySelector(".panels");
  const tabs = document.querySelectorAll(".tab");
  for (const tab of tabs) {
    tab.addEventListener("click", () => {
      panels.dataset.activeStage = tab.dataset.stage;
      for (const t of tabs) t.classList.toggle("active", t === tab);
    });
  }
  document.querySelector('.tab[data-stage="tokens"]').classList.add("active");
}

async function init() {
  populateExamples();
  initTabs();

  const saved = localStorage.getItem(STORAGE_KEY);
  sourceEl.value = saved || EXAMPLES[0].source;

  sourceEl.addEventListener("keydown", (e) => {
    if (e.key === "Tab") {
      e.preventDefault();
      const start = sourceEl.selectionStart;
      const end = sourceEl.selectionEnd;
      sourceEl.value = sourceEl.value.slice(0, start) + "    " + sourceEl.value.slice(end);
      sourceEl.setSelectionRange(start + 4, start + 4);
    } else if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      compile();
    }
  });
  compileBtn.addEventListener("click", compile);

  statusEl.textContent = "Loading Python runtime…";
  const pyodide = await loadPyodide();

  statusEl.textContent = "Loading compiler modules…";
  pyodide.FS.mkdirTree("/py");
  for (const name of PY_FILES) {
    const resp = await fetch(`py/${name}`);
    const text = await resp.text();
    pyodide.FS.writeFile(`/py/${name}`, text);
  }
  pyodide.runPython("import sys\nsys.path.insert(0, '/py')");
  webapi = pyodide.pyimport("webapi");

  statusEl.textContent = "Ready";
  compileBtn.disabled = false;
  compile();
}

init().catch((err) => {
  console.error(err);
  statusEl.textContent = "Failed to load Python runtime — see console.";
});
