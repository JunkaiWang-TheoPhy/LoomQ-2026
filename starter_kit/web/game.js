"use strict";

const engine = globalThis.AtlasGameEngine;
const $ = (selector) => document.querySelector(selector);
const locationNames = {
  observatory: "观测站",
  field: "分岔原野",
  archive: "证据塔",
};
const sceneMessages = {
  observatory: "调查四件物品，拼出一套可靠的观察方法。",
  field: "先留下预测，再运行只改变一个条件的 A/B 调查。",
  archive: "选择一条结论，让同一份实验护照审计它。",
};
const clueNotes = {
  state: "状态记录系统怎样被准备，不是假设它早已藏着唯一答案。",
  possibility: "观察以前保留多种可能，不要过早把世界压成一个答案。",
  repeat: "一次观察只有一条记录；重复同一准备，才能看见分布。",
  control: "前后只改一个条件，才知道变化从哪里开始。",
};

let state = engine.createGame();

function setStatus(message) {
  $("#game-status").textContent = message;
}

function caseStatus() {
  if (state.audit) return "案件已归档";
  if (state.passport) return "等待结论审计";
  if (engine.briefingComplete(state)) return "执行 A/B 调查";
  return `调查规则 ${state.clues.length} / 4`;
}

function renderWorld() {
  const progress = engine.locationProgress(state);
  progress.forEach((item) => {
    const node = document.querySelector(`[data-game-location="${item.id}"]`);
    node.classList.remove("current", "complete", "locked");
    node.classList.add(item.state);
    node.disabled = item.state === "locked";
    if (state.location === item.id) node.setAttribute("aria-current", "location");
    else node.removeAttribute("aria-current");
  });
  const investigator = $("#investigator");
  investigator.className = `investigator at-${state.location}`;
  $("#game-location").textContent = locationNames[state.location];
  $("#game-score").value = state.score;
  $("#game-score").textContent = String(state.score);
  $("#game-case-status").textContent = caseStatus();
}

function renderScene() {
  document.querySelectorAll("[data-game-scene]").forEach((scene) => {
    const active = scene.dataset.gameScene === state.location;
    scene.hidden = !active;
    scene.classList.toggle("active", active);
  });
  const index = engine.LOCATIONS.indexOf(state.location) + 1;
  $("#scene-index").textContent = `地点 0${index}`;
  $("#scene-title").textContent = locationNames[state.location];
  setStatus(sceneMessages[state.location]);
}

function render() {
  renderWorld();
  renderScene();
}

function travel(location, focus = true) {
  try {
    state = engine.travel(state, location);
    render();
    if (focus) $("#scene-panel").focus();
  } catch (error) {
    setStatus(error.message);
  }
}

function renderClueNotebook(lastClue) {
  const notebook = $("#clue-notebook");
  notebook.replaceChildren();
  const heading = document.createElement("strong");
  heading.textContent = `调查手册 ${state.clues.length} / 4`;
  const note = document.createElement("p");
  note.textContent = engine.briefingComplete(state)
    ? "四条规则已记录。分岔原野开放，去做第一次对照实验。"
    : clueNotes[lastClue];
  notebook.append(heading, note);
}

function bars(probabilities, target) {
  target.replaceChildren();
  Object.entries(probabilities).sort().forEach(([label, probability]) => {
    const row = document.createElement("div");
    row.className = "mini-bar";
    const stateLabel = document.createElement("strong");
    stateLabel.textContent = `|${label}⟩`;
    const progress = document.createElement("progress");
    progress.max = 1;
    progress.value = probability;
    progress.setAttribute("aria-label", `${label} 概率 ${(probability * 100).toFixed(1)}%`);
    const percent = document.createElement("span");
    percent.textContent = `${(probability * 100).toFixed(0)}%`;
    row.append(stateLabel, progress, percent);
    target.append(row);
  });
}

async function runExperiment() {
  const button = $("#game-run-experiment");
  button.disabled = true;
  button.textContent = "调查进行中…";
  $("#experiment-light").textContent = "RUN";
  try {
    state = engine.recordPrediction(state, $("#game-prediction").value);
    const response = await fetch("/api/inquiry", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mission: "bell-gates",
        prediction: state.prediction,
        conclusion: $("#game-conclusion").value,
        shots: 128,
      }),
    });
    const passport = await response.json();
    if (!response.ok) throw new Error(passport.error || "实验服务返回错误");
    state = engine.attachPassport(state, passport);
    $("#case-complete").hidden = true;
    $("#game-audit-result").className = "game-audit-result";
    $("#game-audit-result").textContent = "新实验已完成，请重新提交结论。";
    const control = passport.experiment.control.probabilities;
    const variant = passport.experiment.variant.probabilities;
    $("#game-control-states").textContent = Object.keys(control).join(" / ");
    $("#game-variant-states").textContent = Object.keys(variant).join(" / ");
    bars(control, $("#game-control-bars"));
    bars(variant, $("#game-variant-bars"));
    $("#game-divergence").textContent =
      `首个状态分歧：g${passport.comparison.first_divergent_gate + 1} · ${passport.comparison.reference_operation.gate.toUpperCase()}。证据塔已经开放。`;
    $("#game-experiment-result").hidden = false;
    $("#experiment-light").textContent = "PASS";
    renderWorld();
    setStatus("A/B 调查完成：证据塔已经开放。");
  } catch (error) {
    $("#experiment-light").textContent = "ERROR";
    setStatus(`实验失败：${error.message}`);
  } finally {
    button.disabled = false;
    button.textContent = "重新运行 A/B 调查";
  }
}

function audit() {
  try {
    state = engine.auditConclusion(state, $("#game-conclusion").value);
    const result = $("#game-audit-result");
    result.className = `game-audit-result ${state.audit.status}`;
    result.replaceChildren();
    const heading = document.createElement("strong");
    heading.textContent = state.audit.status === "supported"
      ? "证据支持这条结论"
      : state.audit.status === "unsupported" ? "证据不支持这条结论" : "证据不足";
    const claim = document.createElement("p");
    claim.textContent = state.audit.claim;
    const reason = document.createElement("small");
    reason.textContent = state.audit.reason;
    result.append(heading, claim, reason);
    renderWorld();
    $("#final-score").value = state.score;
    $("#final-score").textContent = String(state.score);
    $("#case-complete").hidden = false;
    $("#close-complete").focus();
  } catch (error) {
    setStatus(error.message);
  }
}

function resetGame() {
  state = engine.createGame();
  document.querySelectorAll("[data-clue]").forEach((button) => {
    button.disabled = false;
    button.classList.remove("found");
  });
  $("#clue-notebook").innerHTML = "<strong>调查手册 0 / 4</strong><p>选择地图上的调查物品。</p>";
  $("#game-experiment-result").hidden = true;
  $("#game-audit-result").className = "game-audit-result";
  $("#game-audit-result").textContent = "等待提交结论。";
  $("#case-complete").hidden = true;
  $("#experiment-light").textContent = "READY";
  $("#game-run-experiment").textContent = "运行 A/B 调查";
  render();
}

document.querySelectorAll("[data-clue]").forEach((button) => {
  button.addEventListener("click", () => {
    state = engine.collectClue(state, button.dataset.clue);
    button.classList.add("found");
    button.disabled = true;
    renderClueNotebook(button.dataset.clue);
    renderWorld();
    setStatus(engine.briefingComplete(state)
      ? "观测站调查完成。选择地图上的分岔原野。"
      : `已记录：${button.querySelector("strong").textContent}。`);
  });
});

document.querySelectorAll("[data-game-location]").forEach((button) => {
  button.addEventListener("click", () => travel(button.dataset.gameLocation));
});

document.addEventListener("keydown", (event) => {
  if (["SELECT", "BUTTON", "A"].includes(document.activeElement.tagName)) return;
  const key = event.key.toLowerCase();
  if (["1", "2", "3"].includes(key)) {
    travel(engine.LOCATIONS[Number(key) - 1]);
    return;
  }
  const current = engine.LOCATIONS.indexOf(state.location);
  if (["arrowright", "arrowdown", "d", "s"].includes(key)) {
    travel(engine.LOCATIONS[Math.min(current + 1, engine.LOCATIONS.length - 1)]);
  } else if (["arrowleft", "arrowup", "a", "w"].includes(key)) {
    travel(engine.LOCATIONS[Math.max(current - 1, 0)]);
  }
});

$("#game-run-experiment").addEventListener("click", runExperiment);
$("#game-audit").addEventListener("click", audit);
$("#game-reset").addEventListener("click", resetGame);
$("#close-complete").addEventListener("click", () => {
  $("#case-complete").hidden = true;
  $("#game-audit-result").focus?.();
});

render();
