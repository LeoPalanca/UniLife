/* Country, direction, local filters and URL state have one owner. */
const NAV_GROUPS = [
  {id:'research',label:'Research',topics:[['sec-intro','The question & model'],['sec-explanatory','Variables'],['sec-results','Findings'],['sec-salary','GDP & prosperity'],['sec-reddit','Quality of life'],['sec-institution','Institutions'],['sec-panel','Panel evidence'],['sec-covid','The 2020 shock']]},
  {id:'explore',label:'Explore mobility',topics:[['sec-europe','Europe overview'],['sec-heatmap','Network heatmap'],['sec-explore','Choose a country'],['sec-overview','Country overview'],['sec-flow-filters','Refine exploration'],['sec-map','University map'],['sec-trends','Historical trends'],['sec-top-destinations','Top partners'],['sec-destination-table','Flow table'],['sec-gdp-gap','GDP gap & mobility'],['sec-earnings','Salary reference']]},
  {id:'methods',label:'Data & methods',topics:[['sec-economics','Economic comparisons'],['sec-data','Sources & coverage']]}
];
const COUNTRY_SECTIONS = new Set([...document.querySelectorAll('[data-country-section]')].map(x=>x.id));
const NAV_TOPIC = new Map(NAV_GROUPS.flatMap(g=>g.topics.map(([id,label])=>[id,{group:g.id,label}])));
const endpointCountryNames=new Map(countryNames);
for(const row of orgFlowTables.uniUni || [])if(row.receiving_code&&row.receiving_country)endpointCountryNames.set(row.receiving_code,row.receiving_country);
const regionNames=typeof Intl.DisplayNames==='function'?new Intl.DisplayNames(['en'],{type:'region'}):null;
for(const row of orgFlowTables.uniUni || [])if(row.sending_code&&!endpointCountryNames.has(row.sending_code)){let name=row.sending_code;try{name=regionNames?.of(row.sending_code)||name}catch{}endpointCountryNames.set(row.sending_code,name)}
let activeSection = 'welcome', pendingSection = null, salaryFollow = !viewState.salary;
let scrollTimer, filterTimer, scrollFrame = false;
const viewName = () => countryNames.get(viewState.country) || 'Choose a country';
const directionName = () => viewState.direction === 'incoming' ? 'Incoming' : 'Outgoing';
const hasEndpointFilters = () => Object.values(viewState.filters).some(Boolean);
const detailHtml = entries => `<button type="button" class="row-details-toggle" data-detail="${escapeHtml(JSON.stringify(entries))}" aria-expanded="false">Details</button>`;
function explorationOrgRows() {
  return Mobility.endpointRows(orgFlowTables.uniUni || [],viewState.country,viewState.direction,viewState.filters,endpointCountryNames);
}
function currentOrgRows() {
  const source = explorationOrgRows(), level = orgLevelSelect.value, groups = new Map();
  for (const row of source) {
    const fields = level === 'countryUni' ? ['sending_code','receiving_code','receiving_org','receiving_city'] : level === 'uniCountry' ? ['sending_code','sending_org','sending_city','receiving_code'] : ['sending_code','sending_org','sending_city','receiving_code','receiving_org','receiving_city'];
    const key = JSON.stringify(fields.map(f=>row[f] || ''));
    if (!groups.has(key)) groups.set(key,{...row,...(level==='countryUni'?{sending_org:'',sending_city:''}:level==='uniCountry'?{receiving_org:'',receiving_city:''}:{}),flow_count:0});
    groups.get(key).flow_count += row.flow_count;
  }
  return [...groups.values()].sort((a,b)=>b.flow_count-a.flow_count);
}
function populateOrgOptions() {
  const rows = Mobility.endpointRows(orgFlowTables.uniUni || [],viewState.country,viewState.direction,{origin:'',destination:'',partner:''},endpointCountryNames);
  const lists = [new Set(),new Set(),new Set()];
  rows.forEach(r=>{
    [r.sending_org,r.sending_city].filter(Boolean).forEach(x=>lists[0].add(x));
    lists[1].add(viewState.direction === 'incoming' ? `${r.sending_code} - ${r.sending_country}` : `${r.receiving_code} - ${r.receiving_country}`);
    [r.receiving_org,r.receiving_city].filter(Boolean).forEach(x=>lists[2].add(x));
  });
  [outUniOptions,inCountryOptions,inUniOptions].forEach((el,i)=>{el.innerHTML=[...lists[i]].sort((a,b)=>a.localeCompare(b)).slice(0,1800).map(x=>`<option value="${escapeHtml(x)}"></option>`).join('')});
}
function updateFilterChip() {
  const items = [['Origin',viewState.filters.origin],['Partner',viewState.filters.partner],['Destination',viewState.filters.destination]].filter(x=>x[1]);
  const chip = document.getElementById('flowFilterChip');chip.style.display=items.length?'':'none';
  chip.querySelector('.fc-active').textContent=items.map(([k,v])=>`${k}: ${v}`).join(' · ');
}
function clearIncompatibleFilters() {
  const all = Mobility.endpointRows(orgFlowTables.uniUni || [],viewState.country,viewState.direction,{origin:'',destination:'',partner:''},endpointCountryNames);
  const cleared=[];
  for(const key of ['origin','destination','partner']) {
    if (viewState.filters[key] && !all.some(r=>Mobility.matches(r,{[key]:viewState.filters[key]},viewState.direction))) {viewState.filters[key]='';cleared.push(key)}
  }
  document.getElementById('filterResetNote').textContent=cleared.length?'Filters unavailable for this selection were cleared. Compatible filters were kept.':'';
}
function setCountry(code,{history=true,clean=true}={}) {
  viewState.country=countryNames.has(code)?code:null;
  if(clean) clearIncompatibleFilters();
  salaryFollow=true;viewState.salary=null;
  renderExplorer();
  if(history) saveView(true);
  if(pendingSection && viewState.country) {const next=pendingSection;pendingSection=null;goToSection(next)}
}
function renderSummary(rows) {
  if(!viewState.country) return;
  const stats=SENDER_STATS.get(viewState.country) || {}, count=rows.reduce((n,r)=>n+r.flow_count,0);
  const metric=(label,value,formatter=fmtInt)=>`<div class="card"><div class="label">${escapeHtml(label)}</div><div class="value">${formatter(value)}</div></div>`;
  const scope=hasEndpointFilters()?'Filtered university records · current direction':'National flow sample · current direction';
  const selected=metric(`${directionName()} students`,count)+metric('Partner countries',rows.length);
  const national=metric('National outgoing',stats.outgoing || 0)+metric('National incoming',stats.incoming || 0)+metric('Net outgoing − incoming',stats.net || 0,v=>`${v>0?'+':v<0?'−':''}${fmtInt(Math.abs(v))}`)+metric('Destinations reached',stats.destinations || 0);
  const weighted=(key)=>{const available=rows.filter(r=>Number.isFinite(r[key]));const denom=available.reduce((n,r)=>n+r.flow_count,0);return denom?available.reduce((n,r)=>n+r[key]*r.flow_count,0)/denom:null};
  const gaps=metric('Mean GDP gap · USD',weighted('gdp_gap_usd_wb'),v=>v==null?'—':`${v>0?'+':''}${fmtMoney(v)}`)+metric('Mean earnings gap · EUR',weighted('earnings_gap'),v=>v==null?'—':`${v>0?'+':''}${fmtMoney(v)}`)+metric('Mean price-level gap',weighted('price_level_gap'),v=>v==null?'—':`${v>0?'+':''}${fmtOne(v)}`);
  const grants=metric('National HE grant budget · EUR',stats.grants,v=>v==null?'—':fmtMoney(v))+metric('Grant per estimated participant · EUR',stats.grantPerEstimated,v=>v==null?'—':fmtMoney(v));
  document.getElementById('summaryCards').innerHTML=`<div class="summary-stack">
    <div class="summary-group"><div class="grp-head"><span class="grp-name">${directionName()} ${viewState.direction==='incoming'?'to':'from'} ${escapeHtml(viewName())}</span><span class="grp-hint">${scope}</span></div><div class="cards">${selected}</div></div>
    <div class="summary-group"><div class="grp-head"><span class="grp-name">National context</span><span class="grp-hint">${escapeHtml(viewName())} · KA1 2022 · all universities, both directions</span></div><div class="country-context-metrics">${national}</div><details><summary>National partner rankings</summary><div class="cards"><div class="card"><div class="label">Largest outgoing partners</div>${renderTopList(stats.topOut,'No outgoing flows.')}</div><div class="card"><div class="label">Largest incoming partners</div>${renderTopList(stats.topIn,'No incoming flows.')}</div></div></details></div>
    <div class="summary-group"><div class="grp-head"><span class="grp-name">Economic gaps</span><span class="grp-hint">Flow-weighted destination minus origin · ${scope.toLowerCase()}</span></div><div class="cards">${gaps}</div><p class="grp-foot">Gaps always describe destination minus origin, including in the incoming view. Each mean excludes partners without that indicator.</p></div>
    <div class="summary-group"><div class="grp-head"><span class="grp-name">Grants</span><span class="grp-hint">National budget · university and partner filters do not apply</span></div><div class="cards">${grants}</div><p class="grp-foot">National budgets reflect country size. Grant per estimated participant is a programme proxy, not an individual award.</p></div></div>`;
}
function renderDestinationTable(rows) {
  const sorted=sortRows(rows,destinationSort), incoming=viewState.direction==='incoming';
  const body=sorted.map(r=>`<tr><td class="country-name">${escapeHtml(r.receiving_country)} <span class="note">${escapeHtml(r.receiving_code)}</span></td><td>${fmtInt(r.flow_count)}</td><td>${fmtPct(r.flow_share)}</td><td>${detailHtml([['Partner GDP per capita · USD',fmtMoney(r.partner_gdp ?? (incoming?r.sender_gdp_pc_current_usd_wb:r.receiver_gdp_pc_current_usd_wb))],['Destination − origin GDP gap · USD',fmtMoney(r.gdp_gap_usd_wb)],['Price-level gap',fmtOne(r.price_level_gap)],['Earnings gap · EUR',fmtMoney(r.earnings_gap)]])}</td></tr>`).join('');
  document.getElementById('destinationTable').innerHTML=rows.length?`<table class="data-table"><thead><tr>${sortableHeader(incoming?'Origin':'Destination','receiving_country','destination')}${sortableHeader('Students','flow_count','destination')}${sortableHeader('Share','flow_share','destination')}<th>Economics</th></tr></thead><tbody>${body}</tbody></table>`:'<p class="exploration-empty">No flows match this selection. Clear the exploration filters or choose another country.</p>';
}
function renderOrgFlowTable() {
  const rows=currentOrgRows();
  document.getElementById('orgFlowNote').textContent=`${fmtInt(rows.length)} university-flow rows · ${directionName().toLowerCase()} ${viewState.direction==='incoming'?'to':'from'} ${viewName()} · university-record sample, with active endpoint filters.`;
  document.getElementById('orgFlowTable').innerHTML=rows.length?`<table class="data-table"><thead><tr><th>Origin</th><th>Destination</th><th>Students</th><th>Universities</th></tr></thead><tbody>${rows.map(r=>`<tr><td class="country-name">${escapeHtml(endpointCountryNames.get(r.sending_code)||r.sending_code)}</td><td class="country-name">${escapeHtml(r.receiving_country)}</td><td style="text-align:right">${fmtInt(r.flow_count)}</td><td>${detailHtml([['Origin city',r.sending_city||'Not part of this aggregation'],['Origin university',r.sending_org||'Not part of this aggregation'],['Destination city',r.receiving_city||'Not part of this aggregation'],['Destination university',r.receiving_org||'Not part of this aggregation']])}</td></tr>`).join('')}</tbody></table>`:'<p class="exploration-empty">No university flows match. Try a broader partner or university filter.</p>';
  applyTableSearch();
}
function renderWeightedTable() {
  const rows=sortRows(weightedRows,weightedSort);
  document.getElementById('weightedTable').innerHTML=`<table class="data-table"><thead><tr>${sortableHeader('Country','sender','weighted')}${sortableHeader('Outgoing','outgoing','weighted')}${sortableHeader('Mean destination GDP · USD','weighted_gdp_pc_usd','weighted')}<th>Details</th></tr></thead><tbody>${rows.map(r=>`<tr><td class="country-name">${escapeHtml(countryNames.get(r.code)||r.sender)}</td><td>${fmtInt(r.outgoing)}</td><td>${fmtMoney(r.weighted_gdp_pc_usd)}</td><td>${detailHtml([['Mean destination price level',fmtOne(r.weighted_price_level)],['Mean destination earnings · EUR',fmtMoney(r.weighted_net_earnings_eur)],['Grant / estimated participant · EUR',fmtMoney(r.grant_per_estimated_participant_eur)],['Grant / actual participant · EUR',fmtMoney(r.grant_per_actual_participant_eur)]])}</td></tr>`).join('')}</tbody></table>`;
}
function renderRedditTable() {
  const all=sortRows(redditByCountry.filter(r=>r.mentions>=REDDIT_MIN_MENTIONS),redditSort), rows=redditExpanded?all:all.slice(0,REDDIT_TOP_N);
  document.getElementById('redditTable').innerHTML=`<p class="scope-note">All destination countries with at least ${REDDIT_MIN_MENTIONS} mentions · supporting text evidence, independent of the selected country.</p><table class="data-table"><thead><tr>${sortableHeader('Destination','country','reddit')}${sortableHeader('Mentions','mentions','reddit')}${sortableHeader('Net sentiment','net','reddit')}<th>Details</th></tr></thead><tbody>${rows.map(r=>`<tr><td class="country-name">${escapeHtml(r.country)}</td><td>${fmtInt(r.mentions)}</td><td>${netBadge(r.net)}</td><td>${detailHtml([['Score-weighted net sentiment',r.weightedNet == null ? 'Not available' : Number(r.weightedNet).toFixed(2)],['Positive / neutral / negative',`${r.positive} / ${r.neutral} / ${r.negative}`],['Average Reddit score',fmtOne(r.avgScore)],['Positive themes',r.positiveThemes],['Negative themes',r.negativeThemes],['All themes',r.themes]])}</td></tr>`).join('')}</tbody></table>${all.length>REDDIT_TOP_N?`<button class="button-action reddit-more" type="button" id="redditMore">${redditExpanded?'Show fewer':`Show all ${all.length} countries`}</button>`:''}`;
  document.getElementById('redditMore')?.addEventListener('click',()=>{redditExpanded=!redditExpanded;renderRedditTable()});
}
// Reuse the known receiving-endpoint coordinates for origin institutions when available.
const endpointCoordinates=(()=>{
  const organizations=new Map(), cities=new Map(), centroids=new Map();
  for(const p of orgFlowLevels.countryUni?.all || []) {const country=norm(p.n);if(p.m==='city'){organizations.set(`${country}|${norm(p.o)}`,p);cities.set(`${country}|${norm(p.c)}`,p)}}
  for(const p of orgFlowLevels.uniCountry?.all || []) if(p.dc) centroids.set(p.dc,p);
  return {organizations,cities,centroids};
})();
function explorationMapPoints() {
  const incoming=viewState.direction==='incoming', points=new Map();
  for(const row of explorationOrgRows()) {
    const code=incoming?row.sending_code:row.receiving_code, country=endpointCountryNames.get(code)||code;
    const organization=incoming?row.sending_org:row.receiving_org, city=incoming?row.sending_city:row.receiving_city;
    const coord=endpointCoordinates.organizations.get(`${norm(country)}|${norm(organization)}`)||endpointCoordinates.cities.get(`${norm(country)}|${norm(city)}`)||endpointCoordinates.centroids.get(code);
    if(!coord) continue;
    const key=JSON.stringify([code,organization,city]);
    if(!points.has(key)) points.set(key,{o:organization,c:city,n:country,la:coord.la,lo:coord.lo,m:coord.m,f:0});
    points.get(key).f+=row.flow_count;
  }
  return [...points.values()];
}
function renderMap() {
  if(!map) return;
  clusterLayer.clearLayers();
  if(!viewState.country) return;
  const points=explorationMapPoints(), empty=!points.length;
  document.getElementById('mapEmpty').hidden=!empty;document.getElementById('map').hidden=empty;document.querySelector('#sec-map .map-legend').hidden=empty;
  if(empty) return;
  map.invalidateSize();
  const max=Math.max(1,...points.map(p=>p.f)), markers=[],bounds=[];
  points.forEach(p=>{
    const fallback=p.m!=='city',color=fallback?'#b44e5a':'#2f6f73';
    const marker=L.circleMarker([p.la,p.lo],{radius:4+16*Math.sqrt(p.f/max),color,weight:1,fillColor:color,fillOpacity:.55,flow:p.f});
    marker.bindPopup(`<strong>${escapeHtml(p.o||p.n)}</strong><br>${escapeHtml(p.c)}, ${escapeHtml(p.n)}<br>${fmtInt(p.f)} students${fallback?'<br>Approximate country-centroid position':''}`);
    marker.bindTooltip(`${escapeHtml(p.o||p.n)}: ${fmtInt(p.f)}`);markers.push(marker);bounds.push([p.la,p.lo]);
  });
  clusterLayer.addLayers(markers);map.fitBounds(bounds,{padding:[26,26],maxZoom:7,animate:false});
  document.getElementById('mapNote').textContent=`${viewState.direction==='incoming'?'Origin':'Destination'} institutions, sized by students in the filtered university records. Teal: known city coordinate; coral: approximate country centroid. Institutions without any coordinate are not plotted.`;
}
function renderTrendSender(code) {
  const incoming=viewState.direction==='incoming', byCountry=timeSeries.filter(r=>r[incoming?'d':'s']===code), el=document.getElementById('trendSender');
  document.getElementById('trendSenderTitle').textContent=`${viewName()} · ${incoming?'origins':'destinations'}`;
  if(!byCountry.length){el.innerHTML='<p class="exploration-empty">No historical panel is available for this country. The national 2022 sample may still contain flows.</p>';return}
  const totals=new Map();byCountry.forEach(r=>{const p=incoming?r.s:r.d;totals.set(p,(totals.get(p)||0)+r.f)});
  const series=[...totals].sort((a,b)=>b[1]-a[1]).slice(0,5).map(([code],i)=>({label:countryNames.get(code)||code,color:TREND_COLORS[i],points:trendYears.map(y=>({x:y,y:byCountry.filter(r=>r.y===y&&r[incoming?'s':'d']===code).reduce((n,r)=>n+r.f,0)}))}));
  el.innerHTML=lineChartSvg(series,trendYears)+legendHtml(series);
}
function renderEurope() {
  const total=flows.reduce((n,r)=>n+r.flow_count,0), participating=new Set(flows.flatMap(r=>[r.sending_code,r.receiving_code]).filter(Boolean)).size;
  document.getElementById('europeMetrics').innerHTML=[['Study mobilities',fmtInt(total)],['Countries with coded coverage',fmtInt(participating)],['Country-to-country links',fmtInt(flows.length)]].map(([label,value])=>`<div class="card"><div class="label">${label}</div><div class="value">${value}</div></div>`).join('');
  const uncoded=flows.filter(r=>!r.sending_code||!r.receiving_code).reduce((n,r)=>n+r.flow_count,0);
  document.getElementById('europeCoverage').textContent=uncoded?`${fmtInt(uncoded)} mobilities without a complete country code remain in the total. Country selection and counts use coded participants.`:'';
  for(const [id,key] of [['europeOutgoing','outgoing'],['europeIncoming','incoming']]) {
    document.getElementById(id).innerHTML=[...countries].sort((a,b)=>b[key]-a[key]).slice(0,8).map(c=>`<li><button type="button" class="europe-country-link" data-country="${c.code}" data-direction="${key}">${escapeHtml(c.country)}</button><span>${fmtInt(c[key])}</span></li>`).join('');
  }
}
function setScope(id,text) {
  const section=document.getElementById(id);if(!section) return;
  let line=section.querySelector(':scope > .scope-note, :scope > details > .scope-note');
  if(!line){line=document.createElement('p');line.className='scope-note';const details=section.querySelector(':scope > details');if(details){details.querySelector('summary').after(line)}else section.querySelector('h2').after(line)}
  line.textContent=text;
}
function updateScopes() {
  const country=viewName(), dir=directionName(), where=viewState.direction==='incoming'?'to':'from';
  const filter=hasEndpointFilters()?' · filtered university records':' · national flow sample';
  for(const id of ['sec-overview','sec-top-destinations','sec-destination-table','sec-gdp-gap']) setScope(id,`${dir} ${where} ${country} · KA1 2022${filter}`);
  setScope('sec-map',`${dir} ${where} ${country} · separate university-record sample${hasEndpointFilters()?' · filters active':''}`);
  setScope('sec-flow-filters',`${dir} ${where} ${country} · university filters apply to compatible exploration views`);
  setScope('sec-trends',`${dir} ${where} ${country} · national historical panel, 2014–2023 · university filters do not apply`);
  for(const id of ['sec-intro','sec-explanatory','sec-results','sec-salary','sec-reddit','sec-institution','sec-panel','sec-covid']) setScope(id,`Research evidence · all countries in the reported estimation sample`);
  setScope('sec-economics','All sending countries · national economic comparisons · independent of the selected country');
  document.getElementById('exploreScope').textContent=viewState.country?`${dir} ${where} ${country}`:'Choose a country to start.';
  updateCountryFeedback();
}
function updateCountryFeedback() {
  const group=NAV_TOPIC.get(activeSection)?.group;
  const globalView=['sec-europe','sec-heatmap'].includes(activeSection);
  let text='Choose a country to explore its mobility.';
  if(globalView) text='Europe overview covers all participating countries. Choose a country for its profile.';
  else if(viewState.country&&(group==='research'||group==='methods'))text=`${viewName()} selected for exploration. This section uses its full research/data sample.`;
  else if(viewState.country)text=`${directionName()} ${viewState.direction==='incoming'?'to':'from'} ${viewName()}.`;
  document.getElementById('countryFeedback').textContent=text;
}
function renderSalaryReference() {
  const target=salaryFollow?viewState.country:viewState.salary, supported=new Set(sectorEarnings.map(r=>r.code));
  earnCountrySelect.value=supported.has(target)?target:'';
  earnUnitSelect.value=viewState.unit;
  document.getElementById('salaryScope').textContent=target?`${countryNames.get(target)||target} · Structure of Earnings Survey 2018 · ${salaryFollow?'follows selected country':'local comparison override'}`:'Country-specific salary reference · 2018';
  document.getElementById('salaryState').textContent=target&&!supported.has(target)?`Salary data is unavailable for ${countryNames.get(target)||target}. Choose an available country below for an explicit local comparison.`:salaryFollow?'Following the selected country. This is a national reference; university filters do not apply.':'Local comparison: the main country selection is unchanged.';
  document.getElementById('followSalary').hidden=salaryFollow;
  if(!supported.has(target)) document.getElementById('earningsChart').innerHTML='<p class="exploration-empty">No salary observations for the selected country in this dataset. Available alternatives are listed in the salary-country selector.</p>';
  else renderEarnings();
}
function applyTableSearch() {
  for(const id of ['destinationTable','orgFlowTable']) document.querySelectorAll(`#${id} tbody tr:not(.expanded-table-row)`).forEach(tr=>{tr.hidden=!!viewState.query&&!norm(tr.textContent+' '+(tr.querySelector('[data-detail]')?.dataset.detail||'')).includes(norm(viewState.query));if(tr.nextElementSibling?.classList.contains('expanded-table-row'))tr.nextElementSibling.hidden=tr.hidden||tr.querySelector('[data-detail]')?.getAttribute('aria-expanded')!=='true'});
}
function applyTableView() {
  const university=viewState.table!=='country';
  orgLevelSelect.value=university?viewState.table:'countryUni';
  for(const b of document.querySelectorAll('.seg-btn[data-view]')) {const active=b.dataset.view===viewState.table;b.classList.toggle('on',active);b.setAttribute('aria-selected',String(active))}
  document.getElementById('destinationTable').style.display=university?'none':'';
  document.getElementById('orgFlowTable').style.display=university?'':'none';
  document.getElementById('orgFlowNote').style.display=university?'':'none';
}
function updateCountry() {renderExplorer()}
function renderExplorer() {
  senderSelect.value=viewState.country||'';
  outUniSearch.value=viewState.filters.origin;inCountrySearch.value=viewState.filters.partner;inUniSearch.value=viewState.filters.destination;
  document.getElementById('destTableFilter').value=viewState.query;
  document.getElementById('sidebarDirection').hidden=!viewState.country;
  document.getElementById('countryPrompt').hidden=!!viewState.country;document.getElementById('exploreToolbar').hidden=!viewState.country;
  document.querySelectorAll('[data-country-section]').forEach(x=>{x.hidden=!viewState.country});
  document.querySelectorAll('[data-direction]').forEach(x=>{if(x.tagName==='BUTTON'&&!x.dataset.country)x.setAttribute('aria-pressed',String(x.dataset.direction===viewState.direction))});
  document.getElementById('topStat').textContent='KA1 study mobility · research and country exploration';
  updateScopes();updateFilterChip();populateOrgOptions();applyTableView();
  if(viewState.country) {
    const rows=senderRowsFiltered(viewState.country),total=rows.reduce((n,r)=>n+r.flow_count,0);
    renderSummary(rows);renderBar(rows);renderScatter(rows);renderDestinationTable(rows);renderOrgFlowTable();renderTrendSender(viewState.country);renderMap();
    document.getElementById('exploreStatus').textContent=`${fmtInt(total)} ${viewState.direction} students · ${rows.length} partner countries${hasEndpointFilters()?' · filtered university records; national context and historical panel remain unfiltered':''}`;
    renderSalaryReference();applyTableSearch();
    document.querySelector('#sec-top-destinations h2').textContent=viewState.direction==='incoming'?'Top origins':'Top destinations';
  } else document.getElementById('exploreStatus').textContent='';
}
function navGroup(group) {
  document.querySelectorAll('[data-navgroup]').forEach(b=>{const active=b.dataset.navgroup===group;b.setAttribute('aria-expanded',String(active));document.getElementById(`topics-${b.dataset.navgroup}`).hidden=!active});
}
function markNavigation(id) {
  if(id===activeSection && document.querySelector('#sidebarNav a.active')) return;
  activeSection=id;const topic=NAV_TOPIC.get(id);updateCountryFeedback();
  document.querySelectorAll('#sidebarNav a').forEach(a=>{const active=a.getAttribute('href')==='#'+id;a.classList.toggle('active',active);if(active)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current')});
  if(topic) navGroup(topic.group);
}
function saveView(push=false) {
  if(!explorerReady) return;
  const query=Mobility.query(viewState),hash=activeSection==='welcome'?'':`#${activeSection}`;
  const url=location.pathname+(query?'?'+query:'')+hash;
  if(url!==location.pathname+location.search+location.hash) history[push?'pushState':'replaceState'](null,'',url);
}
function setDrawer(open,{focus=true}={}) {
  const narrow=innerWidth<1024;open=!!open&&narrow;
  document.body.classList.toggle('drawer-open',open);
  const aside=document.getElementById('siteSidebar');aside.inert=narrow&&!open;
  document.getElementById('drawerToggle').setAttribute('aria-expanded',String(open));
  if(open){aside.setAttribute('role','dialog');aside.setAttribute('aria-modal','true');if(focus)document.getElementById('drawerClose').focus()}
  else {aside.removeAttribute('role');aside.removeAttribute('aria-modal')}
  for(const el of document.querySelectorAll('main,.pagehead,footer')) el.inert=open;
}
function goToSection(id,{push=true}={}) {
  if(id==='sec-controls') id='sec-explanatory';
  if(COUNTRY_SECTIONS.has(id)&&!viewState.country){pendingSection=id;id='sec-explore'}
  const target=document.getElementById(id);if(!target)return;
  if(['sec-europe','sec-heatmap'].includes(id))viewState.view='europe';else if(COUNTRY_SECTIONS.has(id)||id==='sec-explore')viewState.view='country';
  const disclosure=target.querySelector(':scope > details');if(disclosure)disclosure.open=true;
  setDrawer(false,{focus:false});markNavigation(id);saveView(push);
  if(id==='welcome') window.scrollTo({top:0,behavior:'instant'});
  else target.scrollIntoView({behavior:'instant',block:'start'});
  if(id==='sec-map'&&map){map.invalidateSize()}
}
function restoreView() {
  Object.assign(viewState,Mobility.readQuery(location.search,new Set(countryNames.keys())));salaryFollow=!viewState.salary;
  renderExplorer();goToSection(location.hash.slice(1)||(viewState.view==='europe'?'sec-europe':'welcome'),{push:false});
}
function initializeExplorer() {
  senderSelect.innerHTML='<option value="">Choose a country…</option>'+[...countries].sort((a,b)=>a.country.localeCompare(b.country)).map(c=>`<option value="${c.code}">${escapeHtml(c.country)}</option>`).join('');
  document.getElementById('sidebarNav').innerHTML=NAV_GROUPS.map(g=>`<div class="nav-section"><button type="button" class="nav-group" data-navgroup="${g.id}" aria-expanded="${g.id==='research'}" aria-controls="topics-${g.id}">${g.label}</button><div class="nav-topics" id="topics-${g.id}"${g.id==='research'?'':' hidden'}>${g.topics.map(([id,label])=>`<a href="#${id}">${label}</a>`).join('')}</div></div>`).join('');
  document.querySelectorAll('[data-navgroup]').forEach(b=>b.addEventListener('click',()=>{const open=b.getAttribute('aria-expanded')!=='true';b.setAttribute('aria-expanded',String(open));document.getElementById(`topics-${b.dataset.navgroup}`).hidden=!open}));
  wireSorting();populateEarnCountries();renderCoeffs();renderResults();renderYearChart();renderCovidEventStudy();fillBetaEffectCards();fillCovidDiDCard();renderHeatmap();renderWeightedTable();renderRedditTable();renderRedditCoverage();renderEurope();
  if(typeof L!=='undefined')initMap();
  renderTrendTotal();renderExplorer();
  senderSelect.addEventListener('change',()=>setCountry(senderSelect.value));
  document.querySelectorAll('.direction-switch [data-direction]').forEach(b=>b.addEventListener('click',()=>{viewState.direction=b.dataset.direction;clearIncompatibleFilters();renderExplorer();saveView(true)}));
  for(const id of ['chooseCountry','changeCountry'])document.getElementById(id).addEventListener('click',()=>{if(innerWidth<1024)setDrawer(true,{focus:false});senderSelect.focus()});
  document.getElementById('resetControls').addEventListener('click',()=>{viewState.filters={origin:'',destination:'',partner:''};document.getElementById('filterResetNote').textContent='Exploration filters cleared. Country and direction are unchanged.';renderExplorer();saveView(true)});
  for(const [el,key] of [[outUniSearch,'origin'],[inCountrySearch,'partner'],[inUniSearch,'destination']])el.addEventListener('input',()=>{viewState.filters[key]=el.value;clearTimeout(filterTimer);filterTimer=setTimeout(()=>{renderExplorer();saveView(false)},180)});
  document.querySelectorAll('.seg-btn[data-view]').forEach(b=>b.addEventListener('click',()=>{viewState.table=b.dataset.view;applyTableView();renderOrgFlowTable();saveView(true)}));
  document.getElementById('destTableFilter').addEventListener('input',e=>{viewState.query=e.target.value;applyTableSearch();saveView(false)});
  earnCountrySelect.addEventListener('change',()=>{viewState.salary=earnCountrySelect.value||null;salaryFollow=false;renderSalaryReference();saveView(true)});
  earnUnitSelect.addEventListener('change',()=>{viewState.unit=earnUnitSelect.value;renderSalaryReference();saveView(true)});
  document.getElementById('followSalary').addEventListener('click',()=>{viewState.salary=null;salaryFollow=true;renderSalaryReference();saveView(true)});
  document.getElementById('sec-europe').addEventListener('click',event=>{const b=event.target.closest('[data-country]');if(!b)return;viewState.direction=b.dataset.direction;setCountry(b.dataset.country);goToSection('sec-overview')});
  document.addEventListener('click',event=>{
    const b=event.target.closest('button.row-details-toggle');if(!b)return;
    const row=b.closest('tr'),open=b.getAttribute('aria-expanded')!=='true';b.setAttribute('aria-expanded',String(open));b.textContent=open?'Close':'Details';
    let expanded=row.nextElementSibling;
    if(!expanded?.classList.contains('expanded-table-row')){expanded=document.createElement('tr');expanded.className='expanded-table-row';const cell=document.createElement('td');cell.colSpan=row.children.length;const entries=JSON.parse(b.dataset.detail);cell.innerHTML='<dl class="expanded-table-details">'+entries.map(([k,v])=>`<div><dt>${escapeHtml(k)}</dt><dd>${escapeHtml(v)}</dd></div>`).join('')+'</dl>';expanded.append(cell);row.after(expanded)}
    expanded.hidden=!open;
  });
  document.addEventListener('click',event=>{const a=event.target.closest('a[href^="#"]');if(!a)return;event.preventDefault();goToSection(a.getAttribute('href').slice(1))});
  document.getElementById('drawerToggle').addEventListener('click',()=>setDrawer(!document.body.classList.contains('drawer-open')));
  for(const id of ['drawerClose','drawerBackdrop'])document.getElementById(id).addEventListener('click',()=>{setDrawer(false);document.getElementById('drawerToggle').focus()});
  document.addEventListener('keydown',event=>{if(!document.body.classList.contains('drawer-open'))return;if(event.key==='Escape'){setDrawer(false);document.getElementById('drawerToggle').focus()}else if(event.key==='Tab'){const items=[...document.querySelectorAll('#siteSidebar a,#siteSidebar button,#siteSidebar select')].filter(x=>!x.hidden&&x.offsetParent!==null);const first=items[0],last=items.at(-1);if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus()}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus()}}});
  document.getElementById('shareView').addEventListener('click',async()=>{saveView(false);try{await navigator.clipboard.writeText(location.href);document.getElementById('shareStatus').textContent='Link copied. It includes the country, section and filters.'}catch{document.getElementById('shareStatus').textContent='Copy the current browser address to share this view.'}});
  window.addEventListener('popstate',restoreView);
  window.addEventListener('scroll',()=>{if(scrollFrame)return;scrollFrame=true;requestAnimationFrame(()=>{scrollFrame=false;const offset=innerWidth<1024?84:32;const ids=['welcome',...NAV_TOPIC.keys()].filter(id=>!document.getElementById(id)?.hidden);let current='welcome',closest=-Infinity;for(const id of ids){const el=document.getElementById(id),top=el?.getBoundingClientRect().top;if(el&&top<=offset&&top>closest){current=id;closest=top}}if(innerHeight+scrollY>=document.documentElement.scrollHeight-3)current='sec-data';markNavigation(current);clearTimeout(scrollTimer);scrollTimer=setTimeout(()=>saveView(false),180)})},{passive:true});
  let resizeTimer;window.addEventListener('resize',()=>{setDrawer(false,{focus:false});clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{renderYearChart();renderCovidEventStudy();renderTrendTotal();if(viewState.country){renderTrendSender(viewState.country);renderSalaryReference();if(map)map.invalidateSize()}},120)});
  setDrawer(false,{focus:false});explorerReady=true;
  const id=location.hash.slice(1)||(viewState.view==='europe'?'sec-europe':'welcome');
  goToSection(id,{push:false});
}
initializeExplorer();
