// Run with: node tests/dashboard-presentation.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(`${__dirname}/../scripts/build_dashboard.py`, 'utf8');
const formatters = source.slice(source.indexOf('    function formatCoefficient('), source.indexOf('    function escapeHtml('));
const effects = source.slice(source.indexOf('    function fillBetaEffectCards('), source.indexOf('    function renderCoeffs('));
const value = {}, row = {};
const card = {getAttribute: () => 'Two-stage CITY: Erasmusu rating', querySelector: selector => selector === '.value .v-num' ? value : row};
const context = vm.createContext({document: {querySelectorAll: () => [card]},
  modelCoefficients: [{variable:'Quality of life (Erasmusu rating)',term:'rating_10',beta:0.161,p:0.0004}],
  regressionResults: [{spec:'Two-stage CITY: Erasmusu rating',term:'rating_10',beta:0.793,p:0.00001}],
  escapeHtml: value => value,
});
vm.runInContext(formatters + effects, context);
assert.equal(vm.runInContext('formatCoefficient(-0.000003)', context), '-3.00e-6');
assert.equal(vm.runInContext('formatCoefficient(0)', context), '0.000');
assert.equal(vm.runInContext('formatCoefficient(null)', context), '—');
assert.equal(vm.runInContext('formatP(0.0004)', context), '&lt;0.001');
assert.equal(vm.runInContext('formatP(0.035)', context), '0.035');
assert.equal(vm.runInContext('formatP(null)', context), 'not reported');
vm.runInContext('fillBetaEffectCards()', context);
assert.equal(value.textContent, '+0.793');
assert.ok(row.innerHTML.includes('log-attractiveness units'));
assert.ok(!row.innerHTML.includes('n/a'));
assert.ok(!row.innerHTML.includes('% per'));
console.log('PASS: tiny coefficients, p-values, missing values and correct two-stage card binding.');
