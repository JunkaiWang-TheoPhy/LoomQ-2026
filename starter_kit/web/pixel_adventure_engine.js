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
  const MOVE_INTERVAL = 0.14;
  const SHARDS = ["state", "repeat", "control"];
  const GUIDE_STEPS = [
    { id: "move", action: "用方向键 / WASD 移动到林默身边" },
    { id: "observe", action: "靠近发光碎片，按 E 进行一次观察" },
    { id: "bridge", action: "沿木桥穿过分岔河谷，去找小满" },
  ];
  const STORY_BEATS = [
    { id: "arrival", title: "失联的量子前哨", line: "Atlas-7 轨道站只发来一句话：不要观测第二条路径。" },
    { id: "fragments", title: "三枚调查碎片", line: "碎片不是燃料，而是三段被删除的实验记录：准备、重复、对照。" },
    { id: "crossing", title: "纠缠能道", line: "河谷中的能道连接两条世界线，木桥是唯一不会强制测量的通路。" },
    { id: "well", title: "量子井回声", line: "小满发现井底还留着一个未知观察者的相位签名。" },
    { id: "choice", title: "谁在观察观察者", line: "A/B 结果一致，却出现了第三个不可见的 witness。" },
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
    village: { name: "量子前哨", range: [0, 8], accent: "#f6dd78", phase: "prepared", background: "/assets/pixel-space-background.png" },
    river: { name: "纠缠能道", range: [9, 15], accent: "#78c7d4", phase: "entangled", background: "/assets/pixel-space-bridge.png" },
    archive: { name: "证据环站", range: [16, 23], accent: "#f06a7b", phase: "audited", background: "/assets/pixel-space-archive.png" },
  };

  function createPixelGame() {
    return { player: { x: 2, y: 14, facing: "right" } };
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

  function cameraFor(player, viewport) {
    const worldWidth = WIDTH * TILE * WORLD_SCALE;
    const worldHeight = HEIGHT * TILE * WORLD_SCALE;
    return {
      x: Math.max(0, Math.min(worldWidth - viewport.width, player.x * TILE * WORLD_SCALE - viewport.width / 2)),
      y: Math.max(0, Math.min(worldHeight - viewport.height, player.y * TILE * WORLD_SCALE - viewport.height / 2)),
    };
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

  return { BUILDINGS, GUIDE_STEPS, HEIGHT, MAP, MOVE_INTERVAL, OBSTACLES, SCENES, SHARDS, STORY_BEATS, TARGETS, TILE, WIDTH, WORLD_SCALE, cameraFor, createPixelGame, interact, isWall, isWater, move, obstacleAt, sceneAt };
});
