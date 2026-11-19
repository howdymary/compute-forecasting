import assert from 'node:assert/strict';
import {stepCountAt,taskStatesAt,comparisonEvidence,activityAt} from '../web/desk/efficient-evidence.mjs';

const episode={duration:30,step_events:[{detected_t:2,completed:true},{detected_t:8,completed:false}],
 events:[{task:'alarm',t:10,success:true,phase:'release'},{task:'alarm',t:12,success:false,phase:'recover'},
         {task:'drawer',t:20,success:false,phase:'release'}]};
assert.equal(stepCountAt(episode,1),0);assert.equal(stepCountAt(episode,9),2);
assert.equal(taskStatesAt(episode,5)[0].status,'active');assert.equal(taskStatesAt(episode,13)[0].status,'passed');
assert.equal(taskStatesAt(episode,21)[1].status,'failed');assert.equal(taskStatesAt(episode,30)[2].status,'pending');
const measured={...episode,model_decisions:[{t:1,observation:{domain:'walk',station:'alarm'}},
 {t:10,observation:{domain:'recovery',task:'alarm'}},{t:15,observation:{domain:'walk',station:'drawer'}}]};
assert.equal(activityAt(measured,0).label,'Settling');
assert.equal(activityAt(measured,11).label,'Clock · Arm recovery');
assert.equal(taskStatesAt(measured,11)[1].status,'pending');
assert.equal(taskStatesAt(measured,16)[1].status,'active');
const passed={complete:true,qualified_complete:true,steps:{attempts:800},duration:260};
const faster={complete:true,qualified_complete:true,steps:{attempts:500},duration:220};
assert.equal(comparisonEvidence(passed,faster).stepReduction,.375);
assert.equal(comparisonEvidence(passed,faster).headline,'300 fewer steps');
assert.equal(comparisonEvidence({...passed,complete:false,qualified_complete:false,steps:{attempts:1}},faster).stepReduction,null);
assert.equal(comparisonEvidence(passed,{...faster,qualified_complete:false}).stepReduction,null);
assert.equal(comparisonEvidence(passed,{...faster,duration:270}).status,'mixed');
console.log('Passed: measured attempt timing, verified task events, failed/unfinished status and no efficiency claim against failed or unqualified episodes.');
