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
  w: `OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
x q[0];
ry(0.95531661812450919) q[1];
cx q[0],q[1];
ry(-0.95531661812450919) q[1];
cx q[0],q[1];
cx q[1],q[0];
ry(0.78539816339744839) q[2];
cx q[1],q[2];
ry(-0.78539816339744839) q[2];
cx q[1],q[2];
cx q[2],q[1];
measure q -> c;`,
  uniform: `OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
h q[1];
h q[2];
measure q -> c;`,
  interference: `OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
h q[0];
s q[0];
s q[0];
h q[0];
measure q -> c;`,
};

const taskPrompts = {
  repair: "修复下面的 OpenQASM 2.0，使它生成 Bell 态并测量；只使用白名单门，并解释修改：\nOPENQASM 2.0; qreg q[2]; h q[0]; cx q[0],q[2];",
  backend: "我需要运行一个 3 比特 GHZ 电路。请比较 SpinQ、本源 OriginQ 与 Braket 的适用性，给出推荐后端、限制和可运行的 OpenQASM 2.0。",
};

const $ = (selector) => document.querySelector(selector);
const qasm = $("#qasm");
const notice = $("#notice");
const agentHistory = [];

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
  const traceSteps = $("#trace-steps");
  traceSteps.replaceChildren();
  if (data.trace_notice) {
    traceSteps.append(element("li", "trace-step", `状态轨迹未展开：${data.trace_notice}；电路运行结果仍然有效。`));
  }
  data.trace.forEach((event) => {
    const item = element("li", "trace-step");
    const operation = event.operation;
    let title = "初始态 |0…0⟩";
    if (operation.kind === "gate") {
      const operands = operation.qubits.map((index) => `q[${index}]`).join(", ");
      title = `${operation.gate.toUpperCase()} · ${operands}`;
    } else if (operation.kind === "measure") {
      title = "测量映射";
    }
    const heading = element("div", "trace-step-heading");
    heading.append(
      element("span", "trace-number", String(event.step).padStart(2, "0")),
      element("strong", "", title),
    );
    item.append(heading, element("p", "", event.explanation));
    const states = element("div", "trace-states");
    event.states.forEach((state) => {
      const phase = Math.abs(state.phase_radians) < 1e-12 ? "0" : state.phase_radians.toFixed(2);
      const real = Math.abs(state.amplitude_real) < 1e-12 ? 0 : state.amplitude_real;
      const imaginary = Math.abs(state.amplitude_imag) < 1e-12 ? 0 : state.amplitude_imag;
      const amplitude = `${real.toFixed(3)}${imaginary >= 0 ? "+" : ""}${imaginary.toFixed(3)}i`;
      const chip = element("span", "trace-state");
      chip.append(
        element("strong", "", `|${state.basis}⟩`),
        element("small", "", `P ${(state.probability * 100).toFixed(1)}% · A ${amplitude} · φ ${phase}`),
      );
      states.append(chip);
    });
    if (event.truncated) {
      states.append(element("span", "trace-more", `另有 ${event.omitted_states} 个非零态`));
    }
    item.append(states);
    traceSteps.append(item);
  });
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
    const prompt = $("#prompt").value;
    const data = await api("/api/agent", { prompt, history: agentHistory });
    agentHistory.push(
      { role: "user", content: prompt },
      { role: "assistant", content: data.reply },
    );
    if (agentHistory.length > 8) agentHistory.splice(0, 2);
    $("#conversation-status").textContent = `已保留 ${agentHistory.length / 2} 轮上下文（最多 4 轮）`;
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

$("#clear-conversation").addEventListener("click", () => {
  agentHistory.splice(0);
  $("#conversation-status").textContent = "当前为新会话";
  $("#agent-reply").hidden = true;
  $("#agent-error").hidden = true;
  tell("多轮上下文已清空");
});
