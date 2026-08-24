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
  // Tiny pond and bridge make the map read as a place rather than a grid.
  drawPixelRect(15, 1, 7, 2, COLORS.water);
  drawPixelRect(16, 2, 5, 1, COLORS.water);
  drawPixelRect(9, 11, 4, 2, COLORS.water);
  for (let x = 9; x < 13; x += 1) drawPixelRect(x, 11, 1, 1, COLORS.yellow);
  // Quest gate.
  drawPixelRect(20, 6, 1, 3, mission.shards.length === 3 ? COLORS.yellow : COLORS.pink);
  ctx.fillStyle = COLORS.ink;
  ctx.fillRect(20 * TILE + 4, 6 * TILE, 8, 4);
  if (mission.shards.length === 3) {
    ctx.fillStyle = COLORS.yellow;
    ctx.fillRect(20 * TILE + 6, 6 * TILE + 5, 4, 38);
  }
  // Labels.
  label("雾镜镇", 2, 2, COLORS.ink);
  label("量子井", 18, 12, COLORS.ink);
  // Shards.
  worldEngine.TARGETS.filter((target) => target.kind === "shard" && !mission.shards.includes(target.id)).forEach((target, index) => {
    const pulse = Math.floor((time / 180 + index) % 2);
    drawPixelRect(target.x, target.y, 1, 1, pulse ? COLORS.yellow : COLORS.paper);
    drawPixelRect(target.x, target.y + 1, 1, 1, COLORS.pink);
    ctx.fillStyle = "rgba(246,221,120,.32)";
    ctx.fillRect(target.x * TILE - 4, target.y * TILE - 4, TILE + 8, TILE + 8);
  });
  // NPCs and signposts.
  drawPerson(3, 13, COLORS.pink, "林默");
  drawPerson(12, 7, COLORS.sky, "小满");
  drawPixelRect(18, 12, 3, 1, COLORS.wall);
  drawPixelRect(19, 11, 1, 2, COLORS.wallTop);
}

function label(text, x, y, color) {
  ctx.fillStyle = "rgba(255,242,200,.78)";
  ctx.fillRect(x * TILE - 2, y * TILE - 2, text.length * 7 + 6, 12);
  ctx.fillStyle = color;
  ctx.font = "bold 8px monospace";
  ctx.fillText(text, x * TILE + 1, y * TILE + 7);
}

function drawPerson(x, y, color, name) {
  const px = x * TILE;
  const py = y * TILE;
  ctx.fillStyle = "rgba(40,29,53,.25)";
  ctx.fillRect(px + 3, py + 13, 11, 3);
  ctx.fillStyle = color;
  ctx.fillRect(px + 3, py + 6, 10, 9);
  ctx.fillStyle = COLORS.paper;
  ctx.fillRect(px + 4, py + 1, 8, 8);
  ctx.fillStyle = COLORS.ink;
  ctx.fillRect(px + 5, py, 7, 3);
  label(name, x - 1, y - 2, COLORS.ink);
}

function drawPlayer() {
  const px = game.player.x * TILE;
  const py = game.player.y * TILE;
  ctx.fillStyle = "rgba(40,29,53,.3)";
  ctx.fillRect(px + 2, py + 13, 12, 3);
  ctx.fillStyle = COLORS.player;
  ctx.fillRect(px + 3, py + 6, 10, 9);
  ctx.fillStyle = COLORS.paper;
  ctx.fillRect(px + 4, py + 1, 8, 8);
  ctx.fillStyle = COLORS.ink;
  ctx.fillRect(px + 3, py, 10, 3);
  ctx.fillStyle = COLORS.yellow;
  ctx.fillRect(px + 6, py + 9, 4, 3);
}

function render(time) {
  ctx.imageSmoothingEnabled = false;
  drawMap(time);
  drawPlayer();
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
