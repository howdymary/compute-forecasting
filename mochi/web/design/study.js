const root=document.querySelector('#study-summary');
const response=await fetch('design/robustness-v2.json');
if(response.ok){
  const report=await response.json();
  const intro=document.createElement('p');intro.textContent=`Completed ${report.remote_rollouts.toLocaleString()} Modal rollouts, ${report.services.sources.length} Exa searches, and ${report.services.decisions.length} Tinker decisions using ${report.model}. ${report.services.eligibility.cross_agent_reads} verified cross-agent memory reads.`;root.replaceChildren(intro);
  const table=document.createElement('table');const head=table.createTHead().insertRow();for(const x of ['Fresh scenarios','Starting policy','Research-guided','Family-matched random']){const th=document.createElement('th');th.textContent=x;head.append(th)}
  for(const [label,values] of Object.entries(report.evaluation)){const row=table.insertRow();row.insertCell().textContent=label;for(const key of ['baseline','research','family_matched_random']){const x=values[key];row.insertCell().textContent=`${x.successes}/${x.n} (${Math.round(x.success_rate*100)}%)`}}
  root.append(table);const link=document.createElement('a');link.href='design/robustness-v2.json';link.textContent='Inspect the full numerical report and service receipts ↗';root.append(link);
}
