"use strict";

const worldEngine = globalThis.PixelAtlas;
const canvas = document.querySelector("#pixel-canvas");
const ctx = canvas.getContext("2d");
const $ = (selector) => document.querySelector(selector);
const TILE = 16;
const COLORS = { grass: "#75b59e", grass2: "#83c1a4", wall: "#3e3657", wallTop: "#5f577b", water: "#78c7d4", flower: "#f06a7b", yellow: "#f6dd78", player: "#f06a7b", ink: "#281d35", paper: "#fff2c8" };
const mapImage = new Image();
mapImage.src = "/assets/pixel-map.png";

let game = worldEngine.createPixelGame();
let mission = { shards: [], complete: false };
let started = false;
let dialogueOpen = false;
let dialogueLocked = false;
let keys = new Set();
let touch = { x: 0, y: 0 };
let toastTimer = 0;
let lastFrame = performance.now();
let currentScene = worldEngine.sceneAt(game.player);

function announce(text) { $("#pixel-sr").textContent = text; }

function toast(text) {
  const element = $("#pixel-toast");
  element.textContent = text;
  element.classList.add("visible");
  element.setAttribute("aria-hidden", "false");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { element.classList.remove("visible"); element.setAttribute("aria-hidden", "true"); }, 2000);
  announce(text);
}

function updateHud() {
  $("#pixel-shards").textContent = `${mission.shards.length} / 3`;
  $("#pixel-objective").textContent = mission.complete
    ? "调查完成 · 继续探索"
    : mission.shards.length === 3 ? "去找小满，启动量子井" : `找齐三枚调查碎片 · ${mission.shards.length} / 3`;
  document.querySelectorAll(".quickbar-slot").forEach((slot) => {
    slot.classList.toggle("collected", mission.shards.includes(slot.dataset.slot));
  });
  $("#pixel-scene-name strong").textContent = worldEngine.SCENES[currentScene].name;
}

function openDialogue({ speaker, kicker = "调查记录", text, choices = [], locked = false, afterClose = null }) {
  dialogueOpen = true;
  dialogueLocked = locked;
  $("#pixel-speaker").textContent = speaker;
  $("#pixel-kicker").textContent = kicker;
  $("#pixel-text").textContent = text;
  const choicesBox = $("#pixel-choices");
  choicesBox.replaceChildren();
  choices.forEach((choice) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = choice.label;
    button.addEventListener("click", choice.action);
    choicesBox.append(button);
  });
  $("#pixel-close").hidden = locked || choices.length > 0;
  $("#pixel-dialogue").hidden = false;
  openDialogue.afterClose = afterClose;
  (choicesBox.querySelector("button") || $("#pixel-close")).focus();
  announce(`${speaker}：${text}`);
}

function closeDialogue() {
  if (!dialogueOpen || dialogueLocked) return;
  dialogueOpen = false;
  $("#pixel-dialogue").hidden = true;
  const afterClose = openDialogue.afterClose;
  openDialogue.afterClose = null;
  canvas.focus();
  if (afterClose) afterClose();
}

function drawPixelRect(x, y, width, height, color) {
  ctx.fillStyle = color;
  ctx.fillRect(x * TILE, y * TILE, width * TILE, height * TILE);
}

function drawMap(time) {
  if (mapImage.complete && mapImage.naturalWidth) {
    ctx.drawImage(mapImage, 0, 0, canvas.width, canvas.height);
  } else {
    ctx.fillStyle = COLORS.grass;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }
  if (!mapImage.complete || !mapImage.naturalWidth) {
    for (let y = 0; y < worldEngine.HEIGHT; y += 1) {
      for (let x = 0; x < worldEngine.WIDTH; x += 1) {
        if (worldEngine.MAP[y][x] === "#") {
          drawPixelRect(x, y, 1, 1, COLORS.wall);
          ctx.fillStyle = COLORS.wallTop;
          ctx.fillRect(x * TILE, y * TILE, TILE, 4);
          ctx.fillStyle = "rgba(17,24,45,.18)";
          ctx.fillRect(x * TILE + 4, y * TILE + 9, 3, 3);
        } else {
          ctx.fillStyle = (x + y) % 3 === 0 ? COLORS.grass2 : COLORS.grass;
          ctx.fillRect(x * TILE, y * TILE, TILE, TILE);
          if ((x * 7 + y * 11) % 29 === 0) {
            ctx.fillStyle = COLORS.flower;
            ctx.fillRect(x * TILE + 5, y * TILE + 7, 3, 3);
            ctx.fillStyle = COLORS.yellow;
            ctx.fillRect(x * TILE + 6, y * TILE + 6, 2, 2);
          }
        }
      }
    }
  }
  drawGate();
  drawQuantumWell(18, 12, time);
  // Labels.
  label("雾镜镇", 2, 2, COLORS.ink);
  label("量子井", 17, 10, COLORS.ink);
  // Shards.
  worldEngine.TARGETS.filter((target) => target.kind === "shard" && !mission.shards.includes(target.id)).forEach((target, index) => {
    drawShard(target.x, target.y, time, index);
  });
  // NPCs and signposts.
  drawPerson(3, 13, COLORS.pink, "林默", time);
  drawPerson(12, 7, COLORS.sky, "小满", time);
}

function label(text, x, y, color) {
  ctx.fillStyle = "rgba(40,29,53,.86)";
  ctx.fillRect(x * TILE - 2, y * TILE - 2, text.length * 6 + 6, 11);
  ctx.strokeStyle = "rgba(246,221,120,.7)";
  ctx.lineWidth = 1;
  ctx.strokeRect(x * TILE - 1, y * TILE - 1, text.length * 6 + 4, 9);
  ctx.fillStyle = color;
  ctx.font = "bold 6px monospace";
  ctx.fillText(text, x * TILE + 1, y * TILE + 6);
}

function drawPerson(x, y, color, name, time = 0) {
  const px = x * TILE;
  const bob = Math.floor(time / 260 + x) % 2;
  const py = y * TILE - bob;
  const isMentor = name === "林默";
  ctx.fillStyle = "rgba(40,29,53,.25)";
  ctx.fillRect(px + 1, py + 14, 14, 3);
  ctx.fillStyle = COLORS.ink;
  ctx.fillRect(px + 4, py + 14, 3, 3);
  ctx.fillRect(px + 9, py + 14, 3, 3);
  ctx.fillStyle = COLORS.ink;
  ctx.fillRect(px + 2, py + 7, 12, 8);
  ctx.fillStyle = color;
  ctx.fillRect(px + 3, py + 6, 10, 9);
  ctx.fillRect(px + 1, py + 8, 3, 5);
  ctx.fillRect(px + 12, py + 8, 3, 5);
  ctx.fillStyle = isMentor ? COLORS.yellow : COLORS.pink;
  ctx.fillRect(px + 5, py + 8, 6, 2);
  ctx.fillStyle = COLORS.paper;
  ctx.fillRect(px + 4, py + 1, 8, 7);
  ctx.fillStyle = COLORS.ink;
  ctx.fillRect(px + 3, py, 10, 3);
  ctx.fillRect(px + 4, py + 3, 2, 3);
  ctx.fillRect(px + 10, py + 3, 2, 3);
  ctx.fillRect(px + 5, py + 5, 2, 2);
  ctx.fillRect(px + 9, py + 5, 2, 2);
  if (isMentor) {
    ctx.fillStyle = COLORS.yellow;
    ctx.fillRect(px + 13, py + 9, 3, 5);
    ctx.fillStyle = COLORS.sky;
    ctx.fillRect(px + 14, py + 8, 2, 2);
  } else {
    ctx.fillStyle = COLORS.paper;
    ctx.fillRect(px + 1, py + 5, 3, 2);
    ctx.fillStyle = COLORS.pink;
    ctx.fillRect(px + 12, py + 2, 3, 5);
  }
  label(name, x - 1, y - 2, COLORS.paper);
}

function drawPlayer(time = 0) {
  const px = game.player.x * TILE;
  const bob = Math.floor(time / 180) % 2;
  const py = game.player.y * TILE - bob;
  ctx.fillStyle = "rgba(40,29,53,.3)";
  ctx.fillRect(px + 1, py + 14, 14, 3);
  ctx.fillStyle = COLORS.ink;
  ctx.fillRect(px + 4, py + 14, 3, 3);
  ctx.fillRect(px + 9, py + 14, 3, 3);
  ctx.fillRect(px + 2, py + 7, 12, 8);
  ctx.fillStyle = COLORS.player;
  ctx.fillRect(px + 3, py + 6, 10, 9);
  ctx.fillRect(px + 1, py + 8, 3, 5);
  ctx.fillRect(px + 12, py + 8, 3, 5);
  ctx.fillStyle = COLORS.yellow;
  ctx.fillRect(px + 2, py + 8, 2, 5);
  ctx.fillStyle = COLORS.paper;
  ctx.fillRect(px + 4, py + 1, 8, 7);
  ctx.fillStyle = COLORS.ink;
  ctx.fillRect(px + 3, py, 10, 3);
  ctx.fillRect(px + 4, py + 3, 2, 3);
  ctx.fillRect(px + 10, py + 3, 2, 3);
  const eyeX = game.player.facing === "left" ? px + 5 : game.player.facing === "right" ? px + 9 : px + 6;
  ctx.fillRect(eyeX, py + 5, 2, 2);
  ctx.fillStyle = COLORS.yellow;
  ctx.fillRect(px + 5, py + 9, 6, 3);
  ctx.fillStyle = COLORS.sky;
  ctx.fillRect(px + 12, py + 10, 4, 4);
}

function drawShard(x, y, time, index) {
  const px = x * TILE;
  const py = y * TILE;
  const bob = Math.floor((time / 160 + index) % 2);
  ctx.fillStyle = "rgba(246,221,120,.24)";
  ctx.fillRect(px - 5, py - 5 - bob, TILE + 10, TILE + 10);
  ctx.fillStyle = COLORS.ink;
  ctx.beginPath();
  ctx.moveTo(px + 8, py - 1 - bob);
  ctx.lineTo(px + 14, py + 7 - bob);
  ctx.lineTo(px + 8, py + 17 - bob);
  ctx.lineTo(px + 2, py + 7 - bob);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = index === 0 ? COLORS.sky : index === 1 ? COLORS.yellow : COLORS.pink;
  ctx.beginPath();
  ctx.moveTo(px + 8, py + 1 - bob);
  ctx.lineTo(px + 11, py + 7 - bob);
  ctx.lineTo(px + 8, py + 13 - bob);
  ctx.lineTo(px + 5, py + 7 - bob);
  ctx.closePath();
  ctx.fill();
  ctx.fillStyle = COLORS.paper;
  ctx.fillRect(px + 7, py + 3 - bob, 2, 3);
}

function drawGate() {
  const x = 20 * TILE;
  const y = 6 * TILE;
  ctx.fillStyle = "rgba(40,29,53,.35)";
  ctx.fillRect(x - 3, y + 27, 22, 4);
  ctx.fillStyle = COLORS.ink;
  ctx.fillRect(x, y, 4, 28);
  ctx.fillRect(x + 12, y, 4, 28);
  ctx.fillRect(x, y, 16, 4);
  ctx.fillStyle = mission.shards.length === 3 ? COLORS.yellow : COLORS.pink;
  ctx.fillRect(x + 5, y + 8, 2, 16);
  ctx.fillRect(x + 10, y + 8, 2, 16);
  if (mission.shards.length === 3) {
    ctx.fillStyle = "rgba(246,221,120,.6)";
    ctx.fillRect(x - 3, y - 4, 22, 2);
  }
}

function drawQuantumWell(x, y, time) {
  const px = x * TILE;
  const py = y * TILE;
  const pulse = Math.floor(time / 240) % 2;
  ctx.fillStyle = "rgba(40,29,53,.35)";
  ctx.fillRect(px - 5, py + 25, 42, 5);
  ctx.fillStyle = COLORS.ink;
  ctx.fillRect(px, py + 8, 32, 18);
  ctx.fillStyle = COLORS.wallTop;
  ctx.fillRect(px + 3, py + 5, 26, 7);
  ctx.fillStyle = COLORS.sky;
  ctx.fillRect(px + 7, py + 10, 18, 10);
  ctx.fillStyle = pulse ? COLORS.yellow : COLORS.pink;
  ctx.fillRect(px + 13, py + 7, 6, 16);
  ctx.fillStyle = COLORS.paper;
  ctx.fillRect(px + 15, py + 9, 2, 5);
  ctx.fillStyle = COLORS.ink;
  ctx.fillRect(px - 3, py + 2, 4, 9);
  ctx.fillRect(px + 29, py + 2, 4, 9);
}

function render(time) {
  ctx.imageSmoothingEnabled = false;
  drawMap(time);
  drawPlayer(time);
}

function performMove(dx, dy) {
  if (!started || dialogueOpen || $("#pixel-complete").hidden === false) return;
  game = worldEngine.move(game, dx, dy);
}

function collect(id) {
  mission.shards = [...mission.shards, id];
  updateHud();
  const lines = {
    state: "状态碎片：先记下系统怎样被准备。",
    repeat: "重复碎片：一次观察只是一条记录，重复才能看见分布。",
    control: "对照碎片：每次只改一个条件，变化才有来源。",
  };
  openDialogue({ speaker: "调查碎片", kicker: `已收集 ${mission.shards.length} / 3`, text: lines[id], afterClose: () => toast(mission.shards.length === 3 ? "三枚碎片齐了 · 去找小满" : "碎片加入调查手册") });
}

async function runWell() {
  openDialogue({ speaker: "量子井", kicker: "正在点亮", text: "三个碎片正在对齐……井底的两条路径开始分岔。", locked: true });
  try {
    const response = await fetch("/api/inquiry", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mission: "bell-gates", prediction: "h-opens-branches", conclusion: "h-opens-branches-cx-correlates", shots: 128 }) });
    const passport = await response.json();
    if (!response.ok) throw new Error(passport.error || "井没有返回护照");
    mission.complete = true;
    $("#pixel-complete-text").textContent = `量子井记录了 ${Object.keys(passport.experiment.control.probabilities).length} 种控制结果和 ${Object.keys(passport.experiment.variant.probabilities).length} 种变体结果。你可以把它们带回 LoomQ 实验室继续复查。`;
    $("#pixel-complete").hidden = false;
    $("#pixel-dialogue").hidden = true;
    dialogueOpen = false;
    updateHud();
  } catch (error) {
    dialogueLocked = false;
    openDialogue({ speaker: "量子井", kicker: "点亮失败", text: error.message });
  }
}

function interact() {
  if (!started || dialogueOpen) return;
  const event = worldEngine.interact(game, mission);
  if (event.event === "none") return toast("附近没有可以调查的东西");
  if (event.event === "locked") return openDialogue({ speaker: event.id === "npc" ? "小满" : "东侧栅门", kicker: "还差一点", text: event.reason });
  if (event.event === "shard") return collect(event.id);
  if (event.event === "mentor") return openDialogue({ speaker: "林默", kicker: "像素调查局", text: "三枚碎片在镇子的不同角落。找到它们，再把记录交给小满。" });
  if (event.event === "npc") return openDialogue({ speaker: "小满", kicker: "量子井管理员", text: "你把三条方法找回来了。现在要不要把它们放进井里，看看删掉第二步以后，世界会怎么分岔？", choices: [{ label: "启动量子井，运行一次 A/B", action: runWell }, { label: "我再走走，先不启动", action: closeDialogue }] });
  if (event.event === "gate") return toast("栅门已经打开，量子井在东南角");
}

function update(delta) {
  if (!started || dialogueOpen) return;
  let dx = touch.x;
  let dy = touch.y;
  if (keys.has("arrowleft") || keys.has("a")) dx -= 1;
  if (keys.has("arrowright") || keys.has("d")) dx += 1;
  if (keys.has("arrowup") || keys.has("w")) dy -= 1;
  if (keys.has("arrowdown") || keys.has("s")) dy += 1;
  if (dx || dy) performMove(dx, dy);
  const nextScene = worldEngine.sceneAt(game.player);
  if (nextScene !== currentScene) {
    currentScene = nextScene;
    updateHud();
    toast(`进入${worldEngine.SCENES[currentScene].name}`);
  }
}

function frame(time) {
  const delta = Math.min((time - lastFrame) / 1000, .05);
  lastFrame = time;
  update(delta);
  render(time);
  requestAnimationFrame(frame);
}

function reset() {
  game = worldEngine.createPixelGame();
  mission = { shards: [], complete: false };
  currentScene = worldEngine.sceneAt(game.player);
  dialogueOpen = false;
  dialogueLocked = false;
  $("#pixel-dialogue").hidden = true;
  $("#pixel-complete").hidden = true;
  updateHud();
  toast("像素案件已重置");
  canvas.focus();
}

document.addEventListener("keydown", (event) => {
  const key = event.key.toLowerCase();
  if (["arrowleft", "arrowright", "arrowup", "arrowdown", "w", "a", "s", "d", "e", " "].includes(key)) event.preventDefault();
  if (!started && key === "enter") { $("#pixel-start-button").click(); return; }
  if (dialogueOpen) {
    if ((key === " " || key === "e" || key === "enter") && !dialogueLocked && !$("#pixel-close").hidden) closeDialogue();
    return;
  }
  if (key === "e" || key === " ") interact();
  else keys.add(key);
});
document.addEventListener("keyup", (event) => keys.delete(event.key.toLowerCase()));
window.addEventListener("blur", () => keys.clear());

$("#pixel-start-button").addEventListener("click", () => { started = true; $("#pixel-start").hidden = true; canvas.focus(); toast("从林默开始，向地图中央走"); });
$("#pixel-close").addEventListener("click", closeDialogue);
$("#pixel-reset").addEventListener("click", reset);
$("#pixel-continue").addEventListener("click", () => { $("#pixel-complete").hidden = true; canvas.focus(); });
$("#pixel-touch-action").addEventListener("click", interact);

const stick = $("#pixel-stick");
const knob = stick.querySelector("i");
function steer(event) {
  const rect = stick.getBoundingClientRect();
  const x = event.clientX - (rect.left + rect.width / 2);
  const y = event.clientY - (rect.top + rect.height / 2);
  const length = Math.max(1, Math.hypot(x, y));
  touch.x = x / length;
  touch.y = y / length;
  knob.style.transform = `translate(${Math.max(-22, Math.min(22, x))}px, ${Math.max(-22, Math.min(22, y))}px)`;
}
function release(event) { if (stick.hasPointerCapture(event.pointerId)) stick.releasePointerCapture(event.pointerId); touch.x = 0; touch.y = 0; knob.style.transform = "translate(0,0)"; }
stick.addEventListener("pointerdown", (event) => { stick.setPointerCapture(event.pointerId); steer(event); });
stick.addEventListener("pointermove", (event) => { if (stick.hasPointerCapture(event.pointerId)) steer(event); });
stick.addEventListener("pointerup", release);
stick.addEventListener("pointercancel", release);

updateHud();
requestAnimationFrame(frame);
