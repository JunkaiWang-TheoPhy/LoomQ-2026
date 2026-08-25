(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.EightyYearQuest = api;
})(typeof globalThis === "object" ? globalThis : this, function () {
  "use strict";

  const CASE_ID = "eightieth-year";
  const CHAPTERS = ["arrival", "memory-room", "divergence-probe", "copy-request", "family-hearing", "signature", "return-visit"];
  const CLUES = ["paper-diary", "copy-summary", "daughter-letter"];
  const CHOICES = ["autonomy-first", "dual-signature", "defer"];

  function createState() {
    return {
      schema_version: "loomq-eighty-year-quest-v1",
      quest_id: CASE_ID,
      chapter: "arrival",
      status: "active",
      clues: [],
      evidence: [],
      probe: null,
      decisions: {},
      ending: null,
      unlocks: [],
      consequences: [],
      relationships: { "shen-yao": 0, "young-copy": 0, daughter: 0 },
      return_visits: 0,
    };
  }

  function clone(state) {
    return JSON.parse(JSON.stringify(state));
  }

  function scene(state) {
    const actions = {
      arrival: ["meet-shen-yao"],
      "memory-room": CLUES.filter((clue) => !state.clues.includes(clue)).map((clue) => `collect-${clue}`),
      "divergence-probe": ["run-memory-probe"],
      "copy-request": ["hear-copy-request"],
      "family-hearing": ["hold-family-hearing"],
      signature: CHOICES.map((choice) => `choose-${choice}`),
      "return-visit": ["return-to-care-home"],
    };
    const copy = {
      arrival: ["长日照护院", "沈遥和她的青年副本正在争论：谁有资格解释她现在的生活？"],
      "memory-room": ["三份记忆", "纸质日记、青年副本摘要和女儿的信互相矛盾。"],
      "divergence-probe": ["记忆分歧实验", "只改变一个条件，比较两条记忆线路在哪里第一次分开。"],
      "copy-request": ["副本的请求", "青年副本请求删除一段记忆，并声称这是保护。"],
      "family-hearing": ["家属听证", "女儿需要副本继续照护，沈遥却不愿再被年轻时的自己代表。"],
      signature: ["签名之前", "没有标准答案，只有谁能签字、谁必须被听见。"],
      "return-visit": ["第二天回访", "结案不是离场，回去看看决定如何改变两个人。"],
    };
    return { chapter: state.chapter, title: copy[state.chapter][0], text: copy[state.chapter][1], actions: actions[state.chapter] };
  }

  function availableActions(state) { return scene(state).actions; }

  function transition(source, action, payload = {}) {
    const state = clone(source);
    if (action.startsWith("choose-") && !CHOICES.includes(action.slice(7))) throw new Error(`unknown choice: ${action.slice(7)}`);
    if (!availableActions(state).includes(action)) {
      if (action.startsWith("collect-")) throw new Error("cannot collect memory clue outside memory-room");
      throw new Error(`action unavailable in ${state.chapter}: ${action}`);
    }
    if (action === "meet-shen-yao") {
      state.chapter = "memory-room";
      state.relationships["shen-yao"] += 1;
    } else if (action.startsWith("collect-")) {
      state.clues.push(action.slice(8));
      if (state.clues.length === CLUES.length) state.chapter = "divergence-probe";
    } else if (action === "run-memory-probe") {
      if (payload.first_divergent_gate === undefined || payload.first_divergent_gate === null) throw new Error("probe requires evidence");
      state.probe = { first_divergent_gate: payload.first_divergent_gate, scope: "local-circuit-comparison" };
      state.evidence.push("memory-divergence");
      state.chapter = "copy-request";
    } else if (action === "hear-copy-request") {
      state.relationships["young-copy"] += 1;
      state.chapter = "family-hearing";
    } else if (action === "hold-family-hearing") {
      state.relationships.daughter += 1;
      state.decisions["family-hearing"] = true;
      state.chapter = "signature";
    } else if (action.startsWith("choose-")) {
      const choice = action.slice(7);
      state.ending = choice;
      state.decisions.signature = choice;
      state.chapter = "return-visit";
      if (choice === "autonomy-first") state.consequences.push("copy-autonomy-revoked", "shen-yao-signs-alone");
      if (choice === "dual-signature") state.consequences.push("joint-consent-required", "care-function-retained");
      if (choice === "defer") state.consequences.push("observation-period-opened", "family-must-return");
    } else if (action === "return-to-care-home") {
      state.return_visits += 1;
      state.status = "complete";
      state.evidence.push("memory-dual-signature");
      state.unlocks.push("second-badge");
    }
    return state;
  }

  return { CASE_ID, CHAPTERS, CLUES, CHOICES, createState, scene, availableActions, transition };
});
