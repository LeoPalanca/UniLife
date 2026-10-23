/* Pure view-state and aggregation helpers. Source records are never mutated. */
const Mobility = (() => {
  const normalize = value => String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]/g, '');
  function partners(records, country, direction = 'outgoing') {
    if (!country) return [];
    const incoming = direction === 'incoming';
    const selected = records.filter(r => r[incoming ? 'receiving_code' : 'sending_code'] === country);
    const total = selected.reduce((n, r) => n + r.flow_count, 0);
    return selected.map(r => ({...r, actual_sending_code:r.sending_code, actual_receiving_code:r.receiving_code,
      receiving_code:incoming ? r.sending_code : r.receiving_code,
      receiving_country:incoming ? r.sending_country : r.receiving_country,
      partner_gdp:incoming ? r.sender_gdp_pc_current_usd_wb : r.receiver_gdp_pc_current_usd_wb,
      flow_share:total ? r.flow_count / total : 0}));
  }
  function matches(row, filters, direction) {
    const origin = normalize(filters.origin), destination = normalize(filters.destination), partner = normalize(filters.partner);
    if (origin && !normalize(`${row.sending_org || ''} ${row.sending_city || ''}`).includes(origin)) return false;
    if (destination && !normalize(`${row.receiving_org || ''} ${row.receiving_city || ''}`).includes(destination)) return false;
    const partnerText = direction === 'incoming' ? `${row.sending_code} ${row.sending_country || ''}` : `${row.receiving_code} ${row.receiving_country || ''}`;
    return !partner || normalize(partnerText).includes(partner);
  }
  function endpointRows(records, country, direction, filters, names = new Map()) {
    if (!country) return [];
    const key = direction === 'incoming' ? 'receiving_code' : 'sending_code';
    return records.filter(r => r[key] === country).map(r => ({...r,sending_country:r.sending_country || names.get(r.sending_code) || r.sending_code})).filter(r => matches(r, filters, direction));
  }
  function aggregatePartners(records, country, direction, countryFlows) {
    const incoming = direction === 'incoming', groups = new Map();
    const refs = new Map(partners(countryFlows, country, direction).map(r => [r.receiving_code,r]));
    records.forEach(r => {
      const code = r[incoming ? 'sending_code' : 'receiving_code'];
      if (!groups.has(code)) groups.set(code,{...(refs.get(code) || {}),receiving_code:code,receiving_country:r[incoming ? 'sending_country' : 'receiving_country'] || code,flow_count:0});
      groups.get(code).flow_count += r.flow_count;
    });
    const total = [...groups.values()].reduce((n,r) => n+r.flow_count,0);
    return [...groups.values()].map(r => ({...r,flow_share:total ? r.flow_count/total : 0}));
  }
  function readQuery(search, validCodes) {
    const p = new URLSearchParams(search), safe = key => (p.get(key) || '').slice(0,180);
    return {country:validCodes.has(p.get('country')) ? p.get('country') : null,
      direction:p.get('direction') === 'incoming' ? 'incoming' : 'outgoing',
      view:p.get('view') === 'europe' ? 'europe' : 'country',
      filters:{origin:safe('origin'),destination:safe('destination'),partner:safe('partner')},
      table:['countryUni','uniCountry','uniUni'].includes(p.get('table')) ? p.get('table') : 'country',
      salary:validCodes.has(p.get('salary')) ? p.get('salary') : null,unit:p.get('unit') === 'pps' ? 'pps' : 'eur',query:safe('q')};
  }
  function query(state) {
    const p = new URLSearchParams();
    if (state.country) p.set('country',state.country);
    if (state.direction !== 'outgoing') p.set('direction',state.direction);
    if (state.view === 'europe') p.set('view','europe');
    for (const key of ['origin','destination','partner']) if (state.filters[key]) p.set(key,state.filters[key]);
    if (state.table !== 'country') p.set('table',state.table);
    if (state.salary && state.salary !== state.country) p.set('salary',state.salary);
    if (state.unit === 'pps') p.set('unit','pps');
    if (state.query) p.set('q',state.query);
    return p.toString();
  }
  return {normalize,partners,matches,endpointRows,aggregatePartners,readQuery,query};
})();
if (typeof module !== 'undefined' && module.exports) module.exports = Mobility;
