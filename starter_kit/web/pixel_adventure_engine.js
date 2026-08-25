(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.PixelAtlas = api;
})(typeof globalThis === "object" ? globalThis : this, function () {
  "use strict";

  const WIDTH = 24;
  const HEIGHT = 16;
  const TILE = 16;
  const WORLD_SCALE = 2;
  const DEFAULT_ZOOM = 0.82;
  const MIN_ZOOM = 0.65;
  const MAX_ZOOM = 2.4;
  const MOVE_INTERVAL = 0.14;
  const CHARACTER_FRAMES = {
    player: { idle: [0, 1], walk: [0, 1, 2, 3], jump: [0, 1], left: [0], right: [1], up: [2], down: [3] },
    mentor: { idle: [0, 1], walk: [0, 1, 0, 2], jump: [0, 1], left: [0], right: [1], up: [2], down: [3] },
    xiaoman: { idle: [0, 1], walk: [0, 2, 1, 3], jump: [1, 0], left: [1], right: [0], up: [2], down: [3] },
  };
  const SHARDS = ["state", "repeat", "control"];
  const GUIDE_STEPS = [
    { id: "move", action: "用方向键 / WASD 移动到林默身边" },
    { id: "observe", action: "靠近发光碎片，按 E 进行一次观察" },
    { id: "bridge", action: "沿木桥穿过分岔河谷，去找小满" },
  ];
  const MAP = [
    "########################",
    "#..............#.......#",
    "#..####........#.......#",
    "#..............#..###..#",
    "#..............#.......#",
    "#.......#......####....#",
    "#........................",
    "#........................",
    "#..............####....#",
    "#..............#.......#",
    "#..............#.......#",
    "#..####........#..###..#",
    "#..............#.......#",
    "#..............#.......#",
    "#......................#",
    "########################",
  ];
  const TARGETS = [
    { id: "state", kind: "shard", x: 4, y: 7 },
    { id: "repeat", kind: "shard", x: 8, y: 3 },
    { id: "control", kind: "shard", x: 17, y: 7 },
    { id: "mentor", kind: "mentor", x: 3, y: 13 },
    { id: "npc", kind: "npc", x: 12, y: 7 },
    { id: "gate", kind: "gate", x: 20, y: 7 },
  ];
  const BUILDINGS = [
    { id: "outpost", kind: "outpost", x: 1, y: 1, width: 4, height: 2 },
    { id: "relay", kind: "relay", x: 6, y: 2, width: 2, height: 2 },
    { id: "archive", kind: "archive", x: 18, y: 1, width: 4, height: 3 },
    { id: "well", kind: "well", x: 18, y: 11, width: 3, height: 2 },
  ];
  const OBSTACLES = [
    { id: "outpost-wall", x: 5, y: 3, width: 1, height: 2, kind: "building" },
    { id: "relay-wall", x: 6, y: 4, width: 2, height: 1, kind: "building" },
    { id: "archive-wall", x: 18, y: 4, width: 4, height: 1, kind: "building" },
    { id: "well-wall", x: 18, y: 13, width: 3, height: 1, kind: "building" },
  ];
  const SCENES = {
    village: { name: "量子前哨", range: [0, 8], accent: "#f6dd78", phase: "prepared", background: "/assets/pixel-space-background-v2.png" },
    river: { name: "纠缠能道", range: [9, 15], accent: "#78c7d4", phase: "entangled", background: "/assets/pixel-space-bridge-v2.png" },
    archive: { name: "证据环站", range: [16, 23], accent: "#f06a7b", phase: "audited", background: "/assets/pixel-space-archive-v2.png" },
  };
  const CAPSULE_ZONES = [
    {
      id: "quantum-workbench",
      kind: "workbench",
      label: "量子工作台",
      purpose: "设计、运行和复查一条量子实验",
      bounds: { x: 2, y: 2, width: 9, height: 7 },
      interaction: "experiment",
    },
    {
      id: "quantum-engine",
      kind: "engine",
      label: "量子引擎",
      purpose: "检查能量、稳定性和当前世界状态",
      bounds: { x: 14, y: 1, width: 8, height: 7 },
      interaction: "engine-status",
    },
    {
      id: "rest-area",
      kind: "rest",
      label: "休息区",
      purpose: "休息、保存和回顾调查记录",
      bounds: { x: 14, y: 8, width: 8, height: 7 },
      interaction: "rest",
    },
  ];

  function createPixelGame() {
    return { player: { x: 2, y: 14, facing: "down" } };
  }

  function isWall(x, y) {
    return x < 0 || y < 0 || x >= WIDTH || y >= HEIGHT || MAP[y][x] === "#" || isWater(x, y) || Boolean(obstacleAt(x, y));
  }

  function obstacleAt(x, y) {
    return OBSTACLES.find((obstacle) => (
      x >= obstacle.x && x < obstacle.x + obstacle.width
      && y >= obstacle.y && y < obstacle.y + obstacle.height
    )) || null;
  }

  function isWater(x, y) {
    return x >= 10 && x <= 12 && y !== 7;
  }

  function sceneAt(player) {
    const x = Math.max(0, Math.min(WIDTH - 1, player.x));
    return Object.entries(SCENES).find(([, scene]) => x >= scene.range[0] && x <= scene.range[1])[0];
  }

  function cameraFor(player, viewport, zoom = 1) {
    const safeZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoom));
    const worldWidth = WIDTH * TILE * WORLD_SCALE * safeZoom;
    const worldHeight = HEIGHT * TILE * WORLD_SCALE * safeZoom;
    return {
      x: Math.max(0, Math.min(worldWidth - viewport.width, player.x * TILE * WORLD_SCALE * safeZoom - viewport.width / 2)),
      y: Math.max(0, Math.min(worldHeight - viewport.height, player.y * TILE * WORLD_SCALE * safeZoom - viewport.height / 2)),
    };
  }

  function directionForKey(key) {
    const normalized = String(key || "").toLowerCase();
    const directions = {
      arrowright: { x: 1, y: 0 }, d: { x: 1, y: 0 },
      arrowleft: { x: -1, y: 0 }, a: { x: -1, y: 0 },
      arrowup: { x: 0, y: -1 }, w: { x: 0, y: -1 },
      arrowdown: { x: 0, y: 1 }, s: { x: 0, y: 1 },
    };
    return directions[normalized] || null;
  }

  function move(state, dx, dy) {
    const stepX = Math.sign(dx);
    const stepY = Math.sign(dy);
    if (!stepX && !stepY) return state;
    let x = state.player.x;
    let y = state.player.y;
    if (stepX && !isWall(x + stepX, y)) x += stepX;
    if (stepY && !isWall(x, y + stepY)) y += stepY;
    const facing = Math.abs(stepX) >= Math.abs(stepY)
      ? (stepX > 0 ? "right" : "left")
      : (stepY > 0 ? "down" : "up");
    return { ...state, player: { x, y, facing } };
  }

  function near(player, target) {
    return Math.max(Math.abs(player.x - target.x), Math.abs(player.y - target.y)) <= 1;
  }

  function interact(state, mission) {
    const shards = Array.isArray(mission?.shards) ? mission.shards : [];
    const target = TARGETS.find((item) => near(state.player, item) && !(item.kind === "shard" && shards.includes(item.id)));
    if (!target) return { event: "none" };
    if (target.kind === "shard") return { event: "shard", id: target.id };
    if (target.kind === "npc" && shards.length < SHARDS.length) {
      return { event: "locked", id: "npc", reason: "先收集三枚调查碎片" };
    }
    if (target.kind === "gate" && shards.length < SHARDS.length) {
      return { event: "locked", id: "gate", reason: "东侧门需要完整调查记录" };
    }
    return { event: target.kind, id: target.id };
  }

  return { BUILDINGS, CAPSULE_ZONES, CHARACTER_FRAMES, DEFAULT_ZOOM, GUIDE_STEPS, HEIGHT, MAP, MAX_ZOOM, MIN_ZOOM, MOVE_INTERVAL, OBSTACLES, SCENES, SHARDS, TARGETS, TILE, WIDTH, WORLD_SCALE, cameraFor, createPixelGame, directionForKey, interact, isWall, isWater, move, obstacleAt, sceneAt };
});
