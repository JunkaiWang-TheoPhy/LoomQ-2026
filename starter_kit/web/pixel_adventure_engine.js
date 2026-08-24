(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.PixelAtlas = api;
})(typeof globalThis === "object" ? globalThis : this, function () {
  "use strict";

  const WIDTH = 24;
  const HEIGHT = 16;
  const SHARDS = ["state", "repeat", "control"];
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
  const SCENES = {
    village: { name: "雾镜镇", range: [0, 8], accent: "#f6dd78" },
    river: { name: "分岔河谷", range: [9, 15], accent: "#78c7d4" },
    archive: { name: "证据塔庭院", range: [16, 23], accent: "#f06a7b" },
  };

  function createPixelGame() {
    return { player: { x: 2, y: 14, facing: "right" } };
  }

  function isWall(x, y) {
    return x < 0 || y < 0 || x >= WIDTH || y >= HEIGHT || MAP[y][x] === "#" || isWater(x, y);
  }

  function isWater(x, y) {
    return x >= 10 && x <= 12 && y !== 7;
  }

  function sceneAt(player) {
    const x = Math.max(0, Math.min(WIDTH - 1, player.x));
    return Object.entries(SCENES).find(([, scene]) => x >= scene.range[0] && x <= scene.range[1])[0];
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

  return { HEIGHT, MAP, SCENES, SHARDS, TARGETS, WIDTH, createPixelGame, interact, isWall, isWater, move, sceneAt };
});
