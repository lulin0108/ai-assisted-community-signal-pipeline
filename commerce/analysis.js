"use strict";

function analyzeProductScene(query, data) {
  const brief = query.trim().normalize("NFKC");
  const pet = /\b(pets?|dogs?|cats?|pupp(?:y|ies)|kittens?)\b|\u5ba0\u7269|\u732b|\u72d7/i;
  const feeding = /\b(feed\w*|mealtime|meals?|bowls?|fountains?|food mats?)\b|\u5582\u98df|\u5582\u517b|\u996e\u6c34|\u7897|\u9910\u57ab|\u7528\u9910/i;
  const otherMarket = /\b(canada|uk|europe|eu|china|japan|australia|germany|france)\b|\u52a0\u62ff\u5927|\u82f1\u56fd|\u4e2d\u56fd|\u6b27\u6d32|\u65e5\u672c|\u6fb3\u5927\u5229\u4e9a/i;
  if (!pet.test(brief) || !feeding.test(brief) || otherMarket.test(brief)) {
    return {query: brief, covered: false, reason: otherMarket.test(brief) ? "The sample covers the US only." : "The sample covers pet feeding areas."};
  }

  const productsWithFeedback = new Set(data.feedback.map(item => item.product));
  const themes = data.themes.map(theme => {
    const records = data.feedback.filter(item => item.theme === theme.id);
    const support = records.filter(item => item.stance === "support");
    return {...theme, focused: theme.keywords.test(brief), records, supportCount: new Set(support.map(item => item.product)).size};
  });

  const candidates = data.directions.map(direction => {
    const theme = themes.find(item => item.id === direction.theme);
    const direct = data.products.filter(product => direction.features.every(feature => product.features[feature] === true));
    const partial = data.products.filter(product => !direct.includes(product) && direction.features.some(feature => product.features[feature] === true));
    let status = "thin";
    let reason = "The available buyer evidence is absent or does not isolate the specific failure mode.";
    if (direct.length) {
      status = "covered";
      reason = `The sample includes ${direct.length} alternative${direct.length === 1 ? "" : "s"} with all listed features.`;
    } else if (theme.supportCount && direction.researchReason) {
      status = "research";
      reason = direction.researchReason;
    }
    return {...direction, focused: theme.focused, direct, partial, status, reason, evidence: theme.records};
  }).sort((left, right) => Number(right.focused) - Number(left.focused) || left.priority - right.priority);

  return {
    query: brief, covered: true, candidates, themes, feedbackProductCount: productsWithFeedback.size,
    latestFeedback: data.feedback.map(item => item.date).sort().at(-1),
  };
}

if (typeof module !== "undefined") module.exports = {analyzeProductScene};
