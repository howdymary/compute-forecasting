const root=document.querySelector('#study-summary');
const response=await fetch('design/robustness-v2.json');
if(response.ok){
  const report=await response.json();
  const intro=document.createElement('p');intro.textContent=`Completed ${report.remote_rollouts.toLocaleString()} Modal rollouts, ${report.services.sources.length} Exa searches, and ${report.services.decisions.length} Tinker decisions using ${report.model}. ${report.services.eligibility.cross_agent_reads} verified cross-agent memory reads.`;root.replaceChildren(intro);
  const table=document.createElement('table');const head=table.createTHead().insertRow();for(const x of ['Fresh scenarios','Starting policy','Research-guided','Family-matched random']){const th=document.createElement('th');th.textContent=x;head.append(th)}
  for(const [label,values] of Object.entries(report.evaluation)){const row=table.insertRow();row.insertCell().textContent=label;for(const key of ['baseline','research','family_matched_random']){const x=values[key];row.insertCell().textContent=`${x.successes}/${x.n} (${Math.round(x.success_rate*100)}%)`}}
  root.append(table);const link=document.createElement('a');link.href='design/robustness-v2.json';link.textContent='Inspect the full numerical report and service receipts ↗';root.append(link);
  const limit=document.createElement('p');limit.className='note';limit.textContent='Development results selected the policies. Held-out and stress scenarios were evaluated after freezing. This study does not isolate the causal value of search or memory, and the new body and bowling task remain design concepts.';root.append(limit);
  const notebook=document.createElement('details');const title=document.createElement('summary');title.textContent='Open the eight-round research notebook';notebook.append(title);
  for(const round of report.rounds){
    const article=document.createElement('article');article.style.cssText='padding:20px 0;border-bottom:1px solid #bdc7bc';const heading=document.createElement('h3');heading.textContent=`Round ${round.iteration+1} / ${round.focus.replaceAll('_',' ')} → ${round.family.replaceAll('_',' ')} / ${round.accepted?'accepted':'rejected'}`;article.append(heading);
    const best=Math.max(...round.candidates.map(x=>x.summary.successes));const measured=document.createElement('p');measured.textContent=`Four candidates tested on the same 24 development scenarios. Best: ${best}/24 successes. Critic evidence: ${round.critic_record}.`;article.append(measured);
    const record=report.services.records.find(x=>x.id===round.evidence_record);for(const source of record?.payload.content.evidence.sources??[]){const p=document.createElement('p');const a=document.createElement('a');a.href=source.url;a.target='_blank';a.rel='noreferrer';a.textContent=source.title;p.append(a);article.append(p)}notebook.append(article);
  }root.append(notebook);
}
