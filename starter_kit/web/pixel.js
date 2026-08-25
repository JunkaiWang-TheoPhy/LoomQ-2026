"use strict";

const worldEngine = globalThis.PixelAtlas;
const canvas = document.querySelector("#pixel-canvas");
const ctx = canvas.getContext("2d");
const $ = (selector) => document.querySelector(selector);
const TILE = 16;
const COLORS = { grass: "#75b59e", grass2: "#83c1a4", wall: "#3e3657", wallTop: "#5f577b", water: "#78c7d4", flower: "#f06a7b", yellow: "#f6dd78", player: "#f06a7b", ink: "#281d35", paper: "#fff2c8" };
const MUSIC_PATTERNS = {
  village: { root: 0, tempo: 260, pad: [0, 7, 12], bass: [0, 0, -5, -5], melody: [12, 10, 7, 5, 7, 10, 12, 15] },
  river: { root: -5, tempo: 220, pad: [-5, 2, 7, 14], bass: [-5, -5, 2, 2], melody: [7, 10, 14, 17, 14, 10, 7, 5] },
  archive: { root: 3, tempo: 300, pad: [3, 10, 15], bass: [3, 3, -2, -2], melody: [15, 14, 10, 7, 10, 14, 17, 14] },
};
const mapImages = Object.fromEntries(Object.entries(worldEngine.SCENES).map(([id, scene]) => {
  const image = new Image();
  image.src = scene.background;
  return [id, image];
}));
const heroineSheet = new Image();
heroineSheet.src = "/assets/pixel-heroine-sheet.png";
const HEROINE_CELL = { width: 384, height: 512 };

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
let audioContext = null;
let audioGraph = null;
let musicTimer = null;
let musicOn = false;
let musicStep = 0;
let musicScene = "village";
let movementClock = 0;
const MOVE_INTERVAL = worldEngine.MOVE_INTERVAL;
let playerAction = "idle";
let jumpStartedAt = 0;
let jumpUntil = 0;
let storyWorld = null;
let completedNodes = [];
let storyBeatIndex = 0;
let zoom = worldEngine.DEFAULT_ZOOM;
let camera = worldEngine.cameraFor(game.player, { width: canvas.width, height: canvas.height }, zoom);
const pointers = new Map();
let pinchStartDistance = null;
let pinchStartZoom = zoom;

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
  $("#pixel-phase-value").textContent = worldEngine.SCENES[currentScene].phase.toUpperCase();
  $("#pixel-zoom-meter strong").textContent = `${Math.round(zoom * 100)}%`;
  updateGuide();
  updateStoryLog();
}

function updateStoryLog() {
  const story = storyContext();
  $("#pixel-story-title").textContent = story.title;
  $("#pixel-story-line").textContent = story.line;
  $("#pixel-story-log").hidden = !started || mission.complete;
}

function storyContext() {
  if (!storyWorld) return { title: "正在连接案件档案", line: "等待 Atlas-7 的叙事数据……" };
  if (!completedNodes.includes("observer-zero")) {
    const beat = storyWorld.mainline.beats[Math.min(storyBeatIndex, storyWorld.mainline.beats.length - 1)];
    return { title: storyWorld.mainline.title, line: `${beat.label}：${beat.action}` };
  }
  const currentCase = storyWorld.cases.find((item) => storyWorld.progress.cases[item.id] === "current") || storyWorld.cases[0];
  return { title: currentCase.title, line: currentCase.question };
}

async function loadStoryWorld() {
  const query = completedNodes.length ? `?completed=${encodeURIComponent(completedNodes.join(","))}` : "";
  try {
    const response = await fetch(`/api/story-world${query}`);
    if (!response.ok) throw new Error("story world request failed");
    storyWorld = await response.json();
    updateStoryLog();
  } catch (_error) {
    storyWorld = null;
    updateStoryLog();
  }
}

function setStoryBeat(index) {
  storyBeatIndex = index;
  updateStoryLog();
  announce(storyContext().line);
}

function guideIndex() {
  if (mission.shards.length >= 3 || currentScene !== "village") return 2;
  if (mission.shards.length > 0) return 1;
  return 0;
}

function updateGuide() {
  const guide = $("#pixel-guide");
  if (!started || mission.complete) {
    guide.hidden = true;
    return;
  }
  const index = guideIndex();
  guide.hidden = false;
  $("#pixel-guide-step").textContent = worldEngine.GUIDE_STEPS[index].action;
  guide.querySelectorAll(".guide-progress i").forEach((bar, barIndex) => {
    bar.classList.toggle("active", barIndex <= index);
  });
}

function noteFrequency(note) {
  return 110 * (2 ** (note / 12));
}

function createMusicGraph() {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) return null;
  if (!audioContext) audioContext = new AudioContextClass();
  if (audioGraph) return audioGraph;
  const masterGain = audioContext.createGain();
  const padGain = audioContext.createGain();
  const bassGain = audioContext.createGain();
  const melodyGain = audioContext.createGain();
  const percussionGain = audioContext.createGain();
  masterGain.gain.value = 0.0001;
  padGain.gain.value = 0.42;
  bassGain.gain.value = 0.34;
  melodyGain.gain.value = 0.26;
  percussionGain.gain.value = 0.18;
  [padGain, bassGain, melodyGain, percussionGain].forEach((gain) => gain.connect(masterGain));
  masterGain.connect(audioContext.destination);
  audioGraph = { masterGain, padGain, bassGain, melodyGain, percussionGain };
  return audioGraph;
}

function scheduleTone(note, duration, volume, type, when, destination) {
  if (!audioContext || !audioGraph || !musicOn) return;
  const oscillator = audioContext.createOscillator();
  const gain = audioContext.createGain();
  oscillator.type = type;
  oscillator.frequency.value = noteFrequency(note);
  gain.gain.setValueAtTime(0.0001, when);
  gain.gain.linearRampToValueAtTime(volume, when + 0.018);
  gain.gain.exponentialRampToValueAtTime(0.0001, when + duration);
  oscillator.connect(gain).connect(destination);
  oscillator.start(when);
  oscillator.stop(when + duration + 0.03);
}

function scheduleMusicStep() {
  if (!audioContext || !audioGraph || !musicOn) return;
  const pattern = MUSIC_PATTERNS[musicScene] || MUSIC_PATTERNS.village;
  const step = musicStep % pattern.melody.length;
  const when = audioContext.currentTime + 0.025;
  if (step === 0) pattern.pad.forEach((note) => scheduleTone(pattern.root + note, 1.8, 0.018, "sine", when, audioGraph.padGain));
  if (step % 2 === 0) scheduleTone(pattern.root + pattern.bass[(step / 2) % pattern.bass.length] - 12, 0.38, 0.035, "triangle", when, audioGraph.bassGain);
  scheduleTone(pattern.root + pattern.melody[step], 0.24, 0.028, "sine", when, audioGraph.melodyGain);
  if (step === 0 || step === 4) scheduleTone(pattern.root - 24, 0.055, 0.018, "square", when, audioGraph.percussionGain);
  musicStep += 1;
}

function playEventStinger(kind) {
  if (!audioContext || !audioGraph || !musicOn) return;
  const patterns = { shard: [12, 19, 24], transition: [0, 7, 12], success: [12, 16, 19, 24], error: [0, -3, -7] };
  const when = audioContext.currentTime + 0.02;
  (patterns[kind] || patterns.shard).forEach((note, index) => scheduleTone(note, 0.16 + index * 0.02, 0.045, "sine", when + index * 0.075, audioGraph.melodyGain));
}

function setMusicScene(scene) {
  if (!MUSIC_PATTERNS[scene] || scene === musicScene) return;
  musicScene = scene;
  musicStep = 0;
  playEventStinger("transition");
}

function startMusic() {
  const graph = createMusicGraph();
  if (!graph) {
    toast("当前浏览器不支持环境音乐，但调查仍可继续");
    return;
  }
  audioContext.resume();
  musicOn = true;
  graph.masterGain.gain.cancelScheduledValues(audioContext.currentTime);
  graph.masterGain.gain.setValueAtTime(Math.max(graph.masterGain.gain.value, 0.0001), audioContext.currentTime);
  graph.masterGain.gain.linearRampToValueAtTime(0.13, audioContext.currentTime + 0.45);
  $("#pixel-music-toggle").textContent = "♫ ON";
  $("#pixel-music-toggle").setAttribute("aria-pressed", "true");
  $("#pixel-music-toggle").setAttribute("aria-label", "关闭量子环境音乐");
  if (musicTimer) return;
  scheduleMusicStep();
  musicTimer = window.setInterval(scheduleMusicStep, MUSIC_PATTERNS[musicScene].tempo);
}

function stopMusic() {
  musicOn = false;
  if (musicTimer) window.clearInterval(musicTimer);
  musicTimer = null;
  if (audioContext && audioGraph) audioGraph.masterGain.gain.linearRampToValueAtTime(0.0001, audioContext.currentTime + 0.25);
  $("#pixel-music-toggle").textContent = "♫ OFF";
  $("#pixel-music-toggle").setAttribute("aria-pressed", "false");
  $("#pixel-music-toggle").setAttribute("aria-label", "打开量子环境音乐");
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

function drawContain(image) {
  const scale = Math.min(canvas.width / image.naturalWidth, canvas.height / image.naturalHeight);
  const width = image.naturalWidth * scale;
  const height = image.naturalHeight * scale;
  ctx.fillStyle = "#081522";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(image, (canvas.width - width) / 2, (canvas.height - height) / 2, width, height);
}

function drawMap(time) {
  const mapImage = mapImages[currentScene];
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
  drawBuildings();
  drawQuantumField(time);
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

function drawBuildings() {
  worldEngine.BUILDINGS.forEach((building) => {
    const px = building.x * TILE;
    const py = building.y * TILE;
    ctx.fillStyle = "rgba(0,0,0,.32)";
    ctx.fillRect(px - 3, py + building.height * TILE - 2, building.width * TILE + 6, 5);
    ctx.fillStyle = "#111c35";
    ctx.fillRect(px, py, building.width * TILE, building.height * TILE);
    ctx.strokeStyle = "#334b76";
    ctx.lineWidth = 2;
    ctx.strokeRect(px + 2, py + 2, building.width * TILE - 4, building.height * TILE - 4);
    ctx.fillStyle = COLORS.sky;
    if (building.kind === "outpost") {
      ctx.fillRect(px + 12, py + 8, 40, 4);
      ctx.fillRect(px + 20, py + 16, 24, 12);
      ctx.fillStyle = COLORS.pink;
      ctx.fillRect(px + 25, py + 14, 14, 3);
    } else if (building.kind === "relay") {
      ctx.fillRect(px + 8, py + 7, 12, 18);
      ctx.fillStyle = COLORS.yellow;
      ctx.fillRect(px + 11, py + 10, 6, 3);
    } else if (building.kind === "archive") {
      ctx.fillRect(px + 10, py + 6, 44, 5);
      ctx.fillRect(px + 20, py + 15, 25, 12);
      ctx.fillStyle = COLORS.pink;
      ctx.fillRect(px + 28, py + 16, 8, 8);
    } else {
      ctx.fillRect(px + 10, py + 8, 28, 4);
      ctx.fillStyle = COLORS.yellow;
      ctx.fillRect(px + 20, py + 13, 8, 8);
    }
  });
  worldEngine.OBSTACLES.forEach((obstacle) => {
    const px = obstacle.x * TILE;
    const py = obstacle.y * TILE;
    ctx.fillStyle = "#0b142a";
    ctx.fillRect(px, py, obstacle.width * TILE, obstacle.height * TILE);
    ctx.strokeStyle = "#273d62";
    ctx.lineWidth = 2;
    ctx.strokeRect(px + 1, py + 1, obstacle.width * TILE - 2, obstacle.height * TILE - 2);
    ctx.fillStyle = COLORS.sky;
    ctx.fillRect(px + 3, py + 3, Math.max(3, obstacle.width * TILE - 6), 2);
  });
}

function drawQuantumField(time) {
  const centerX = 12 * TILE + 8;
  const centerY = 7 * TILE + 8;
  const shimmer = 0.12 + (Math.sin(time / 350) + 1) * 0.04;
  ctx.save();
  ctx.globalAlpha = shimmer;
  ctx.strokeStyle = currentScene === "river" ? COLORS.sky : COLORS.yellow;
  ctx.lineWidth = 1;
  for (let ring = 0; ring < 3; ring += 1) {
    ctx.beginPath();
    ctx.ellipse(centerX, centerY, 18 + ring * 8, 7 + ring * 4, Math.sin(time / 1400) * .25, 0, Math.PI * 2);
    ctx.stroke();
  }
  worldEngine.TARGETS.filter((target) => target.kind === "shard" && !mission.shards.includes(target.id)).forEach((target, index) => {
    const startX = target.x * TILE + 8;
    const startY = target.y * TILE + 8;
    const travel = (time / 900 + index * .2) % 1;
    const dotX = startX + (centerX - startX) * travel;
    const dotY = startY + (centerY - startY) * travel;
    ctx.fillStyle = index === 0 ? COLORS.sky : index === 1 ? COLORS.yellow : COLORS.pink;
    ctx.fillRect(Math.round(dotX), Math.round(dotY), 2, 2);
  });
  ctx.restore();
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

function animationFrame(character, action, time) {
  const frames = worldEngine.CHARACTER_FRAMES?.[character] || worldEngine.CHARACTER_FRAMES?.player;
  const sequence = frames?.[action] || frames?.idle || [0];
  const cadence = action === "walk" ? 105 : action === "jump" ? 90 : 280;
  return sequence[Math.floor(time / cadence) % sequence.length];
}

function drawHumanSprite(x, y, config, time = 0) {
  const px = x * TILE;
  const action = config.action || "idle";
  const frame = Number.isFinite(config.frame) ? config.frame : animationFrame(config.character, action, time);
  const walking = action === "walk";
  const jumping = action === "jump";
  const jumpProgress = Math.max(0, Math.min(1, config.jumpProgress ?? 0));
  const jumpLift = jumping ? Math.round(Math.sin(jumpProgress * Math.PI) * 7) : 0;
  const idleBob = jumping ? 0 : Math.floor(time / (config.player ? 140 : 260) + x) % 2;
  const py = y * TILE - idleBob - jumpLift;
  const stride = walking ? (frame % 2 === 0 ? 1 : -1) : 0;
  const jumpPose = jumping ? -1 : 0;
  const armSwing = jumping ? -2 : stride;
  const skin = config.skin || "#ffd8ad";
  const hair = config.hair || COLORS.ink;
  ctx.fillStyle = "rgba(3,10,23,.55)";
  ctx.fillRect(px - 2, y * TILE + 21, 20, 4);
  // boots and legs
  ctx.fillStyle = COLORS.ink;
  ctx.fillRect(px + 3 - (jumping ? 1 : 0), py + 17 + stride + jumpPose, 6, 7);
  ctx.fillRect(px + 11 + (jumping ? 1 : 0), py + 17 - stride + jumpPose, 6, 7);
  ctx.fillStyle = config.boots || "#334b76";
  ctx.fillRect(px + 2 - (jumping ? 1 : 0), py + 21 + stride + jumpPose, 7, 4);
  ctx.fillRect(px + 11 + (jumping ? 1 : 0), py + 21 - stride + jumpPose, 7, 4);
  // torso silhouette, jacket, arms
  ctx.fillStyle = COLORS.ink;
  ctx.fillRect(px + 1, py + 8, 18, 12);
  ctx.fillStyle = config.body;
  ctx.fillRect(px + 3, py + 8, 14, 11);
  ctx.fillRect(px - 1, py + 10 + armSwing, 4, 7);
  ctx.fillRect(px + 17, py + 10 - armSwing, 4, 7);
  ctx.fillStyle = config.accent;
  ctx.fillRect(px + 7, py + 9, 6, 3);
  ctx.fillRect(px + 8, py + 12, 4, 6);
  // neck and head outline
  ctx.fillStyle = COLORS.ink;
  ctx.fillRect(px + 5, py - 4, 10, 13);
  ctx.fillStyle = skin;
  ctx.fillRect(px + 6, py - 2, 8, 9);
  // hair shape, with side locks to make silhouettes distinct
  ctx.fillStyle = hair;
  ctx.fillRect(px + 4, py - 5, 12, 4);
  ctx.fillRect(px + 3, py - 2, 3, 7);
  ctx.fillRect(px + 13, py - 2, 3, 5);
  const facingUp = config.facing === "up";
  const facingSide = config.facing === "left" || config.facing === "right";
  ctx.fillStyle = COLORS.paper;
  ctx.fillRect(px + 6, py, 2, 2);
  // Face: a readable JRPG front profile, with a hair-only back profile.
  ctx.fillStyle = COLORS.ink;
  if (facingUp) {
    ctx.fillStyle = hair;
    ctx.fillRect(px + 5, py - 1, 10, 8);
    ctx.fillStyle = config.accent;
    ctx.fillRect(px + 7, py + 5, 6, 2);
  } else {
    const eyeOffset = config.facing === "left" ? -1 : config.facing === "right" ? 1 : 0;
    const blink = action === "idle" && frame % 2 === 1;
    if (blink) {
      ctx.fillRect(px + 7 + eyeOffset, py + 3, 2, 1);
      ctx.fillRect(px + 11 + eyeOffset, py + 3, 2, 1);
    } else {
      ctx.fillRect(px + 7 + eyeOffset, py + 2, 2, 2);
      ctx.fillRect(px + 11 + eyeOffset, py + 2, 2, 2);
    }
    ctx.fillRect(px + 9, py + 4, 2, 1);
    ctx.fillRect(px + 8, py + 6, 5, 1);
    if (!blink) {
      ctx.fillStyle = config.eye || COLORS.sky;
      ctx.fillRect(px + 8 + eyeOffset, py + 2, 1, 1);
      ctx.fillRect(px + 12 + eyeOffset, py + 2, 1, 1);
    }
    if (facingSide) ctx.fillRect(px + (config.facing === "left" ? 4 : 14), py + 3, 2, 3);
  }
  // character accessory
  if (config.accessory === "satchel") {
    ctx.fillStyle = COLORS.sky;
    ctx.fillRect(px + 16, py + 11, 5, 7);
    ctx.fillStyle = COLORS.yellow;
    ctx.fillRect(px + 17, py + 12, 3, 1);
  } else if (config.accessory === "clipboard") {
    ctx.fillStyle = COLORS.yellow;
    ctx.fillRect(px + 17, py + 10, 4, 7);
    ctx.fillStyle = COLORS.paper;
    ctx.fillRect(px + 18, py + 12, 2, 1);
  } else {
    ctx.fillStyle = COLORS.pink;
    ctx.fillRect(px + 3, py + 7, 12, 2);
  }
  if (config.name) label(config.name, x - 1, y - 3, COLORS.paper);
}

function drawPerson(x, y, color, name, time = 0) {
  const mentor = name === "林默";
  drawHumanSprite(x, y, {
    character: mentor ? "mentor" : "xiaoman",
    body: color,
    accent: mentor ? COLORS.yellow : COLORS.sky,
    hair: mentor ? "#e6edf5" : "#f06a7b",
    skin: mentor ? "#e7b18a" : "#f1c39a",
    boots: "#263b5b",
    accessory: mentor ? "clipboard" : "satchel",
    eye: mentor ? COLORS.sky : COLORS.yellow,
    name,
    facing: "down",
    action: "idle",
    frame: animationFrame(mentor ? "mentor" : "xiaoman", "idle", time),
  }, time);
}

function heroineFrame(action, facing, time) {
  const step = Math.floor(time / 105) % 2;
  if (action === "jump") return { col: 3, row: 0 };
  if (action === "walk") {
    if (facing === "left") return { col: 0, row: 1 };
    if (facing === "right") return { col: 1, row: 1 };
    if (facing === "up") return { col: 2, row: 1 };
    return { col: step ? 2 : 1, row: 0 };
  }
  if (facing === "left" || facing === "right") return { col: 3, row: 1 };
  if (facing === "up") return { col: 2, row: 1 };
  return { col: 0, row: 0 };
}

function drawHeroineSprite(x, y, action, facing, time, jumpProgress = 0) {
  if (!heroineSheet.complete || !heroineSheet.naturalWidth) return false;
  const frame = heroineFrame(action, facing, time);
  const lift = action === "jump" ? Math.round(Math.sin(jumpProgress * Math.PI) * 7) : 0;
  const px = x * TILE;
  const py = y * TILE;
  ctx.fillStyle = "rgba(3,10,23,.55)";
  ctx.fillRect(px - 6, py + 22, 28, 4);
  ctx.drawImage(
    heroineSheet,
    frame.col * HEROINE_CELL.width,
    frame.row * HEROINE_CELL.height,
    HEROINE_CELL.width,
    HEROINE_CELL.height,
    px - 10,
    py - 22 - lift,
    36,
    48,
  );
  return true;
}

function drawPlayer(time = 0) {
  const jumpProgress = jumpUntil > jumpStartedAt
    ? Math.max(0, Math.min(1, (time - jumpStartedAt) / (jumpUntil - jumpStartedAt)))
    : 0;
  if (drawHeroineSprite(game.player.x, game.player.y, playerAction, game.player.facing, time, jumpProgress)) return;
  drawHumanSprite(game.player.x, game.player.y, {
    character: "player",
    body: COLORS.player,
    accent: COLORS.yellow,
    hair: "#d46b3c",
    skin: "#f2c08a",
    boots: "#263b5b",
    accessory: "satchel",
    eye: COLORS.sky,
    facing: game.player.facing,
    player: true,
    action: playerAction,
    frame: animationFrame("player", playerAction, time),
    jumpProgress,
  }, time);
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
  const targetCamera = worldEngine.cameraFor(game.player, { width: canvas.width, height: canvas.height }, zoom);
  camera.x += (targetCamera.x - camera.x) * .18;
  camera.y += (targetCamera.y - camera.y) * .18;
  const mapImage = mapImages[currentScene];
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  if (mapImage.complete && mapImage.naturalWidth) drawContain(mapImage);
  else {
    ctx.fillStyle = COLORS.grass;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }
  ctx.setTransform(worldEngine.WORLD_SCALE * zoom, 0, 0, worldEngine.WORLD_SCALE * zoom, -camera.x, -camera.y);
  drawMap(time);
  drawPlayer(time);
  ctx.setTransform(1, 0, 0, 1, 0, 0);
}

function performMove(dx, dy) {
  if (!started || dialogueOpen || $("#pixel-complete").hidden === false) return;
  game = worldEngine.move(game, dx, dy);
}

function triggerJump() {
  if (!started || dialogueOpen || $("#pixel-complete").hidden === false) return;
  const now = performance.now();
  if (now < jumpUntil) return;
  playerAction = "jump";
  jumpStartedAt = now;
  jumpUntil = now + 480;
  toast("调查员跳跃 · 观察路径的高度变化");
}

function collect(id) {
  mission.shards = [...mission.shards, id];
  playEventStinger("shard");
  if (mission.shards.length === 1) setStoryBeat(1);
  if (mission.shards.length === 3) setStoryBeat(2);
  updateHud();
  const lines = {
    state: "状态碎片：先记下系统怎样被准备。",
    repeat: "重复碎片：一次观察只是一条记录，重复才能看见分布。",
    control: "对照碎片：每次只改一个条件，变化才有来源。",
  };
  openDialogue({ speaker: "调查碎片", kicker: `已收集 ${mission.shards.length} / 3`, text: lines[id], afterClose: () => toast(mission.shards.length === 3 ? "三枚碎片齐了 · 去找小满" : "碎片加入调查手册") });
}

async function runWell() {
  setStoryBeat(3);
  openDialogue({ speaker: "量子井", kicker: "正在点亮", text: storyContext().line, locked: true });
  try {
    const response = await fetch("/api/inquiry", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mission: "bell-gates", prediction: "h-opens-branches", conclusion: "h-opens-branches-cx-correlates", shots: 128 }) });
    const passport = await response.json();
    if (!response.ok) throw new Error(passport.error || "井没有返回护照");
    mission.complete = true;
    playEventStinger("success");
    completedNodes = ["observer-zero"];
    await loadStoryWorld();
    $("#pixel-complete-text").textContent = `量子井记录了 ${Object.keys(passport.experiment.control.probabilities).length} 种控制结果和 ${Object.keys(passport.experiment.variant.probabilities).length} 种变体结果。你可以把它们带回 LoomQ 实验室继续复查。`;
    $("#pixel-complete").hidden = false;
    $("#pixel-dialogue").hidden = true;
    dialogueOpen = false;
    updateHud();
  } catch (error) {
    playEventStinger("error");
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
  if (event.event === "mentor") {
    setStoryBeat(1);
    return openDialogue({ speaker: "林默", kicker: storyContext().title, text: storyContext().line });
  }
  if (event.event === "npc") return openDialogue({ speaker: "小满", kicker: storyContext().title, text: storyContext().line, choices: [{ label: "启动量子井，运行一次 A/B", action: runWell }, { label: "我再走走，先不启动", action: closeDialogue }] });
  if (event.event === "gate") return toast("栅门已经打开，量子井在东南角");
}

function update(delta) {
  if (!started || dialogueOpen) return;
  movementClock += delta;
  let dx = touch.x;
  let dy = touch.y;
  if (keys.has("arrowleft") || keys.has("a")) dx -= 1;
  if (keys.has("arrowright") || keys.has("d")) dx += 1;
  if (keys.has("arrowup") || keys.has("w")) dy -= 1;
  if (keys.has("arrowdown") || keys.has("s")) dy += 1;
  const moving = Boolean(dx || dy);
  if (moving && movementClock >= MOVE_INTERVAL) {
    performMove(dx, dy);
    movementClock = 0;
  }
  if (performance.now() >= jumpUntil) playerAction = moving ? "walk" : "idle";
  else playerAction = "jump";
  const nextScene = worldEngine.sceneAt(game.player);
  if (nextScene !== currentScene) {
    currentScene = nextScene;
    setMusicScene(currentScene);
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
  completedNodes = [];
  storyWorld = null;
  storyBeatIndex = 0;
  movementClock = 0;
  playerAction = "idle";
  jumpStartedAt = 0;
  jumpUntil = 0;
  zoom = worldEngine.DEFAULT_ZOOM;
  camera = worldEngine.cameraFor(game.player, { width: canvas.width, height: canvas.height }, zoom);
  dialogueOpen = false;
  dialogueLocked = false;
  $("#pixel-dialogue").hidden = true;
  $("#pixel-complete").hidden = true;
  updateHud();
  toast("像素案件已重置");
  stopMusic();
  canvas.focus();
}

function handleKeydown(event) {
  const key = event.key.toLowerCase();
  if (["arrowleft", "arrowright", "arrowup", "arrowdown", "w", "a", "s", "d", "e", "j", "shift", " "].includes(key)) event.preventDefault();
  if (!started && key === "enter") { $("#pixel-start-button").click(); return; }
  if (dialogueOpen) {
    if ((key === " " || key === "e" || key === "enter") && !dialogueLocked && !$("#pixel-close").hidden) closeDialogue();
    return;
  }
  if (key === "j" || key === "shift") { triggerJump(); return; }
  if (key === "e" || key === " ") interact();
  else {
    const direction = worldEngine.directionForKey(key);
    if (direction && !event.repeat && started) {
      performMove(direction.x, direction.y);
      movementClock = 0;
    }
    keys.add(key);
  }
}
window.addEventListener("keydown", handleKeydown);
window.addEventListener("keyup", (event) => keys.delete(event.key.toLowerCase()));
window.addEventListener("blur", () => keys.clear());

$("#pixel-start-button").addEventListener("click", () => { started = true; $("#pixel-start").hidden = true; setStoryBeat(0); loadStoryWorld(); updateGuide(); startMusic(); canvas.focus(); toast("Atlas-7 轨道站：先找到林默"); });
$("#pixel-close").addEventListener("click", closeDialogue);
$("#pixel-reset").addEventListener("click", reset);
$("#pixel-music-toggle").addEventListener("click", () => {
  if (musicOn) stopMusic();
  else startMusic();
});
$("#pixel-continue").addEventListener("click", () => { $("#pixel-complete").hidden = true; canvas.focus(); });
$("#pixel-touch-action").addEventListener("click", interact);
$("#pixel-touch-jump").addEventListener("click", triggerJump);

function setZoom(nextZoom) {
  zoom = Math.max(worldEngine.MIN_ZOOM, Math.min(worldEngine.MAX_ZOOM, nextZoom));
  updateHud();
}

function pointerDistance() {
  const values = [...pointers.values()];
  if (values.length < 2) return null;
  return Math.hypot(values[0].x - values[1].x, values[0].y - values[1].y);
}

canvas.addEventListener("pointerdown", (event) => {
  pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
  canvas.setPointerCapture(event.pointerId);
  if (pointers.size === 2) {
    pinchStartDistance = pointerDistance();
    pinchStartZoom = zoom;
  }
});
canvas.addEventListener("pointermove", (event) => {
  if (!pointers.has(event.pointerId)) return;
  pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
  if (pointers.size >= 2 && pinchStartDistance) {
    setZoom(pinchStartZoom * (pointerDistance() / pinchStartDistance));
  }
});
function endPointer(event) {
  pointers.delete(event.pointerId);
  if (pointers.size < 2) pinchStartDistance = null;
}
canvas.addEventListener("pointerup", endPointer);
canvas.addEventListener("pointercancel", endPointer);
canvas.addEventListener("wheel", (event) => {
  event.preventDefault();
  setZoom(zoom - Math.sign(event.deltaY) * .08);
}, { passive: false });

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
loadStoryWorld();
requestAnimationFrame(frame);
