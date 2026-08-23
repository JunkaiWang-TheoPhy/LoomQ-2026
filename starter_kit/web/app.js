const examples = {
  bell: `OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
measure q -> c;`,
  ghz: `OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
cx q[0],q[1];
cx q[0],q[2];
measure q -> c;`,
  uniform: `OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
h q[1];
h q[2];
measure q -> c;`,
};

const taskPrompts = {
  repair: "修复下面的 OpenQASM 2.0，使它生成 Bell 态并测量；只使用白名单门，并解释修改：\nOPENQASM 2.0; qreg q[2]; h q[0]; cx q[0],q[2];",
  backend: "我需要运行一个 3 比特 GHZ 电路。请比较 SpinQ、本源 OriginQ 与 Braket 的适用性，给出推荐后端、限制和可运行的 OpenQASM 2.0。",
};

const $ = (selector) => document.querySelector(selector);
const qasm = $("#qasm");
const notice = $("#notice");

function tell(message) {
  notice.textContent = message;
  notice.classList.add("show");
  clearTimeout(tell.timer);
  tell.timer = setTimeout(() => notice.classList.remove("show"), 4200);
}

function element(tag, className, value) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (value !== undefined) node.textContent = value;
  return node;
}

function renderCircuit() {
  const source = qasm.value;
  const count = Number((source.match(/qreg\s+\w+\[(\d+)\]/) || [])[1] || 0);
  const gates = Array.from({ length: count }, () => []);
  for (const line of source.split("\n")) {
    const match = line.trim().match(/^(h|x|s|sdg|t|tdg|rz|ry|cx|cu1|swap|ccx)\b[^;]*?((?:q\[\d+\][^;]*)+);/);
    if (!match) continue;
    const used = [...match[2].matchAll(/q\[(\d+)\]/g)].map((item) => Number(item[1]));
    used.forEach((index) => gates[index]?.push(match[1].toUpperCase()));
  }
  const circuit = $("#circuit");
  circuit.replaceChildren();
  if (!gates.length) {
    circuit.append(element("div", "wire", "输入 qreg 后显示电路"));
    return;
  }
  gates.forEach((items, index) => {
    const wire = element("div", "wire");
    wire.append(element("span", "wire-label", `q[${index}]`), element("span", "wire-line"));
    items.forEach((gate) => wire.append(element("b", "gate", gate)));
    circuit.append(wire);
  });
}

function selectExample(name) {
  qasm.value = examples[name];
  document.querySelectorAll(".chip").forEach((button) => {
    button.classList.toggle("active", button.dataset.example === name);
  });
  renderCircuit();
}

document.querySelectorAll(".chip").forEach((button) => {
  button.addEventListener("click", () => selectExample(button.dataset.example));
});
qasm.addEventListener("input", renderCircuit);
selectExample("bell");

document.querySelectorAll(".task-card").forEach((button) => {
  button.addEventListener("click", () => {
    const task = button.dataset.task;
    document.querySelectorAll(".task-card").forEach((card) => card.classList.toggle("active", card === button));
    if (task === "learn") {
      selectExample("bell");
      $("#lesson").focus();
      return;
    }
    if (task === "build") {
      $("#workspace").focus();
      return;
    }
    $("#prompt").value = taskPrompts[task];
    $("#prompt").focus();
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    $("#agent-title").scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "center" });
  });
});

async function api(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error?.message || "请求失败");
  return data;
}

function renderResults(data) {
  $("#empty").hidden = true;
  const results = $("#results");
  results.hidden = false;
  $("#backend").textContent = data.result.backend;
  const entries = Object.entries(data.probabilities).sort((a, b) => b[1] - a[1]);
  const chart = $("#chart");
  const rows = $("#result-rows");
  chart.replaceChildren();
  rows.replaceChildren();
  entries.forEach(([state, probability]) => {
    const barRow = element("div", "bar-row");
    const progress = element("progress", "bar-track", `${(probability * 100).toFixed(1)}%`);
    progress.max = 1;
    progress.value = probability;
    progress.setAttribute("aria-label", `状态 ${state} 的概率`);
    barRow.append(
      element("strong", "", `|${state}⟩`),
      progress,
      element("span", "", `${(probability * 100).toFixed(1)}%`),
    );
    chart.append(barRow);

    const row = document.createElement("tr");
    const count = data.result.counts[state] || 0;
    [`|${state}⟩`, String(count), `${(probability * 100).toFixed(2)}%`].forEach((value) => {
      row.append(element("td", "", value));
    });
    rows.append(row);
  });
  const leaders = entries.slice(0, 2).map(([state]) => `|${state}⟩`).join(" 与 ");
  $("#explanation").textContent = `共测量 ${data.result.shots} 次。主导结果为 ${leaders}；位串从左到右对应高位到低位。`;
  $("#native").textContent = data.native_ir;
  results.setAttribute("tabindex", "-1");
  results.focus();
}

$("#run").addEventListener("click", async () => {
  const button = $("#run");
  button.disabled = true;
  button.textContent = "正在编织…";
  try {
    const data = await api("/api/run", {
      qasm: qasm.value,
      target: $("#target").value,
      shots: Number($("#shots").value),
    });
    renderResults(data);
    tell("运行完成：结果已通过统一 Schema 输出");
  } catch (error) {
    tell(error.message);
  } finally {
    button.disabled = false;
    const icon = element("span", "", "▶");
    icon.setAttribute("aria-hidden", "true");
    button.replaceChildren(icon, document.createTextNode(" 运行电路"));
  }
});

$("#agent-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.currentTarget.querySelector("button");
  const reply = $("#agent-reply");
  const errorBox = $("#agent-error");
  button.disabled = true;
  button.textContent = "校验中…";
  errorBox.hidden = true;
  try {
    const data = await api("/api/agent", { prompt: $("#prompt").value });
    reply.hidden = false;
    reply.textContent = data.reply;
    reply.setAttribute("tabindex", "-1");
    reply.focus();
    tell("Agent 回答已通过确定性校验");
  } catch (error) {
    reply.hidden = true;
    errorBox.hidden = false;
    errorBox.textContent = `${error.message}。仍可使用上方本地模拟与三后端转译。`;
    errorBox.setAttribute("tabindex", "-1");
    errorBox.focus();
  } finally {
    button.disabled = false;
    button.textContent = "发送给 Agent";
  }
});
