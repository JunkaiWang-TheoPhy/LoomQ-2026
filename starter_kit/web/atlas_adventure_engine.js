(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.AtlasAdventure = api;
})(typeof globalThis === "object" ? globalThis : this, function () {
  "use strict";

  const WORLD = { width: 1920, height: 1080 };
  const PLAYER_RADIUS = 18;
  const SPEED = 250;
  const CLUE_IDS = ["state", "possibility", "repeat", "control"];
  const TARGETS = [
    { id: "mentor", kind: "mentor", x: 250, y: 830, radius: 74 },
    { id: "state", kind: "clue", x: 370, y: 690, radius: 72 },
    { id: "possibility", kind: "clue", x: 490, y: 470, radius: 72 },
    { id: "repeat", kind: "clue", x: 250, y: 285, radius: 72 },
    { id: "control", kind: "clue", x: 485, y: 215, radius: 72 },
    { id: "experiment", kind: "experiment", x: 965, y: 520, radius: 92 },
    { id: "archivist", kind: "archive", x: 1635, y: 490, radius: 92 },
  ];

  const STATIC_BLOCKERS = [
    { x: 72, y: 70, width: 320, height: 138 },
    { x: 700, y: 110, width: 210, height: 185 },
    { x: 1085, y: 740, width: 235, height: 210 },
    { x: 1480, y: 120, width: 300, height: 210 },
    { x: 1510, y: 670, width: 290, height: 220 },
  ];

  function createWorld() {
    return { player: { x: 145, y: 850, facing: "right" } };
  }

  function hasAllClues(mission) {
    const clues = Array.isArray(mission?.clues) ? mission.clues : [];
    return CLUE_IDS.every((id) => clues.includes(id));
  }

  function blockers(mission) {
    const result = [...STATIC_BLOCKERS];
    if (!hasAllClues(mission)) result.push({ x: 625, y: 350, width: 28, height: 385 });
    if (!mission?.passport) result.push({ x: 1325, y: 330, width: 28, height: 410 });
    return result;
  }

  function circleHitsRect(x, y, radius, rect) {
    const nearestX = Math.max(rect.x, Math.min(x, rect.x + rect.width));
    const nearestY = Math.max(rect.y, Math.min(y, rect.y + rect.height));
    return (x - nearestX) ** 2 + (y - nearestY) ** 2 < radius ** 2;
  }

  function isOpen(x, y, mission) {
    if (
      x < PLAYER_RADIUS
      || y < PLAYER_RADIUS
      || x > WORLD.width - PLAYER_RADIUS
      || y > WORLD.height - PLAYER_RADIUS
    ) return false;
    return !blockers(mission).some((rect) => circleHitsRect(x, y, PLAYER_RADIUS, rect));
  }

  function move(state, dx, dy, seconds, mission) {
    const magnitude = Math.hypot(dx, dy);
    if (!magnitude || !Number.isFinite(seconds) || seconds <= 0) return state;
    const travelX = (dx / magnitude) * SPEED * Math.min(seconds, 0.25);
    const travelY = (dy / magnitude) * SPEED * Math.min(seconds, 0.25);
    const steps = Math.max(1, Math.ceil(Math.hypot(travelX, travelY) / 6));
    let x = state.player.x;
    let y = state.player.y;
    for (let index = 0; index < steps; index += 1) {
      const nextX = x + travelX / steps;
      const nextY = y + travelY / steps;
      if (isOpen(nextX, y, mission)) x = nextX;
      if (isOpen(x, nextY, mission)) y = nextY;
    }
    const facing = Math.abs(dx) > Math.abs(dy)
      ? (dx > 0 ? "right" : "left")
      : (dy > 0 ? "down" : "up");
    return { ...state, player: { x, y, facing } };
  }

  function distanceTo(player, target) {
    return Math.hypot(player.x - target.x, player.y - target.y);
  }

  function nearestTarget(state, mission) {
    return TARGETS
      .filter((target) => !(target.kind === "clue" && mission?.clues?.includes(target.id)))
      .map((target) => ({ ...target, distance: distanceTo(state.player, target) }))
      .filter((target) => target.distance <= target.radius)
      .sort((a, b) => a.distance - b.distance)[0] || null;
  }

  function interact(state, mission) {
    const target = nearestTarget(state, mission);
    if (!target) return { event: "none" };
    if (target.kind === "clue") return { event: "clue", id: target.id };
    if (target.kind === "experiment" && !hasAllClues(mission)) {
      return { event: "locked", id: "experiment", reason: "先找齐四条调查方法" };
    }
    if (target.kind === "archive" && !mission?.passport) {
      return { event: "locked", id: "archive", reason: "证据塔只接受实验护照" };
    }
    return { event: target.kind, id: target.id };
  }

  function regionAt(x) {
    if (x < 650) return "雾镜观测站";
    if (x < 1350) return "分岔原野";
    return "证据塔庭院";
  }

  return {
    CLUE_IDS,
    PLAYER_RADIUS,
    SPEED,
    STATIC_BLOCKERS,
    TARGETS,
    WORLD,
    blockers,
    createWorld,
    hasAllClues,
    interact,
    move,
    nearestTarget,
    regionAt,
  };
});
