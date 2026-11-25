"use strict";

const assert = require("node:assert/strict");
const {test} = require("node:test");
require("../commerce/evidence.js");
const {analyzeProductScene} = require("../commerce/analysis.js");
const data = globalThis.commerceEvidence;

test("the general brief separates leads, covered features, and incomplete evidence", () => {
  const result = analyzeProductScene(data.example, data);
  assert.equal(result.covered, true);
  assert.deepEqual(result.candidates.map(candidate => candidate.status), ["research", "covered", "thin"]);
  assert.equal(result.candidates[0].direct.length, 0);
  assert.equal(result.candidates[1].direct.length, 2);
  assert.equal(result.latestFeedback, "2025-12-24");
});

test("English and Chinese briefs prioritize the relevant direction", () => {
  assert.equal(analyzeProductScene(data.focusExamples[1], data).candidates[0].id, "rim");
  assert.equal(analyzeProductScene("\u5ba0\u7269\u9910\u57ab\u8010\u7528\u5417", data).candidates[0].id, "edge");
  assert.equal(analyzeProductScene("\u8ba9\u5ba0\u7269\u5582\u98df\u533a\u66f4\u6574\u6d01", data).candidates[0].id, "lift");
});

test("unsupported markets and categories return coverage gaps", () => {
  for (const brief of ["", "bathroom storage", "pet food mat for Canada"]) {
    const result = analyzeProductScene(brief, data);
    assert.equal(result.covered, false);
    assert.equal(result.candidates, undefined);
  }
});

test("counts deduplicate product families and keep opposing evidence", () => {
  const result = analyzeProductScene(data.example, data);
  const wear = result.themes.find(theme => theme.id === "wear");
  assert.equal(wear.records.length, 2);
  assert.equal(wear.supportCount, 1);
  assert.equal(result.feedbackProductCount, 2);
  assert.ok(result.candidates[0].evidence.some(record => record.stance === "counter"));
  for (const item of data.feedback) {
    assert.ok(data.products.some(product => product.id === item.product));
    assert.equal(new URL(item.url).protocol, "https:");
  }
});
