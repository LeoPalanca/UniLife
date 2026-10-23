const assert=require('node:assert/strict');
const M=require('../dashboard/ui/mobility.js');
const flows=[
 {sending_code:'IT',sending_country:'Italy',receiving_code:'FR',receiving_country:'France',flow_count:30,gdp_gap_usd_wb:500,receiver_gdp_pc_current_usd_wb:3500,sender_gdp_pc_current_usd_wb:3000},
 {sending_code:'DE',sending_country:'Germany',receiving_code:'IT',receiving_country:'Italy',flow_count:20,gdp_gap_usd_wb:-1000,receiver_gdp_pc_current_usd_wb:3000,sender_gdp_pc_current_usd_wb:4000},
 {sending_code:'FR',sending_country:'France',receiving_code:'IT',receiving_country:'Italy',flow_count:10,gdp_gap_usd_wb:-500,receiver_gdp_pc_current_usd_wb:3000,sender_gdp_pc_current_usd_wb:3500}
];
const snapshot=JSON.stringify(flows),out=M.partners(flows,'IT','outgoing'),incoming=M.partners(flows,'IT','incoming');
assert.equal(out.length,1);assert.equal(out[0].flow_share,1);assert.equal(out[0].receiving_country,'France');
assert.equal(incoming.reduce((n,r)=>n+r.flow_count,0),30);assert.equal(incoming[0].receiving_country,'Germany');assert.equal(incoming[0].partner_gdp,4000);assert.equal(incoming[0].gdp_gap_usd_wb,-1000);assert.equal(incoming[0].actual_receiving_code,'IT');assert.equal(incoming.reduce((n,r)=>n+r.flow_share,0),1);
assert.deepEqual(M.partners(flows,null),[]);assert.deepEqual(M.partners(flows,'XX'),[]);assert.equal(JSON.stringify(flows),snapshot);
const org=[{sending_code:'DE',sending_org:'Universität Alpha',sending_city:'Berlin',receiving_code:'IT',receiving_country:'Italy',receiving_org:'Beta',flow_count:7},{sending_code:'FR',sending_org:'Gamma',receiving_code:'IT',receiving_country:'Italy',receiving_org:'Beta',flow_count:3}];
const filtered=M.endpointRows(org,'IT','incoming',{origin:'universitat',partner:'Germany'},new Map([['DE','Germany'],['FR','France']]));assert.equal(filtered.length,1);assert.equal(filtered[0].flow_count,7);
const agg=M.aggregatePartners(filtered,'IT','incoming',flows);assert.equal(agg[0].receiving_code,'DE');assert.equal(agg[0].flow_share,1);assert.equal(agg[0].gdp_gap_usd_wb,-1000);
const valid=new Set(['IT','DE','FR']);assert.equal(M.readQuery('',valid).country,null);assert.equal(M.readQuery('?country=XX&direction=invalid',valid).country,null);
const expected={country:'IT',direction:'incoming',view:'europe',filters:{origin:'Università & Alpha',destination:'Beta',partner:'DE - Germany'},table:'uniUni',salary:'FR',unit:'pps',query:'x & y'};
assert.deepEqual(M.readQuery('?'+M.query(expected),valid),expected);
assert.equal(M.readQuery('?table=other&unit=other',valid).table,'country');
console.log('PASS: outgoing/incoming arithmetic, original GDP meaning, null selection, endpoint filters, payload immutability and share-link round trips.');
