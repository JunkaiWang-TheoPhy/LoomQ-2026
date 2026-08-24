(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.AtlasGameEngine = api;
})(typeof globalThis === "object" ? globalThis : this, function () {
  "use strict";

  const CLUES = ["state", "possibility", "repeat", "control"];
  const LOCATIONS = ["observatory", "field", "archive"];

  function createGame() {
    return {
      location: "observatory",
      clues: [],
      prediction: null,
      passport: null,
      audit: null,
      score: 0,
    };
  }

  function briefingComplete(state) {
    return CLUES.every((clue) => state.clues.includes(clue));
  }

  function locationProgress(state) {
    const items = [
      { id: "observatory", state: "current" },
      { id: "field", state: "locked" },
      { id: "archive", state: "locked" },
    ];
    if (briefingComplete(state)) {
      items[0].state = "complete";
      items[1].state = "current";
    }
    if (state.passport) {
      items[1].state = "complete";
      items[2].state = "current";
    }
    if (state.audit) items[2].state = "complete";
    return items;
  }

  function collectClue(state, clue) {
    if (!CLUES.includes(clue)) throw new Error(`未知调查线索：${clue}`);
    if (state.clues.includes(clue)) return state;
    return {
      ...state,
      clues: [...state.clues, clue],
      score: state.score + 5,
    };
  }

  function travel(state, location) {
    if (!LOCATIONS.includes(location)) throw new Error(`未知地点：${location}`);
    const progress = locationProgress(state).find((item) => item.id === location);
    if (progress.state === "locked") throw new Error(`${location} 尚未解锁`);
    return { ...state, location };
  }

  function recordPrediction(state, prediction) {
    if (!briefingComplete(state)) throw new Error("请先完成观测站调查");
    if (!prediction) throw new Error("请先留下预测");
    return {
      ...state,
      prediction,
      score: state.prediction ? state.score : state.score + 10,
    };
  }

  function attachPassport(state, passport) {
    if (
      !passport
      || passport.schema_version !== "loomq-inquiry-passport-v1"
      || typeof passport.conclusion_audits !== "object"
    ) {
      throw new Error("实验护照格式无效");
    }
    return {
      ...state,
      passport,
      audit: null,
      score: (state.passport ? state.score : state.score + 20) - (state.audit ? 50 : 0),
    };
  }

  function auditConclusion(state, conclusion) {
    if (!state.passport) throw new Error("请先取得实验护照");
    const audit = state.passport.conclusion_audits[conclusion];
    if (!audit) throw new Error("实验护照不包含这条结论");
    return {
      ...state,
      audit,
      score: state.audit ? state.score : state.score + 50,
    };
  }

  return {
    CLUES,
    LOCATIONS,
    attachPassport,
    auditConclusion,
    briefingComplete,
    collectClue,
    createGame,
    locationProgress,
    recordPrediction,
    travel,
  };
});
