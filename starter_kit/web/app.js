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
  deutsch: `OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[2];
x q[2];
h q[0];
h q[1];
h q[2];
cx q[0],q[2];
cx q[1],q[2];
h q[0];
h q[1];
measure q[0] -> c[0];
measure q[1] -> c[1];`,
  grover: `OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0]; h q[1]; h q[2];
h q[2]; ccx q[0],q[1],q[2]; h q[2];
h q[0]; h q[1]; h q[2];
x q[0]; x q[1]; x q[2];
h q[2]; ccx q[0],q[1],q[2]; h q[2];
x q[0]; x q[1]; x q[2];
h q[0]; h q[1]; h q[2];
h q[2]; ccx q[0],q[1],q[2]; h q[2];
h q[0]; h q[1]; h q[2];
x q[0]; x q[1]; x q[2];
h q[2]; ccx q[0],q[1],q[2]; h q[2];
x q[0]; x q[1]; x q[2];
h q[0]; h q[1]; h q[2];
measure q -> c;`,
  qft: `OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
x q[0];
h q[3];
cu1(pi/2) q[2],q[3];
cu1(pi/4) q[1],q[3];
cu1(pi/8) q[0],q[3];
h q[2];
cu1(pi/2) q[1],q[2];
cu1(pi/4) q[0],q[2];
h q[1];
cu1(pi/2) q[0],q[1];
h q[0];
swap q[0],q[3];
swap q[1],q[2];
measure q -> c;`,
};

const exampleLessons = {
  bell: "Bell：H 创建两条等幅路径，CX 把第二比特与第一比特关联；Z 基只证明经典相关性，不单独证明真机纠缠。",
  ghz: "GHZ：一次 H 后串联 CX，把两条路径扩展为 |000⟩ 与 |111⟩；任一比特单独看仍是 50/50。",
  w: "W：三个单激发态 |001⟩、|010⟩、|100⟩ 各占三分之一；它与只含全 0/全 1 的 GHZ 分布不同。",
  uniform: "均匀叠加：每个比特各施加一次 H，三个比特产生 8 条等概率路径。",
  interference: "相位干涉：两次 S 让 |1⟩ 路径累积 π 相位；末尾 H 把相位差转换为确定的 |1⟩ 概率。",
  deutsch: "Deutsch–Jozsa：平衡 oracle 把函数差异写入相位；末尾两个 H 让输入寄存器确定测得 11。",
  grover: "Grover：oracle 标记 |111⟩，两次均值反射把它从 1/8 放大到 94.53125%，其余七态各 0.78125%。",
  qft: "QFT：测量仍是 16 个等概率结果，但逐门状态中的复振幅相位按 π/8 递进；只看柱状图会漏掉算法信息。",
};

const taskPrompts = {
  repair: "修复下面的 OpenQASM 2.0，使它生成 Bell 态并测量；只使用白名单门，并解释修改：\nOPENQASM 2.0; qreg q[2]; h q[0]; cx q[0],q[2];",
  backend: "我需要运行一个 3 比特 GHZ 电路。请比较 SpinQ、本源 OriginQ 与 Braket 的适用性，给出推荐后端、限制和可运行的 OpenQASM 2.0。",
};

const defaultAssertions = JSON.stringify(
  [
    { kind: "support", states: ["00", "11"], minimum_probability: 0.9 },
    { kind: "parity", bits: [0, 1], expected: "even", minimum_probability: 0.9 },
    { kind: "uniformity", states: ["00", "11"], maximum_total_variation: 0.05 },
  ],
  null,
  2,
);

const hybridExample = `OPENQASM 2.0; include "qelib1.inc";
qreg q[2]; creg c[2];
h q[0];
cx q[0],q[1];
measure q -> c;
classical {
  r1 = 10;
  if (c[1] == 1) { r3 = r1 + 2; } else { r3 = r1 - 8; }
}`;

const bellCounterexample = examples.bell.replace("cx q[0],q[1];", "x q[1];");

const $ = (selector) => document.querySelector(selector);
const qasm = $("#qasm");
const notice = $("#notice");
const agentHistory = [];
const TOUR_TARGETS = ["spinq", "originq", "braket"];
const TOUR_STATUSES = new Set(["pass", "fail", "inconclusive"]);
let lastProofUrl = null;
let lastHybridPathUrl = null;
let lastWitnessUrl = null;
let lastInquiryUrl = null;
let currentInquiryPassport = null;

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

function requireTourEvidence(condition, message) {
  if (!condition) throw new Error(`证据语义检查失败：${message}`);
}

function markTourStep(step, detail) {
  const status = $(`#tour-${step}-status`);
  status.textContent = `完成 · ${detail}`;
  status.closest("a").classList.add("complete");
}

function resetTourStep(step, reason = "输入已变化") {
  const status = $(`#tour-${step}-status`);
  status.textContent = reason;
  status.closest("a").classList.remove("complete");
}

function addEvidenceReset(selector, eventName, steps) {
  $(selector).addEventListener(eventName, () => {
    steps.forEach((step) => resetTourStep(step));
  });
}

function initializeTourState() {
  ["run", "compare", "assert", "witness", "hybrid", "contract"].forEach(
    (step) => resetTourStep(step, "未运行"),
  );
}

function renderCircuit() {
  const source = qasm.value;
  const count = Number((source.match(/qreg\s+\w+\[(\d+)\]/) || [])[1] || 0);
  const gates = Array.from({ length: count }, () => []);
  for (const rawStatement of source.split(";")) {
    const statement = rawStatement.trim();
    const match = statement.match(/^(h|x|s|sdg|t|tdg|rz|ry|cx|cu1|swap|ccx)\b/i);
    if (!match) continue;
    const used = [...statement.matchAll(/q\[(\d+)\]/g)].map((item) => Number(item[1]));
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
  $("#lesson").textContent = exampleLessons[name];
  document.querySelectorAll(".chip").forEach((button) => {
    button.classList.toggle("active", button.dataset.example === name);
  });
  renderCircuit();
  ["run", "compare", "assert", "witness"].forEach((step) => resetTourStep(step));
}

document.querySelectorAll(".chip").forEach((button) => {
  button.addEventListener("click", () => selectExample(button.dataset.example));
});
qasm.addEventListener("input", () => {
  renderCircuit();
  ["run", "compare", "assert", "witness"].forEach((step) => resetTourStep(step));
});
selectExample("bell");
$("#assertions-input").value = defaultAssertions;
$("#hybrid-source").value = hybridExample;
$("#candidate-qasm").value = bellCounterexample;
initializeTourState();

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

function parseJsonInput(raw, label) {
  try {
    return JSON.parse(raw);
  } catch (_error) {
    throw new Error(`${label} 不是合法 JSON`);
  }
}

function formatPercent(value) {
  return `${(value * 100).toFixed(1)}%`;
}

function renderAssertionSummary(item) {
  if ("minimum_probability" in item) {
    return `观测 ${formatPercent(item.observed_probability)}，阈值 ≥ ${formatPercent(item.minimum_probability)}`;
  }
  return `观测 TV ${item.observed_total_variation.toFixed(4)}，阈值 ≤ ${item.maximum_total_variation.toFixed(4)}`;
}

function renderAssertionItems(items, label) {
  const results = $("#assert-results");
  results.replaceChildren();
  items.forEach((item) => {
    const row = element("li", `audit-item ${item.status}`);
    const header = element(
      "strong",
      "",
      `${label} #${item.index + 1} · ${item.kind} · ${item.status.toUpperCase()}`,
    );
    const meta = element(
      "span",
      "audit-meta",
      `${item.evidence_mode} · ${renderAssertionSummary(item)}`,
    );
    row.append(header, meta);
    if (item.confidence_interval) {
      row.append(
        element(
          "small",
          "audit-note-inline",
          `confidence_interval ${item.confidence_interval.map(formatPercent).join(" – ")}`,
        ),
      );
    }
    results.append(row);
  });
}

function renderAssertionReport(data) {
  if (data.mode === "exact-local") {
    $("#assert-mode").textContent = "exact-local";
    $("#assert-caveat").textContent = data.attribution_caveat;
    renderAssertionItems(data.assertions, "本地");
    return;
  }
  const diagnosis = data.diagnosis;
  const items = diagnosis.observed_assertions.length
    ? diagnosis.observed_assertions
    : diagnosis.reference_assertions;
  const label = diagnosis.observed_assertions.length ? "观测" : "参考";
  $("#assert-mode").textContent = `${data.mode} · ${diagnosis.classification}`;
  $("#assert-caveat").textContent = diagnosis.attribution_caveat;
  renderAssertionItems(items, label);
}

function renderHybridReport(report) {
  $("#hybrid-path").textContent = report.branch_path || "无条件分支";
  $("#hybrid-caveat").textContent =
    "branch_path 以源码条件真假记为 ifN:T / ifN:F；machine_jump_taken 只说明机器是否跳转。";
  const branches = $("#hybrid-branches");
  branches.replaceChildren();
  report.branch_events.forEach((branch) => {
    const item = element("li", "audit-item");
    item.append(
      element(
        "strong",
        "",
        `${branch.branch_id} 号分支 · pc ${branch.pc} · machine_jump_taken=${branch.machine_jump_taken} · source_condition_true=${branch.source_condition_true}`,
      ),
      element(
        "span",
        "audit-meta",
        `source ${branch.source_operator} · measurements ${branch.influencing_measurements.join(", ") || "无"}`,
      ),
    );
    branches.append(item);
  });
  if (!report.branch_events.length) {
    branches.append(element("li", "audit-item", "该程序没有条件分支。"));
  }

  const events = $("#hybrid-events");
  events.replaceChildren();
  report.instruction_events.forEach((event) => {
    const changes = Object.entries(event.register_changes)
      .map(([register, value]) => `${register}=${value}`)
      .join(", ") || "无寄存器变化";
    const item = element("li", "audit-item");
    item.append(
      element(
        "strong",
        "",
        `step ${event.step} · pc ${event.pc} · ${event.operation} ${event.args.join(", ")}`,
      ),
      element("span", "audit-meta", `next_pc ${event.next_pc} · Δ ${changes}`),
    );
    events.append(item);
  });
  $("#hybrid-assembly").textContent = report.assembly;
  $("#hybrid-registers").textContent = JSON.stringify(report.final_registers, null, 2);
}

function renderHybridPathCertificate(certificate) {
  const report = certificate;
  const outcomeIndex = new Map(
    report.certificate.outcomes.map((item) => [item.outcome, item]),
  );
  const totalProbability = report.certificate.outcomes.reduce(
    (sum, item) => sum + item.probability,
    0,
  );
  const distinctFinalResults = new Set(
    report.certificate.outcomes
      .filter((item) => item.reachable)
      .map((item) => item.final_register_sha256),
  ).size;
  $("#hybrid-path").textContent = report.verification.valid ? "本地重算通过" : "验证失败";
  $("#hybrid-path-summary").textContent =
    `已按 2**num_clbits <= max_outcomes 的上限 ${report.certificate.limits.max_outcomes} 穷举 ${report.certificate.outcomes.length} 个 outcome；总概率 ${formatPercent(totalProbability)}。`;
  const overview = $("#hybrid-path-overview");
  overview.replaceChildren();
  [
    ["可达路径", String(report.certificate.path_groups.filter((item) => item.total_probability > 0).length)],
    ["死路径", String(report.certificate.dead_path_ids.length)],
    ["不可达 outcome", String(report.certificate.unreachable_outcomes.length)],
    ["不同终态", String(distinctFinalResults)],
  ].forEach(([label, value]) => {
    const card = element("div", "path-summary-card");
    card.append(element("strong", "", value), element("span", "", label));
    overview.append(card);
  });
  const probabilities = $("#hybrid-path-probabilities");
  probabilities.replaceChildren();
  report.certificate.path_groups.forEach((item) => {
    const pathOutcomes = report.certificate.outcomes.filter(
      (outcome) => outcome.path_id === item.path_id,
    );
    const row = element("li", "audit-item path-verdict");
    const reachable = item.reachable_outcomes.length > 0;
    const verdict = reachable ? "这条路径会发生" : "在当前量子态下不会发生";
    row.append(
      element("strong", "", `${item.path_id || "root"} · ${verdict}`),
      element(
        "span",
        "audit-meta",
        `路径概率 ${formatPercent(item.total_probability)} · outcomes ${item.outcomes.join("、") || "无"} · 不同终态 ${item.final_register_sha256s.length}`,
      ),
    );
    const bar = document.createElement("progress");
    bar.className = "path-bar";
    bar.max = 1;
    bar.value = item.total_probability;
    bar.setAttribute("aria-label", `${item.path_id || "root"} 的路径概率`);
    row.append(bar);
    row.append(
      element(
        "p",
        "audit-note-inline path-outcomes",
        `结果位串：${item.outcomes.join("、") || "无"}；可达：${item.reachable_outcomes.join("、") || "无"}`,
      ),
    );
    row.append(
      element(
        "small",
        "audit-note-inline",
        pathOutcomes
          .filter((outcome) => outcome.reachable)
          .map(
            (outcome) =>
              `${outcome.outcome} → ${Object.entries(outcome.final_registers)
                .map(([register, value]) => `${register}=${value}`)
                .join(", ") || "无源级寄存器变化"}`,
          )
          .join(" ｜ ") || "没有可达终态寄存器差异",
      ),
    );
    const details = document.createElement("details");
    details.append(
      element("summary", "", "查看源码条件、branch events 与哈希"),
      element(
        "p",
        "audit-note-inline",
        pathOutcomes
          .flatMap((outcome) => outcome.branch_events)
          .map(
            (branch) =>
              `${branch.branch_id}：source_condition_true=${branch.source_condition_true} · machine_jump_taken=${branch.machine_jump_taken}`,
          )
          .join(" ｜ ") || "无条件分支",
      ),
      element(
        "small",
        "audit-note-inline",
        pathOutcomes
          .map(
            (outcome) =>
              `${outcome.outcome} → ${outcome.final_register_sha256.slice(0, 12)}…`,
          )
          .join(" ｜ "),
      ),
    );
    row.append(details);
    probabilities.append(row);
  });
  if (!report.certificate.path_groups.length) {
    probabilities.append(element("li", "audit-item", "没有可达路径。"));
  }

  const unreachable = $("#hybrid-path-unreachable");
  unreachable.replaceChildren();
  report.certificate.unreachable_outcomes.forEach((item) => {
    const outcome = outcomeIndex.get(item);
    unreachable.append(
      element(
        "li",
        "audit-item",
        `${item} · ${outcome?.path_id || "root"} · 在当前量子态下不会发生`,
      ),
    );
  });
  if (!report.certificate.unreachable_outcomes.length) {
    unreachable.append(element("li", "audit-item", "没有不可达 outcome。"));
  }
  if (lastHybridPathUrl) URL.revokeObjectURL(lastHybridPathUrl);
  const hybridPathBlob = new Blob([JSON.stringify(report, null, 2)], {
    type: "application/json",
  });
  lastHybridPathUrl = URL.createObjectURL(hybridPathBlob);
  const downloadHybridPath = $("#download-hybrid-path");
  downloadHybridPath.href = lastHybridPathUrl;
  downloadHybridPath.download = `loomq-hybrid-paths-${report.verification.certificate_sha256.slice(0, 12)}.json`;
  downloadHybridPath.setAttribute("aria-disabled", "false");
  $("#hybrid-path-panel").open = true;
}

function renderWitnessAudit(audit) {
  const verification = audit.verification;
  $("#witness-status").textContent = verification.valid ? "本地重算通过" : "验证失败";
  const digest = audit.integrity.audit_sha256;
  $("#witness-integrity").textContent =
    `SHA-256 ${digest} · 内容地址用于发现归档篡改，不是身份签名。`;
  const chain = $("#witness-chain");
  chain.replaceChildren();
  audit.witness_chain.forEach((stage) => {
    const item = element("li", "");
    const witnesses = stage.witness_ids.length ? stage.witness_ids.join(" → ") : "无可归因 witness";
    item.append(
      element("strong", "", stage.stage),
      element("code", "", witnesses),
      element("p", "audit-note", stage.detail || stage.scope || "确定性跨模块映射"),
    );
    chain.append(item);
  });
  if (lastWitnessUrl) URL.revokeObjectURL(lastWitnessUrl);
  const blob = new Blob([JSON.stringify(audit, null, 2)], { type: "application/json" });
  lastWitnessUrl = URL.createObjectURL(blob);
  const downloadWitness = $("#download-witness");
  downloadWitness.href = lastWitnessUrl;
  downloadWitness.download = `loomq-witness-chain-${digest.slice(0, 12)}.json`;
  downloadWitness.setAttribute("aria-disabled", "false");
  $("#witness-panel").focus();
}

function formatOperation(operation) {
  if (!operation) return "无对应门";
  const qubits = operation.qubits.map((index) => `q[${index}]`).join(", ");
  const parameter = operation.parameter === null ? "" : `(${operation.parameter})`;
  return `${operation.gate.toUpperCase()}${parameter} ${qubits}`;
}

function renderComparison(report) {
  const structural = report.scope === "structural-mismatch";
  const divergent = report.first_divergent_gate !== null;
  $("#compare-status").textContent = structural
    ? "结构不可比"
    : divergent ? "发现因果分歧" : "未发现分歧";
  $("#compare-summary").textContent = structural
    ? "先让寄存器和测量映射保持一致。"
    : divergent
      ? `第 ${report.first_divergent_gate + 1} 扇门改变了后续量子态。`
      : "两个电路在本次精确比较范围内一致。";
  $("#compare-explanation").textContent = report.explanation;
  $("#compare-gate").textContent = divergent ? String(report.first_divergent_gate + 1) : "—";
  $("#compare-amplitude").textContent = structural
    ? "—" : Number(report.max_amplitude_delta).toFixed(6);
  $("#compare-distance").textContent = structural
    ? "—" : Number(report.final_distribution_distance).toFixed(6);
  $("#compare-operations").textContent = structural
    ? `结构差异：${report.reason}`
    : `参考：${formatOperation(report.reference_operation)} · 候选：${formatOperation(report.candidate_operation)}`;
  $("#compare-scope").textContent = report.scope_note;
  $("#compare-result").focus();
}

function renderInquiryBars(selector, bars) {
  const chart = $(selector);
  chart.replaceChildren();
  bars.forEach((item) => {
    const row = element("div", "inquiry-bar-row");
    const progress = element("progress", "inquiry-bar");
    progress.max = 1;
    progress.value = item.probability;
    progress.setAttribute("aria-label", `状态 ${item.state} 的概率 ${item.percent}`);
    row.append(
      element("strong", "", `|${item.state}⟩`),
      progress,
      element("span", "", item.percent),
    );
    chart.append(row);
  });
}

function resetInquiryAudit(message = "选择一条结论，让系统指出证据支持到哪里。") {
  const audit = $("#inquiry-audit");
  audit.className = "inquiry-audit";
  audit.textContent = message;
  const download = $("#download-inquiry");
  download.href = "#";
  download.setAttribute("aria-disabled", "true");
  if (lastInquiryUrl) {
    URL.revokeObjectURL(lastInquiryUrl);
    lastInquiryUrl = null;
  }
}

function renderStoryProgress(hasExperiment, auditStatus) {
  const progress = globalThis.LoomQInquiry.journeyProgress(hasExperiment, auditStatus);
  progress.chapters.forEach((chapter) => {
    const item = document.querySelector(`[data-story-chapter="${chapter.id}"]`);
    if (!item) return;
    item.classList.remove("current", "complete", "upcoming");
    item.classList.add(chapter.state);
    if (chapter.state === "current") item.setAttribute("aria-current", "step");
    else item.removeAttribute("aria-current");
  });
  $("#story-progress-copy").textContent = progress.message;
}

function renderInquiryExperiment(passport) {
  const view = globalThis.LoomQInquiry.viewModel(passport);
  renderInquiryBars("#inquiry-control-chart", view.controlBars);
  renderInquiryBars("#inquiry-variant-chart", view.variantBars);
  $("#inquiry-control-observation").textContent = view.controlObservation;
  $("#inquiry-variant-observation").textContent = view.variantObservation;
  $("#inquiry-finding-title").textContent =
    `${view.divergence} 是两次实验首次出现状态差异的位置。`;
  $("#inquiry-finding-copy").textContent = view.predictionReason;
  $("#inquiry-divergence").textContent = `first divergence ${view.divergence}`;
  $("#inquiry-results").hidden = false;
  $("#inquiry-results").scrollIntoView({
    behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
    block: "start",
  });
  return view;
}

function renderInquiryAudit(passport) {
  const view = globalThis.LoomQInquiry.viewModel(passport);
  const audit = $("#inquiry-audit");
  audit.className = `inquiry-audit ${view.auditStatus}`;
  audit.replaceChildren(
    element("strong", "", globalThis.LoomQInquiry.auditHeading(view.auditStatus)),
    element("p", "", view.auditClaim),
    element("p", "inquiry-audit-reason", view.auditReason),
    element("small", "", `证据边界：${view.caveat}`),
  );
  if (lastInquiryUrl) URL.revokeObjectURL(lastInquiryUrl);
  lastInquiryUrl = URL.createObjectURL(
    new Blob([JSON.stringify(passport, null, 2)], { type: "application/json" }),
  );
  const download = $("#download-inquiry");
  download.href = lastInquiryUrl;
  download.download = "loomq-inquiry-bell-gates.json";
  download.setAttribute("aria-disabled", "false");
}

async function requestInquiry() {
  const payload = globalThis.LoomQInquiry.requestPayload(
    $("#inquiry-prediction").value,
    $("#inquiry-conclusion").value,
    128,
  );
  return api("/api/inquiry", payload);
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
  const proof = data.proof;
  const sourceMetrics = proof.metrics.source;
  const optimizedMetrics = proof.metrics.optimized;
  const metricDelta = (before, after) => before === after ? String(after) : `${before} → ${after}`;
  $("#proof-status").textContent = proof.equivalence.verified ? "已验证" : "未验证";
  $("#proof-scope").textContent =
    "证明范围：命名的通用酉恒等式；测量映射保持不变。它不把模拟结果冒充真机保真度。";
  $("#proof-gates").textContent = metricDelta(sourceMetrics.gate_count, optimizedMetrics.gate_count);
  $("#proof-depth").textContent = metricDelta(sourceMetrics.depth, optimizedMetrics.depth);
  $("#proof-two-qubit").textContent = metricDelta(
    sourceMetrics.two_qubit_gate_count,
    optimizedMetrics.two_qubit_gate_count,
  );
  const coveredSourceOperations = new Set([
    ...proof.lineage.flatMap((item) => item.source_operation_indices),
    ...proof.rewrites.flatMap((item) => item.source_operation_indices),
  ]);
  const sourceOperationCount = sourceMetrics.gate_count + sourceMetrics.measurement_count;
  $("#proof-lineage").textContent = `${coveredSourceOperations.size}/${sourceOperationCount} 项`;
  const proofTargets = $("#proof-targets");
  proofTargets.replaceChildren();
  Object.entries(data.proof.portability).forEach(([target, report]) => {
    const hash = report.native_ir_sha256.slice(0, 10);
    proofTargets.append(element("li", "", `${target} · ${report.roundtrip_verified ? "通过" : "失败"} · ${hash}…`));
  });
  const proofRewrites = $("#proof-rewrites");
  proofRewrites.replaceChildren();
  if (!proof.rewrites.length) {
    proofRewrites.append(element("li", "", "未发现冗余门；原线路直接进入三后端验证。"));
  } else {
    proof.rewrites.forEach((rewrite) => {
      const sources = rewrite.source_operation_indices.join(", ");
      proofRewrites.append(element("li", "", `${rewrite.rule} · 源操作 ${sources}`));
    });
  }
  if (lastProofUrl) URL.revokeObjectURL(lastProofUrl);
  const proofBlob = new Blob([JSON.stringify(proof, null, 2)], { type: "application/json" });
  lastProofUrl = URL.createObjectURL(proofBlob);
  const downloadProof = $("#download-proof");
  downloadProof.href = lastProofUrl;
  downloadProof.download = `loomq-prooftrace-${proof.source_sha256.slice(0, 12)}.json`;
  downloadProof.setAttribute("aria-disabled", "false");
  const traceSteps = $("#trace-steps");
  $("#state-trace").open = data.trace.length <= 15;
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

function validateRunEvidence(data) {
  const proof = data.proof;
  const portability = proof?.portability || {};
  const targets = Object.keys(portability).sort();
  requireTourEvidence(proof?.equivalence?.verified === true, "ProofTrace 未验证等价性");
  requireTourEvidence(
    targets.length === TOUR_TARGETS.length
      && TOUR_TARGETS.every((target) => targets.includes(target)),
    "三种声明目标不完整",
  );
  requireTourEvidence(
    TOUR_TARGETS.every((target) => portability[target]?.roundtrip_verified === true),
    "至少一种目标 IR 未通过独立回读",
  );
}

function validateAssertionEvidence(data) {
  requireTourEvidence(data.mode === "exact-local", "评委路径必须使用 exact-local 断言");
  requireTourEvidence(Array.isArray(data.assertions) && data.assertions.length > 0, "断言列表为空");
  requireTourEvidence(
    data.assertions.every(
      (item) => TOUR_STATUSES.has(item.status) && item.evidence_mode === "exact-local",
    ),
    "断言状态或 evidence_mode 不受支持",
  );
  requireTourEvidence(
    data.attribution_caveat?.includes("不归因具体噪声机制"),
    "缺少科学归因边界",
  );
}

function validateHybridPathEvidence(data) {
  const verification = data.verification;
  requireTourEvidence(verification.valid === true, "路径证书未通过服务端重算");
  requireTourEvidence(
    data.certificate?.schema_version === "loomq-hybrid-path-certificate-v1",
    "路径证书 schema 不匹配",
  );
  requireTourEvidence(
    Array.isArray(data.certificate.outcomes) && Array.isArray(data.certificate.path_groups),
    "路径证书缺少完备 outcome 或 path_groups",
  );
}

function renderPromptContract(data) {
  const contract = data.contract;
  const constraints = contract.backend_constraints;
  const result = $("#prompt-contract-result");
  result.replaceChildren();
  const summary = element("dl", "prompt-contract-summary");
  [
    ["任务", contract.task_kind],
    ["目标态", contract.state_goal ? JSON.stringify(contract.state_goal) : "未指定"],
    ["平台", constraints.platforms.join("、") || "未限定"],
    ["后端种类", constraints.kinds.join("、") || "未限定"],
    ["最少比特", constraints.minimum_qubits === null ? "未限定" : String(constraints.minimum_qubits)],
    ["费用", constraints.free ? "免费" : "未限定"],
    ["排队", constraints.no_queue ? "要求零排队" : "未要求零排队"],
    ["账号", constraints.requires_account === false ? "不需要" : constraints.requires_account === true ? "需要" : "未限定"],
  ].forEach(([label, value]) => {
    const row = document.createElement("div");
    row.append(element("dt", "", label), element("dd", "", value));
    summary.append(row);
  });
  result.append(
    summary,
    element(
      "p",
      "audit-note",
      `semantic SHA-256 ${contract.integrity.semantic_sha256.slice(0, 12)}… · 服务端重建通过 · 摘要不是身份签名。`,
    ),
  );
  $("#prompt-contract-status").textContent = "本地重建通过";
}

async function executeRunEvidence() {
  const data = await api("/api/run", {
    qasm: qasm.value,
    target: $("#target").value,
    shots: Number($("#shots").value),
  });
  validateRunEvidence(data);
  renderResults(data);
  markTourStep("run", "三后端回读");
  return data;
}

async function executeCompareEvidence(requireDivergence = false) {
  const data = await api("/api/compare", {
    reference_qasm: qasm.value,
    candidate_qasm: $("#candidate-qasm").value,
  });
  renderComparison(data);
  if (data.first_divergent_gate !== null) {
    markTourStep("compare", `第 ${data.first_divergent_gate + 1} 门`);
  } else if (requireDivergence) {
    requireTourEvidence(false, "默认反例没有首个分歧门");
  } else {
    resetTourStep("compare", "未发现首门分歧");
  }
  return data;
}

async function executeAssertionEvidence() {
  const payload = {
    qasm: qasm.value,
    assertions: parseJsonInput($("#assertions-input").value, "assertions"),
  };
  const observedRaw = $("#observed-input").value.trim();
  if (observedRaw) payload.observed = parseJsonInput(observedRaw, "observed");
  const shotsRaw = $("#observed-shots").value.trim();
  if (shotsRaw) payload.shots = Number(shotsRaw);
  const data = await api("/api/assert", payload);
  renderAssertionReport(data);
  if (data.mode !== "exact-local") {
    resetTourStep("assert", "非 exact-local");
    return data;
  }
  validateAssertionEvidence(data);
  const counts = data.assertions.reduce((summary, item) => {
    summary[item.status] = (summary[item.status] || 0) + 1;
    return summary;
  }, {});
  markTourStep("assert", Object.entries(counts).map(([key, value]) => `${value} ${key}`).join(" / "));
  return data;
}

async function executeWitnessEvidence() {
  const data = await api("/api/causal-audit", {
    reference_qasm: qasm.value,
    candidate_qasm: $("#candidate-qasm").value,
    assertions: parseJsonInput($("#assertions-input").value, "assertions"),
    hybrid_source: $("#hybrid-source").value,
    measurement_bits: parseJsonInput($("#hybrid-bits").value, "measurement_bits"),
    target: $("#target").value,
  });
  requireTourEvidence(data.verification?.valid === true, "Witness Chain 未通过本地重算");
  renderWitnessAudit(data);
  markTourStep("witness", "本地重算通过");
  return data;
}

async function executeHybridPathEvidence() {
  const data = await api("/api/hybrid-paths", {
    source: $("#hybrid-source").value,
    max_outcomes: Number($("#hybrid-max-outcomes").value),
  });
  validateHybridPathEvidence(data);
  renderHybridPathCertificate(data);
  markTourStep("hybrid", "语义重算通过");
  return data;
}

async function executePromptContractEvidence() {
  const data = await api("/api/prompt-contract", {
    prompt: $("#contract-prompt").value,
  });
  const contract = data.contract;
  const verification = data.verification;
  requireTourEvidence(verification.valid === true, "Prompt Contract 未通过服务端重建");
  requireTourEvidence(
    contract.schema_version === "loomq-prompt-contract-v1",
    "Prompt Contract schema 不匹配",
  );
  requireTourEvidence(contract.integrity.is_signature === false, "摘要被错误标记为签名");
  renderPromptContract(data);
  markTourStep("contract", contract.task_kind);
  return data;
}

$("#run").addEventListener("click", async () => {
  const button = $("#run");
  button.disabled = true;
  button.textContent = "正在运行并整理证据…";
  try {
    await executeRunEvidence();
    tell("运行完成：先看 ProofTrace，再看路径和结果表");
  } catch (error) {
    tell(error.message);
  } finally {
    button.disabled = false;
    const icon = element("span", "", "▶");
    icon.setAttribute("aria-hidden", "true");
    button.replaceChildren(icon, document.createTextNode(" 运行电路"));
  }
});

$("#run-inquiry").addEventListener("click", async () => {
  const button = $("#run-inquiry");
  const status = $("#inquiry-status");
  button.disabled = true;
  button.textContent = "正在运行两组实验…";
  status.textContent = "实验 A 与实验 B 正在使用相同 shots 运行。";
  try {
    const passport = await requestInquiry();
    currentInquiryPassport = passport;
    renderInquiryExperiment(passport);
    renderStoryProgress(true, null);
    resetInquiryAudit("实验已完成。现在选择结论，并让证据检查它。");
    status.textContent = "A/B 实验完成：只改变了 CX，下一步请形成结论。";
    tell("Quantum World：对照实验完成");
  } catch (error) {
    status.textContent = `实验失败：${error.message}`;
    tell(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "重新运行 A/B 对照实验";
  }
});

$("#audit-inquiry").addEventListener("click", async () => {
  const button = $("#audit-inquiry");
  button.disabled = true;
  button.textContent = "正在核对证据…";
  try {
    if (!currentInquiryPassport) {
      throw new Error("请先运行 A/B 对照实验，再审计结论");
    }
    const passport = globalThis.LoomQInquiry.withConclusion(
      currentInquiryPassport,
      $("#inquiry-conclusion").value,
    );
    renderInquiryAudit(passport);
    renderStoryProgress(true, passport.conclusion_audit.status);
    $("#inquiry-audit").setAttribute("tabindex", "-1");
    $("#inquiry-audit").focus();
    tell("结论审计完成；实验护照可以下载");
  } catch (error) {
    resetInquiryAudit(`结论审计失败：${error.message}`);
    tell(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "用实验审计结论";
  }
});

$("#inquiry-prediction").addEventListener("change", () => {
  currentInquiryPassport = null;
  $("#inquiry-results").hidden = true;
  $("#inquiry-status").textContent = "预测已记录；运行实验后再看答案。";
  resetInquiryAudit();
  renderStoryProgress(false, null);
});

$("#inquiry-conclusion").addEventListener("change", () => {
  resetInquiryAudit("结论已变化；请重新用当前实验审计。");
  renderStoryProgress(Boolean(currentInquiryPassport), null);
});

$("#run-assert").addEventListener("click", async () => {
  const button = $("#run-assert");
  button.disabled = true;
  button.textContent = "检查中…";
  try {
    await executeAssertionEvidence();
    tell("断言报告已更新");
  } catch (error) {
    tell(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "生成断言报告";
  }
});

$("#run-hybrid").addEventListener("click", async () => {
  const button = $("#run-hybrid");
  button.disabled = true;
  button.textContent = "回放中…";
  try {
    const data = await api("/api/hybrid-trace", {
      source: $("#hybrid-source").value,
      measurement_bits: parseJsonInput($("#hybrid-bits").value, "measurement_bits"),
    });
    renderHybridReport(data);
    tell("Hybrid 分支证据已更新");
  } catch (error) {
    tell(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "回放 Hybrid 分支";
  }
});

$("#run-hybrid-path").addEventListener("click", async () => {
  const button = $("#run-hybrid-path");
  button.disabled = true;
  button.textContent = "列举中…";
  try {
    await executeHybridPathEvidence();
    tell("Hybrid 路径证书已更新");
  } catch (error) {
    tell(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "列出所有可能分支";
  }
});

$("#copy-reference").addEventListener("click", () => {
  $("#candidate-qasm").value = qasm.value;
  ["compare", "witness"].forEach((step) => resetTourStep(step));
  $("#candidate-qasm").focus();
  tell("已复制当前电路；现在修改一扇门再比较");
});

$("#load-counterexample").addEventListener("click", () => {
  selectExample("bell");
  $("#candidate-qasm").value = bellCounterexample;
  tell("已加载 Bell 反例：CX 被替换为 X");
});

$("#run-compare").addEventListener("click", async () => {
  const button = $("#run-compare");
  button.disabled = true;
  button.textContent = "逐门比较中…";
  try {
    await executeCompareEvidence();
    tell("反事实比较已完成");
  } catch (error) {
    tell(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "比较因果差异";
  }
});

$("#run-witness").addEventListener("click", async () => {
  const button = $("#run-witness");
  button.disabled = true;
  button.textContent = "对齐证据中…";
  try {
    await executeWitnessEvidence();
    tell("统一 Witness Chain 已通过本地重算");
  } catch (error) {
    tell(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "生成统一审计链";
  }
});

$("#inspect-prompt-contract").addEventListener("click", async () => {
  const button = $("#inspect-prompt-contract");
  button.disabled = true;
  button.textContent = "重建中…";
  try {
    await executePromptContractEvidence();
    $("#prompt-contract-panel").focus();
    tell("Prompt Contract 已通过服务端重建");
  } catch (error) {
    $("#prompt-contract-status").textContent = "检查失败";
    tell(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "检查 Prompt Contract";
  }
});

const judgeTourSteps = [
  ["run", "运行与 ProofTrace", executeRunEvidence],
  ["compare", "首个因果分歧", () => executeCompareEvidence(true)],
  ["assert", "统计断言", executeAssertionEvidence],
  ["witness", "Witness Chain", executeWitnessEvidence],
  ["hybrid", "Mid-circuit 路径", executeHybridPathEvidence],
  ["contract", "Prompt Contract", executePromptContractEvidence],
];

$("#run-judge-tour").addEventListener("click", async () => {
  const button = $("#run-judge-tour");
  const status = $("#judge-tour-status");
  button.disabled = true;
  selectExample("bell");
  $("#target").value = "spinq";
  $("#shots").value = "1024";
  $("#candidate-qasm").value = bellCounterexample;
  $("#assertions-input").value = defaultAssertions;
  $("#observed-input").value = "";
  $("#observed-shots").value = "";
  $("#hybrid-source").value = hybridExample;
  $("#hybrid-bits").value = "[1, 0]";
  $("#hybrid-max-outcomes").value = "256";
  $("#contract-prompt").value = "Which free 20-qubit simulator on OriginQ needs no account?";
  judgeTourSteps.forEach(([step]) => resetTourStep(step, "未运行"));
  try {
    for (let index = 0; index < judgeTourSteps.length; index += 1) {
      const [_step, label, runStep] = judgeTourSteps[index];
      status.textContent = `正在运行 ${index + 1}/6 · ${label}`;
      await runStep();
    }
    status.textContent = "6/6 已由真实本地 API 完成；可沿状态条逐项复核。";
    $("#prompt-contract-panel").focus();
    tell("评委路径完成：6 项证据均通过各自语义门槛");
  } catch (error) {
    status.textContent = `已停止：${error.message}`;
    tell(error.message);
  } finally {
    button.disabled = false;
  }
});

addEvidenceReset("#target", "change", ["run", "witness"]);
addEvidenceReset("#shots", "change", ["run"]);
addEvidenceReset("#candidate-qasm", "input", ["compare", "witness"]);
addEvidenceReset("#assertions-input", "input", ["assert", "witness"]);
addEvidenceReset("#observed-input", "input", ["assert", "witness"]);
addEvidenceReset("#observed-shots", "input", ["assert", "witness"]);
addEvidenceReset("#hybrid-source", "input", ["hybrid", "witness"]);
addEvidenceReset("#hybrid-max-outcomes", "input", ["hybrid"]);
addEvidenceReset("#hybrid-bits", "input", ["witness"]);
addEvidenceReset("#contract-prompt", "input", ["contract"]);

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
