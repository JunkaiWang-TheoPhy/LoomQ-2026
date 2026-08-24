(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.LoomQInquiry = api;
})(typeof globalThis === "object" ? globalThis : this, function () {
  "use strict";

  function bars(probabilities) {
    return Object.entries(probabilities || {})
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([state, probability]) => ({
        state,
        probability,
        percent: `${(probability * 100).toFixed(1)}%`,
      }));
  }

  function statesLabel(items) {
    return items.map((item) => item.state).join("、") || "没有可见状态";
  }

  function requestPayload(prediction, conclusion, shots) {
    return {
      mission: "bell-gates",
      prediction,
      conclusion,
      shots,
    };
  }

  function auditHeading(status) {
    if (status === "supported") return "证据支持这条结论";
    if (status === "unsupported") return "证据不支持这条结论";
    return "本次证据不足以判断";
  }

  function withConclusion(passport, conclusion) {
    const audit = passport.conclusion_audits?.[conclusion];
    if (!audit) throw new Error("当前实验护照不包含这条结论的审计结果");
    return {
      ...passport,
      learner: { ...passport.learner, conclusion },
      conclusion_audit: audit,
      replay: {
        ...passport.replay,
        request: { ...passport.replay.request, conclusion },
      },
    };
  }

  function viewModel(passport) {
    const controlBars = bars(passport.experiment.control.probabilities);
    const variantBars = bars(passport.experiment.variant.probabilities);
    const gateNumber = passport.comparison.first_divergent_gate + 1;
    const gate = passport.comparison.reference_operation?.gate || "unknown";
    return {
      controlBars,
      variantBars,
      controlObservation: `主要状态：${statesLabel(controlBars)}。`,
      variantObservation: `禁用 CX 后主要状态变为 ${statesLabel(variantBars)}。`,
      divergence: `g${gateNumber} · ${gate.toUpperCase()}`,
      predictionStatus: passport.prediction_review.status,
      predictionReason: passport.prediction_review.reason,
      auditStatus: passport.conclusion_audit.status,
      auditClaim: passport.conclusion_audit.claim,
      auditReason: passport.conclusion_audit.reason,
      caveat: passport.scope_caveats.join("；"),
    };
  }

  return { auditHeading, bars, requestPayload, withConclusion, viewModel };
});
