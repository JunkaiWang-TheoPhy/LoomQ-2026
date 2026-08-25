"use strict";

const missionEngine = globalThis.AtlasGameEngine;
const adventure = globalThis.AtlasAdventure;
const questEngine = globalThis.EightyYearQuest;
const $ = (selector) => document.querySelector(selector);
const canvas = $("#adventure-canvas");
const context = canvas.getContext("2d");

const clueStories = {
  state: {
    name: "准备日志",
    text: "每次调查都要先记下对象如何被准备。我们把这份完整描述叫作“状态”。它不是观察结果，而是所有可能结果的起点。",
  },
  possibility: {
    name: "分岔罗盘",
    text: "指针在被读取以前没有替你选好唯一方向。先保留多种可能，观察发生后再记录一条结果。",
  },
  repeat: {
    name: "回声计数器",
    text: "一次观察只留下一个答案。把同一种准备重复很多次，答案出现的频率才会组成可比较的分布。",
  },
  control: {
    name: "单变量封条",
    text: "比较两次实验时只改一个条件。否则看到变化，也不知道是谁造成的。",
  },
};

const colors = {
  night: "#071a1e",
  ink: "#0b292b",
  paper: "#f7edcf",
  mint: "#9fe1c8",
  acid: "#e8f36b",
  coral: "#ff8264",
};

let world = adventure.createWorld();
let mission = missionEngine.createGame();
let started = false;
let busy = false;
let dialogueLocked = false;
let dialogueAfterClose = null;
let lastTimestamp = performance.now();
let camera = { x: 0, y: 0 };
let lastRegion = adventure.regionAt(world.player.x);
let regionTimer = 0;
let toastTimer = 0;
let experimentPulse = 0;
let lastExperiment = null;
let storyWorld = null;
let storyWorldRequest = null;
let eightyQuest = questEngine.createState();
const keys = new Set();
const touchVector = { x: 0, y: 0 };

const decoration = (() => {
  let seed = 3917;
  const values = [];
  for (let index = 0; index < 150; index += 1) {
    seed = (seed * 16807) % 2147483647;
    const x = (seed % adventure.WORLD.width);
    seed = (seed * 16807) % 2147483647;
    const y = (seed % adventure.WORLD.height);
    seed = (seed * 16807) % 2147483647;
    values.push({ x, y, size: 2 + (seed % 5), phase: seed % 100 });
  }
  return values;
})();

function resizeCanvas() {
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.round(window.innerWidth * ratio);
  canvas.height = Math.round(window.innerHeight * ratio);
  canvas.style.width = `${window.innerWidth}px`;
  canvas.style.height = `${window.innerHeight}px`;
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
}

function objective() {
  if (mission.audit) return "案件已归档 · 可以继续探索";
  if (mission.passport) return "向东进入证据塔，审计你的结论";
  if (missionEngine.briefingComplete(mission)) return "穿过栅门，启动原野中央的 A/B 装置";
  if (mission.clues.length) return `寻找剩余的调查方法 · ${mission.clues.length} / 4`;
  return "在观测站寻找四件发光的调查工具";
}

function updateHud() {
  $("#game-objective").textContent = objective();
  $("#clue-count").textContent = `${mission.clues.length} / 4`;
  $("#game-score").value = mission.score;
  $("#game-score").textContent = String(mission.score);
  renderStoryBoard();
}

function completedStoryNodes() {
  const completed = [];
  if (mission.audit || eightyQuest.status === "complete") completed.push("observer-zero");
  if (eightyQuest.status === "complete") completed.push("eightieth-year");
  return completed;
}

function renderStoryBoard() {
  if (!storyWorld) return;
  const status = $("#case-board-status");
  const list = $("#case-list");
  if (!status || !list) return;
  status.textContent = storyWorld.progress.mainline === "complete"
    ? "主线已完成 · 五个案件已开放。点击案件查看它的调查问题。"
    : "完成主线实验后，五个案件会从地图上亮起。";
  list.replaceChildren();
  storyWorld.cases.forEach((caseFile) => {
    const state = storyWorld.progress.cases[caseFile.id];
    const item = document.createElement("li");
    const button = document.createElement("button");
    const copy = document.createElement("span");
    const title = document.createElement("strong");
    const theme = document.createElement("small");
    const stateLabel = document.createElement("em");
    button.type = "button";
    button.className = state;
    button.disabled = state === "locked";
    button.setAttribute("aria-label", `${caseFile.title} · ${state}`);
    title.textContent = caseFile.title;
    theme.textContent = caseFile.theme;
    stateLabel.textContent = state === "complete" ? "已归档" : state === "current" ? "可调查" : "待解锁";
    copy.append(title, theme);
    button.append(copy, stateLabel);
    button.addEventListener("click", () => (
      caseFile.id === "eightieth-year" ? openEightyYearQuest() : openCaseBriefing(caseFile)
    ));
    item.append(button);
    list.append(item);
  });
}

async function refreshStoryWorld(force = false) {
  if (storyWorldRequest && !force) return storyWorldRequest;
  if (force) storyWorldRequest = null;
  const query = completedStoryNodes().join(",");
  storyWorldRequest = fetch(`/api/story-world?completed=${encodeURIComponent(query)}`)
    .then((response) => {
      if (!response.ok) throw new Error("故事地图暂时无法读取");
      return response.json();
    })
    .then((payload) => {
      storyWorld = payload;
      renderStoryBoard();
      return payload;
    })
    .catch((error) => {
      announce(error.message);
      return null;
    })
    .finally(() => {
      storyWorldRequest = null;
    });
  return storyWorldRequest;
}

function announce(message) {
  $("#sr-status").textContent = message;
}

function toast(message) {
  const element = $("#toast");
  element.textContent = message;
  element.classList.add("visible");
  element.setAttribute("aria-hidden", "false");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    element.classList.remove("visible");
    element.setAttribute("aria-hidden", "true");
  }, 2300);
  announce(message);
}

function tone(frequency = 520, duration = 0.08) {
  try {
    const Audio = window.AudioContext || window.webkitAudioContext;
    if (!Audio) return;
    const audio = tone.audio || (tone.audio = new Audio());
    const oscillator = audio.createOscillator();
    const gain = audio.createGain();
    oscillator.type = "sine";
    oscillator.frequency.value = frequency;
    gain.gain.setValueAtTime(0.045, audio.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.0001, audio.currentTime + duration);
    oscillator.connect(gain).connect(audio.destination);
    oscillator.start();
    oscillator.stop(audio.currentTime + duration);
  } catch (_error) {
    // Audio is optional; interaction remains fully visual.
  }
}

function showDialogue({ speaker, kicker = "调查记录", text, choices = [], object = false, locked = false, afterClose = null }) {
  const box = $("#dialogue-box");
  $("#dialogue-speaker").textContent = speaker;
  $("#dialogue-kicker").textContent = kicker;
  $("#dialogue-text").textContent = text;
  $("#speaker-portrait").classList.toggle("object", object);
  const choiceBox = $("#dialogue-choices");
  choiceBox.replaceChildren();
  choices.forEach((choice) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = choice.label;
    button.addEventListener("click", choice.action);
    choiceBox.append(button);
  });
  dialogueLocked = locked;
  dialogueAfterClose = afterClose;
  $("#dialogue-close").hidden = locked || choices.length > 0;
  box.hidden = false;
  announce(`${speaker}：${text}`);
  (choiceBox.querySelector("button") || $("#dialogue-close")).focus();
}

function closeDialogue() {
  if (dialogueLocked || $("#dialogue-box").hidden) return;
  $("#dialogue-box").hidden = true;
  const callback = dialogueAfterClose;
  dialogueAfterClose = null;
  canvas.focus();
  if (callback) callback();
}

function openCaseBriefing(caseFile) {
  const contract = caseFile.evidence_contract;
  showDialogue({
    speaker: caseFile.title,
    kicker: `地图案件 · ${caseFile.theme}`,
    text: `${caseFile.question} ${caseFile.identities.public} ${caseFile.identities.hidden}`,
    choices: [
      {
        label: "运行这宗案件的最小对照实验",
        action: () => runCaseExperiment(caseFile),
      },
      {
        label: "查看这宗案件的证据边界",
        action: () => showDialogue({
          speaker: caseFile.title,
          kicker: "证据契约",
          text: `调查动作：${contract.changed_variable.operation}。可观察对象：${contract.observable}。${caseFile.claim_boundary}`,
        }),
      },
    ],
  });
}

function saveEightyYearQuest() {
  try {
    window.localStorage.setItem("loomq:eighty-year-quest", JSON.stringify(eightyQuest));
  } catch (_error) {
    announce("浏览器没有允许本地存档；本次回访仍可继续，但刷新后会重新开始案件。");
  }
}

function loadEightyYearQuest() {
  try {
    const raw = window.localStorage.getItem("loomq:eighty-year-quest");
    if (!raw) return;
    const parsed = JSON.parse(raw);
    if (parsed?.quest_id === questEngine.CASE_ID && Array.isArray(parsed.clues) && parsed.chapter) {
      eightyQuest = parsed;
    }
  } catch (_error) {
    eightyQuest = questEngine.createState();
  }
}

const eightyYearLabels = {
  "meet-shen-yao": "坐下，先听沈遥和青年副本各说一遍",
  "collect-paper-diary": "查看沈遥的纸质日记",
  "collect-copy-summary": "查看青年副本的自动摘要",
  "collect-daughter-letter": "查看女儿留下的信",
  "run-memory-probe": "只改变一个条件，运行记忆分歧实验",
  "hear-copy-request": "听青年副本提出请求",
  "hold-family-hearing": "召开一次家属听证",
  "choose-autonomy-first": "让沈遥优先决定自己的记忆",
  "choose-dual-signature": "建立本人和副本的双签协议",
  "choose-defer": "暂不裁决，保留观察期",
  "return-to-care-home": "第二天回到照护院回访",
};

function openEightyYearQuest() {
  const scene = questEngine.scene(eightyQuest);
  const complete = eightyQuest.status === "complete";
  showDialogue({
    speaker: "沈遥的案件",
    kicker: `第一案 · ${scene.title}${complete ? " · 已归档" : ""}`,
    text: complete
      ? `你选择了“${eightyQuest.ending}”。${eightyQuest.consequences.join("；")}。下一个案件已经进入地图。`
      : scene.text,
    choices: complete
      ? []
      : scene.actions.map((action) => ({ label: eightyYearLabels[action] || action, action: () => advanceEightyYearQuest(action) })),
  });
}

async function advanceEightyYearQuest(action) {
  if (action === "run-memory-probe") {
    const caseFile = storyWorld?.cases?.find((item) => item.id === "eightieth-year");
    if (!caseFile) return;
    busy = true;
    dialogueLocked = true;
    showDialogue({ speaker: "记忆分歧实验", kicker: "只改一个条件", text: "正在比较两条可重放线路；结果只说明电路差异，不判定人格。", object: true, locked: true });
    try {
      const contract = caseFile.evidence_contract;
      const response = await fetch("/api/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reference_qasm: contract.reference_qasm, candidate_qasm: contract.variant_qasm }),
      });
      const report = await response.json();
      if (!response.ok) throw new Error(report.error?.message || "实验失败");
      eightyQuest = questEngine.transition(eightyQuest, action, { first_divergent_gate: report.first_divergent_gate });
      saveEightyYearQuest();
      await refreshStoryWorld(true);
      showDialogue({
        speaker: "记忆分歧实验",
        kicker: "证据已写入案件",
        text: `首个分歧在 g${Number(report.first_divergent_gate) + 1}；总变差距离 ${Number(report.final_distribution_distance || 0).toFixed(6)}。${contract.observable}。`,
        object: true,
        afterClose: openEightyYearQuest,
      });
    } catch (error) {
      showDialogue({ speaker: "记忆分歧实验", kicker: "实验中断", text: `没有生成可复核结果：${error.message}`, object: true });
    } finally {
      busy = false;
      dialogueLocked = false;
    }
    return;
  }
  try {
    eightyQuest = questEngine.transition(eightyQuest, action);
    saveEightyYearQuest();
    await refreshStoryWorld(true);
    updateHud();
    openEightyYearQuest();
  } catch (error) {
    showDialogue({ speaker: "案件状态", kicker: "不能跳过这一段", text: error.message, object: true });
  }
}

async function runCaseExperiment(caseFile) {
  const contract = caseFile.evidence_contract;
  busy = true;
  dialogueLocked = true;
  showDialogue({
    speaker: caseFile.title,
    kicker: "正在比较两条可重放线路",
    text: "两条线路只改变证据契约中标出的条件；结果来自本地精确状态比较。",
    object: true,
    locked: true,
  });
  try {
    const response = await fetch("/api/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        reference_qasm: contract.reference_qasm,
        candidate_qasm: contract.variant_qasm,
      }),
    });
    const report = await response.json();
    if (!response.ok) throw new Error(report.error?.message || "对照实验失败");
    const gate = report.first_divergent_gate == null
      ? "没有发现首个分歧门"
      : `首个分歧在 g${report.first_divergent_gate + 1}`;
    showDialogue({
      speaker: caseFile.title,
      kicker: "实验记录已写入案件",
      text: `${gate}；最终分布总变差距离 ${Number(report.final_distribution_distance || 0).toFixed(6)}。${report.scope_note} ${caseFile.claim_boundary}`,
      object: true,
    });
  } catch (error) {
    showDialogue({
      speaker: caseFile.title,
      kicker: "实验中断",
      text: `没有生成可复核结果：${error.message}`,
      object: true,
    });
  } finally {
    busy = false;
    dialogueLocked = false;
  }
}

function worldToScreen(x, y) {
  return { x: x - camera.x, y: y - camera.y };
}

function drawGround(time) {
  context.fillStyle = "#83a998";
  context.fillRect(0, 0, 650, adventure.WORLD.height);
  context.fillStyle = "#8cac6b";
  context.fillRect(650, 0, 700, adventure.WORLD.height);
  context.fillStyle = "#a99676";
  context.fillRect(1350, 0, 570, adventure.WORLD.height);

  const gradient = context.createLinearGradient(0, 0, 0, adventure.WORLD.height);
  gradient.addColorStop(0, "rgba(255,255,230,.18)");
  gradient.addColorStop(1, "rgba(4,28,29,.12)");
  context.fillStyle = gradient;
  context.fillRect(0, 0, adventure.WORLD.width, adventure.WORLD.height);

  decoration.forEach((item) => {
    const regionColor = item.x < 650 ? "rgba(224,242,217,.28)" : item.x < 1350 ? "rgba(32,85,49,.2)" : "rgba(70,48,35,.18)";
    context.fillStyle = regionColor;
    context.beginPath();
    context.arc(item.x, item.y, item.size + Math.sin(time / 900 + item.phase) * .5, 0, Math.PI * 2);
    context.fill();
  });

  context.strokeStyle = "rgba(247,237,207,.38)";
  context.lineWidth = 72;
  context.lineCap = "round";
  context.lineJoin = "round";
  context.beginPath();
  context.moveTo(145, 850);
  context.bezierCurveTo(410, 850, 490, 570, 655, 560);
  context.bezierCurveTo(810, 550, 900, 600, 1060, 530);
  context.bezierCurveTo(1200, 470, 1310, 545, 1410, 535);
  context.bezierCurveTo(1530, 520, 1640, 520, 1780, 440);
  context.stroke();
  context.strokeStyle = "rgba(26,65,57,.15)";
  context.lineWidth = 3;
  context.setLineDash([8, 16]);
  context.stroke();
  context.setLineDash([]);
}

function roundedRect(x, y, width, height, radius, fill, stroke = null) {
  context.beginPath();
  context.roundRect(x, y, width, height, radius);
  if (fill) { context.fillStyle = fill; context.fill(); }
  if (stroke) { context.strokeStyle = stroke; context.stroke(); }
}

function drawTree(x, y, scale = 1, hue = "#255e52") {
  context.fillStyle = "rgba(5,29,27,.18)";
  context.beginPath();
  context.ellipse(x + 9 * scale, y + 12 * scale, 34 * scale, 13 * scale, 0, 0, Math.PI * 2);
  context.fill();
  context.fillStyle = "#6e5337";
  context.fillRect(x - 4 * scale, y, 8 * scale, 24 * scale);
  context.fillStyle = hue;
  for (const [ox, oy, radius] of [[0,-22,25],[-20,-10,20],[19,-8,22]]) {
    context.beginPath();
    context.arc(x + ox * scale, y + oy * scale, radius * scale, 0, Math.PI * 2);
    context.fill();
  }
  context.fillStyle = "rgba(232,243,107,.22)";
  context.beginPath();
  context.arc(x - 8 * scale, y - 31 * scale, 8 * scale, 0, Math.PI * 2);
  context.fill();
}

function drawBuildings() {
  // Observatory hall.
  roundedRect(72, 70, 320, 138, 20, "#173f42", "rgba(247,237,207,.42)");
  context.fillStyle = "#f7edcf";
  context.font = "800 14px system-ui";
  context.fillText("雾镜观测站", 105, 178);
  context.fillStyle = "#98d8d1";
  context.beginPath();
  context.arc(230, 92, 70, Math.PI, 0);
  context.fill();
  context.strokeStyle = "rgba(7,26,30,.5)";
  context.lineWidth = 5;
  context.stroke();
  context.fillStyle = colors.acid;
  context.fillRect(226, 82, 8, 58);

  // Weather relay / field lab.
  roundedRect(700, 110, 210, 185, 12, "#285952", "rgba(247,237,207,.36)");
  context.fillStyle = "#9fe1c8";
  context.fillRect(730, 145, 150, 76);
  context.strokeStyle = "#0b292b";
  context.lineWidth = 4;
  for (let line = 0; line < 4; line += 1) {
    context.beginPath(); context.moveTo(740, 160 + line * 16); context.lineTo(865, 160 + line * 16); context.stroke();
  }
  context.fillStyle = colors.paper;
  context.font = "700 12px system-ui";
  context.fillText("重复观测档案", 744, 260);

  // Reed pond.
  roundedRect(1085, 740, 235, 210, 70, "#4f8f86");
  context.strokeStyle = "rgba(232,243,107,.35)";
  context.lineWidth = 3;
  for (let line = 0; line < 6; line += 1) {
    context.beginPath(); context.arc(1200, 835, 28 + line * 17, Math.PI * .15, Math.PI * .85); context.stroke();
  }

  // Archive structures.
  roundedRect(1480, 120, 300, 210, 18, "#17393d", "rgba(247,237,207,.38)");
  context.fillStyle = "#d4c398";
  context.fillRect(1520, 160, 220, 120);
  context.fillStyle = "#17393d";
  for (let col = 0; col < 6; col += 1) context.fillRect(1535 + col * 34, 175, 13, 90);
  context.fillStyle = colors.paper;
  context.font = "800 14px system-ui";
  context.fillText("证据塔 · 公开档案层", 1530, 307);
  roundedRect(1510, 670, 290, 220, 18, "#544f43", "rgba(247,237,207,.28)");
  context.fillStyle = "#c6b487";
  context.fillRect(1545, 710, 220, 130);
  context.fillStyle = "#544f43";
  context.font = "800 13px system-ui";
  context.fillText("不可越界结论库", 1584, 780);

  [[55,300,1],[105,430,.8],[535,820,.9],[570,320,.8],[690,690,.9],[790,840,.8],[1010,270,1],[1150,330,.8],[1240,650,.9],[1410,830,.8],[1840,280,.9],[1840,720,1]].forEach((tree) => drawTree(...tree));
}

function drawGate(x, open, label) {
  context.save();
  context.translate(x, 540);
  context.strokeStyle = open ? "rgba(232,243,107,.34)" : "#183f3c";
  context.lineWidth = 11;
  context.beginPath();
  context.moveTo(-5, -190);
  context.lineTo(-5, 190);
  context.stroke();
  context.fillStyle = open ? "rgba(232,243,107,.18)" : colors.coral;
  context.fillRect(-17, -28, 24, 56);
  context.fillStyle = colors.paper;
  context.font = "800 10px ui-monospace";
  context.textAlign = "center";
  context.fillText(open ? "OPEN" : label, -5, -208);
  context.restore();
}

function drawCharacter(x, y, coat, label, player = false, time = 0) {
  const moving = player && (keys.size || Math.hypot(touchVector.x, touchVector.y) > .1);
  const bob = moving ? Math.sin(time / 90) * 2 : Math.sin(time / 450) * 1;
  context.fillStyle = "rgba(7,26,30,.25)";
  context.beginPath(); context.ellipse(x, y + 18, 20, 8, 0, 0, Math.PI * 2); context.fill();
  context.fillStyle = "#102f32";
  context.fillRect(x - 12, y + 6 + bob, 9, 17);
  context.fillRect(x + 3, y + 6 - bob, 9, 17);
  context.fillStyle = coat;
  roundedRect(x - 18, y - 30 + bob, 36, 44, 12, coat);
  context.fillStyle = colors.paper;
  context.beginPath(); context.arc(x, y - 40 + bob, 15, 0, Math.PI * 2); context.fill();
  context.fillStyle = player ? colors.acid : colors.night;
  context.beginPath(); context.arc(x, y - 45 + bob, 16, Math.PI, 0); context.fill();
  if (player) {
    context.strokeStyle = colors.paper;
    context.lineWidth = 3;
    context.beginPath(); context.arc(x, y - 40 + bob, 21, 0, Math.PI * 2); context.stroke();
  }
  if (label) {
    context.font = "800 10px system-ui";
    const width = context.measureText(label).width + 16;
    roundedRect(x - width / 2, y - 78, width, 22, 5, "rgba(7,26,30,.84)");
    context.fillStyle = player ? colors.acid : colors.paper;
    context.textAlign = "center";
    context.fillText(label, x, y - 63);
  }
}

function drawClue(target, clue, time) {
  const pulse = 1 + Math.sin(time / 330 + target.x) * .11;
  context.save();
  context.translate(target.x, target.y);
  context.scale(pulse, pulse);
  context.fillStyle = "rgba(232,243,107,.14)";
  context.beginPath(); context.arc(0, 0, 38, 0, Math.PI * 2); context.fill();
  context.strokeStyle = colors.acid;
  context.lineWidth = 3;
  context.beginPath(); context.arc(0, 0, 23, 0, Math.PI * 2); context.stroke();
  context.fillStyle = colors.night;
  roundedRect(-16, -16, 32, 32, 6, colors.night);
  context.strokeStyle = colors.paper;
  context.lineWidth = 2;
  if (clue === "state") {
    context.beginPath(); context.arc(0, 0, 8, 0, Math.PI * 2); context.moveTo(-14, 0); context.lineTo(14, 0); context.stroke();
  } else if (clue === "possibility") {
    context.beginPath(); context.moveTo(0, 13); context.lineTo(0, -4); context.lineTo(-10, -14); context.moveTo(0, -4); context.lineTo(10, -14); context.stroke();
  } else if (clue === "repeat") {
    context.beginPath(); context.arc(0, 0, 10, .2, Math.PI * 1.7); context.stroke();
  } else {
    context.beginPath(); context.moveTo(-11, -8); context.lineTo(11, -8); context.moveTo(-11, 0); context.lineTo(7, 0); context.moveTo(-11, 8); context.lineTo(2, 8); context.stroke();
  }
  context.restore();
  context.fillStyle = colors.night;
  context.font = "800 10px system-ui";
  context.textAlign = "center";
  context.fillText(clueStories[clue].name, target.x, target.y + 52);
}

function drawExperiment(time) {
  const x = 965;
  const y = 520;
  context.fillStyle = "rgba(7,26,30,.25)";
  context.beginPath(); context.ellipse(x, y + 52, 88, 24, 0, 0, Math.PI * 2); context.fill();
  roundedRect(x - 82, y - 56, 164, 106, 14, "#173f42", "rgba(247,237,207,.55)");
  context.fillStyle = "#0a2528";
  roundedRect(x - 62, y - 35, 124, 52, 6, "#071a1e");
  context.strokeStyle = busy ? colors.acid : colors.mint;
  context.lineWidth = 3;
  const phase = time / 170;
  for (let rail = 0; rail < 2; rail += 1) {
    const railY = y - 21 + rail * 22;
    context.beginPath(); context.moveTo(x - 52, railY); context.lineTo(x + 52, railY); context.stroke();
    if (busy || lastExperiment) {
      for (let dot = 0; dot < 4; dot += 1) {
        const dotX = x - 45 + ((phase * 18 + dot * 31) % 90);
        context.fillStyle = rail ? colors.coral : colors.acid;
        context.beginPath(); context.arc(dotX, railY, 4, 0, Math.PI * 2); context.fill();
      }
    }
  }
  context.fillStyle = busy ? colors.acid : colors.paper;
  context.font = "900 10px ui-monospace";
  context.textAlign = "center";
  context.fillText(busy ? "RUNNING A/B" : lastExperiment ? "PASSPORT READY" : "A/B FIELD DEVICE", x, y + 37);
}

function drawTargets(time) {
  drawCharacter(250, 830, colors.coral, "调查员 林默", false, time);
  adventure.TARGETS.filter((target) => target.kind === "clue" && !mission.clues.includes(target.id))
    .forEach((target) => drawClue(target, target.id, time));
  drawExperiment(time);
  drawCharacter(1635, 490, "#577878", "档案员 赫辛", false, time);
}

function drawMinimap() {
  const width = 170;
  const height = 58;
  const x = window.innerWidth - width - 22;
  const y = window.innerHeight < 680 ? 150 : 104;
  roundedRect(x, y, width, height, 8, "rgba(7,26,30,.78)", "rgba(247,237,207,.22)");
  context.fillStyle = "#83a998"; context.fillRect(x + 10, y + 12, 45, 34);
  context.fillStyle = "#8cac6b"; context.fillRect(x + 55, y + 12, 62, 34);
  context.fillStyle = "#a99676"; context.fillRect(x + 117, y + 12, 43, 34);
  context.fillStyle = colors.acid;
  context.beginPath();
  context.arc(x + 10 + (world.player.x / adventure.WORLD.width) * 150, y + 12 + (world.player.y / adventure.WORLD.height) * 34, 4, 0, Math.PI * 2);
  context.fill();
}

function render(time) {
  context.clearRect(0, 0, window.innerWidth, window.innerHeight);
  const desiredX = Math.max(0, Math.min(adventure.WORLD.width - window.innerWidth, world.player.x - window.innerWidth / 2));
  const desiredY = Math.max(0, Math.min(adventure.WORLD.height - window.innerHeight, world.player.y - window.innerHeight / 2));
  camera.x += (desiredX - camera.x) * .09;
  camera.y += (desiredY - camera.y) * .09;
  if (window.innerWidth >= adventure.WORLD.width) camera.x = -(window.innerWidth - adventure.WORLD.width) / 2;
  if (window.innerHeight >= adventure.WORLD.height) camera.y = -(window.innerHeight - adventure.WORLD.height) / 2;

  context.save();
  context.translate(-camera.x, -camera.y);
  drawGround(time);
  drawBuildings();
  drawGate(625, missionEngine.briefingComplete(mission), "4 CLUES");
  drawGate(1325, Boolean(mission.passport), "PASSPORT");
  drawTargets(time);
  drawCharacter(world.player.x, world.player.y, colors.coral, "YOU", true, time);
  context.restore();
  drawMinimap();
}

function updateInteractionPrompt() {
  const target = adventure.nearestTarget(world, mission);
  const prompt = $("#interaction-prompt");
  prompt.hidden = !target || busy || !$("#dialogue-box").hidden || !started;
  if (!target) return;
  const labels = {
    mentor: "交谈",
    clue: "调查物品",
    experiment: missionEngine.briefingComplete(mission) ? "启动 A/B 装置" : "检查上锁装置",
    archive: mission.passport ? "提交证据" : "检查封锁线",
  };
  prompt.querySelector("span").textContent = labels[target.kind];
}

function showRegion(region) {
  const card = $("#region-card");
  card.querySelector("strong").textContent = region;
  card.classList.add("visible");
  clearTimeout(regionTimer);
  regionTimer = setTimeout(() => card.classList.remove("visible"), 1700);
  announce(`进入${region}`);
}

function update(delta) {
  if (!started || busy || !$("#dialogue-box").hidden || !$("#case-complete").hidden) return;
  let dx = touchVector.x;
  let dy = touchVector.y;
  if (keys.has("arrowleft") || keys.has("a")) dx -= 1;
  if (keys.has("arrowright") || keys.has("d")) dx += 1;
  if (keys.has("arrowup") || keys.has("w")) dy -= 1;
  if (keys.has("arrowdown") || keys.has("s")) dy += 1;
  if (dx || dy) world = adventure.move(world, dx, dy, delta, mission);
  const region = adventure.regionAt(world.player.x);
  if (region !== lastRegion) {
    lastRegion = region;
    showRegion(region);
  }
  updateInteractionPrompt();
}

function formatDistribution(probabilities) {
  return Object.entries(probabilities)
    .filter(([, probability]) => probability > .01)
    .map(([label, probability]) => `|${label}⟩ ${(probability * 100).toFixed(0)}%`)
    .join("、");
}

async function runExperiment(prediction) {
  mission = missionEngine.recordPrediction(mission, prediction);
  updateHud();
  busy = true;
  dialogueLocked = true;
  showDialogue({
    speaker: "原野 A/B 装置",
    kicker: "正在重复观测 128 次",
    text: "两条线路使用相同的初始准备；B 线路只移除第二个操作。探针正在收集结果分布……",
    object: true,
    locked: true,
  });
  tone(440, .16);
  try {
    const response = await fetch("/api/inquiry", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        mission: "bell-gates",
        prediction,
        conclusion: "h-opens-branches-cx-correlates",
        shots: 128,
      }),
    });
    const passport = await response.json();
    if (!response.ok) throw new Error(passport.error || "实验装置没有返回护照");
    mission = missionEngine.attachPassport(mission, passport);
    lastExperiment = passport;
    const control = formatDistribution(passport.experiment.control.probabilities);
    const variant = formatDistribution(passport.experiment.variant.probabilities);
    const gate = passport.comparison.reference_operation.gate.toUpperCase();
    showDialogue({
      speaker: "原野 A/B 装置",
      kicker: "实验护照已生成 · 证据塔通路开放",
      text: `A 线路：${control}。B 线路：${variant}。两条世界线第一次在 g${passport.comparison.first_divergent_gate + 1} · ${gate} 分开。别急着解释，先把这份护照送去证据塔。`,
      object: true,
      afterClose: () => toast("获得实验护照 · 东侧证据塔已经开放"),
    });
    tone(660, .2);
  } catch (error) {
    showDialogue({
      speaker: "原野 A/B 装置",
      kicker: "运行中断",
      text: `本次调查没有生成证据：${error.message}。可以再次启动装置。`,
      object: true,
    });
  } finally {
    busy = false;
    dialogueLocked = false;
    updateHud();
  }
}

function openExperiment() {
  showDialogue({
    speaker: "原野 A/B 装置",
    kicker: "在运行之前留下预测",
    text: "一条线路执行第一步 H 和第二步 CX；另一条只移除 CX。你认为删掉第二步以后，结果分布会怎样变化？",
    object: true,
    choices: [
      { label: "H 打开多种结果；CX 改变两个比特的关联", action: () => runExperiment("h-opens-branches") },
      { label: "CX 才打开最初的多种结果", action: () => runExperiment("cx-opens-branches") },
      { label: "我不知道。先记录不确定，再看证据", action: () => runExperiment("not-sure") },
    ],
  });
}

function finishAudit(conclusion) {
  mission = missionEngine.auditConclusion(mission, conclusion);
  updateHud();
  refreshStoryWorld(true);
  const supported = mission.audit.status === "supported";
  showDialogue({
    speaker: "档案员 赫辛",
    kicker: supported ? "结论在证据边界内" : "结论越过了证据边界",
    text: `${mission.audit.claim} ${mission.audit.reason} ${supported ? "这条表述可以随护照归档。" : "案件仍可归档，但这句话必须保留 unsupported 标记。"}`,
    afterClose: showCompletion,
  });
  tone(supported ? 760 : 240, .22);
}

function openArchive() {
  if (mission.audit) {
    showDialogue({
      speaker: "档案员 赫辛",
      kicker: `已归档 · ${mission.audit.status}`,
      text: `${mission.audit.claim} ${mission.audit.reason}`,
    });
    return;
  }
  showDialogue({
    speaker: "档案员 赫辛",
    kicker: "证据只负责限制结论",
    text: "我不检查你像不像专家，只检查你的话有没有超过这份 A/B 护照。选一条你愿意署名的结论。",
    choices: [
      { label: "H 建立多种结果，CX 改变两个比特的关联结构", action: () => finishAudit("h-opens-branches-cx-correlates") },
      { label: "CX 建立了最初的多种结果", action: () => finishAudit("cx-opens-branches") },
      { label: "一次 Z 基实验完整证明了 Bell 非定域性", action: () => finishAudit("proves-nonlocality") },
    ],
  });
}

function showCompletion() {
  const supported = mission.audit?.status === "supported";
  $("#complete-summary").textContent = supported
    ? "你的结论与 A/B 护照一致。更重要的是，预测、对照、分布和审计都能被下一位调查员重新检查。"
    : "你的结论没有通过审计，但系统保存了这次失败，没有偷偷替你改成标准答案。可复查的错误也是证据链的一部分。";
  $("#final-score").value = mission.score;
  $("#final-score").textContent = String(mission.score);
  $("#case-complete").hidden = false;
  $("#continue-world").focus();
}

function collectClue(id) {
  mission = missionEngine.collectClue(mission, id);
  updateHud();
  const clue = clueStories[id];
  const finished = missionEngine.briefingComplete(mission);
  showDialogue({
    speaker: clue.name,
    kicker: `调查方法 ${mission.clues.length} / 4`,
    text: `${clue.text}${finished ? " 四条方法已经组成一套完整调查规程。西侧封锁门正在开启。" : ""}`,
    object: true,
    afterClose: () => {
      tone(finished ? 720 : 560, .14);
      if (finished) toast("四条调查方法已集齐 · 分岔原野开放");
    },
  });
}

function performInteract() {
  if (!started || busy || !$("#dialogue-box").hidden || !$("#case-complete").hidden) return;
  const interaction = adventure.interact(world, mission);
  if (interaction.event === "none") {
    toast("附近没有可调查的目标");
  } else if (interaction.event === "locked") {
    showDialogue({ speaker: "封锁门", kicker: "通路未开放", text: interaction.reason, object: true });
  } else if (interaction.event === "mentor") {
    showDialogue({
      speaker: "调查员 林默",
      kicker: "欢迎来到无形世界调查局",
      text: "量子不是一串门名。它首先是一种调查看不见对象的方法：记住怎样准备、允许多种可能、重复观察、每次只改一个条件。四件工具散落在观测站，去把它们找回来。",
    });
  } else if (interaction.event === "clue") {
    collectClue(interaction.id);
  } else if (interaction.event === "experiment") {
    openExperiment();
  } else if (interaction.event === "archive") {
    openArchive();
  }
}

function resetGame() {
  world = adventure.createWorld();
  mission = missionEngine.createGame();
  busy = false;
  lastExperiment = null;
  keys.clear();
  touchVector.x = 0;
  touchVector.y = 0;
  $("#dialogue-box").hidden = true;
  $("#case-complete").hidden = true;
  updateHud();
  refreshStoryWorld(true);
  lastRegion = adventure.regionAt(world.player.x);
  showRegion(lastRegion);
  canvas.focus();
  toast("案件已重置");
}

function frame(timestamp) {
  const delta = Math.min((timestamp - lastTimestamp) / 1000, .05);
  lastTimestamp = timestamp;
  update(delta);
  experimentPulse += delta;
  render(timestamp);
  requestAnimationFrame(frame);
}

document.addEventListener("keydown", (event) => {
  const key = event.key.toLowerCase();
  if (["arrowleft", "arrowright", "arrowup", "arrowdown", "w", "a", "s", "d", "e", " "].includes(key)) {
    event.preventDefault();
  }
  if (!started && key === "enter") {
    $("#start-game").click();
    return;
  }
  if (!$("#dialogue-box").hidden) {
    if ((key === " " || key === "e" || key === "enter") && !dialogueLocked && !$("#dialogue-close").hidden) closeDialogue();
    if (key === "escape" && !dialogueLocked) closeDialogue();
    return;
  }
  if (key === "e" || key === " ") performInteract();
  else keys.add(key);
});

document.addEventListener("keyup", (event) => keys.delete(event.key.toLowerCase()));
window.addEventListener("blur", () => keys.clear());
window.addEventListener("resize", resizeCanvas);

$("#start-game").addEventListener("click", () => {
  started = true;
  $("#start-screen").classList.add("dismissed");
  setTimeout(() => { $("#start-screen").hidden = true; }, 600);
  canvas.focus();
  showRegion(lastRegion);
  toast("寻找林默和四件发光的调查工具");
  tone(520, .18);
});
$("#dialogue-close").addEventListener("click", closeDialogue);
$("#touch-action").addEventListener("click", performInteract);
$("#game-reset").addEventListener("click", resetGame);
$("#continue-world").addEventListener("click", () => {
  $("#case-complete").hidden = true;
  canvas.focus();
});

const stick = $("#touch-stick");
const knob = $("#stick-knob");
function updateStick(event) {
  const rect = stick.getBoundingClientRect();
  const x = event.clientX - (rect.left + rect.width / 2);
  const y = event.clientY - (rect.top + rect.height / 2);
  const length = Math.max(1, Math.hypot(x, y));
  const radius = Math.min(36, length);
  const nx = x / length;
  const ny = y / length;
  touchVector.x = nx * Math.min(1, length / 32);
  touchVector.y = ny * Math.min(1, length / 32);
  knob.style.transform = `translate(${nx * radius}px, ${ny * radius}px)`;
}
stick.addEventListener("pointerdown", (event) => {
  stick.setPointerCapture(event.pointerId);
  updateStick(event);
});
stick.addEventListener("pointermove", (event) => {
  if (stick.hasPointerCapture(event.pointerId)) updateStick(event);
});
function releaseStick(event) {
  if (stick.hasPointerCapture(event.pointerId)) stick.releasePointerCapture(event.pointerId);
  touchVector.x = 0;
  touchVector.y = 0;
  knob.style.transform = "translate(0, 0)";
}
stick.addEventListener("pointerup", releaseStick);
stick.addEventListener("pointercancel", releaseStick);

resizeCanvas();
loadEightyYearQuest();
updateHud();
refreshStoryWorld();
requestAnimationFrame(frame);
