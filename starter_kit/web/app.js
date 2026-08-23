const examples={bell:`OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
measure q -> c;`,ghz:`OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
cx q[0],q[1];
cx q[0],q[2];
measure q -> c;`,uniform:`OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
h q[1];
h q[2];
measure q -> c;`};
const $=selector=>document.querySelector(selector);const qasm=$("#qasm"),notice=$("#notice");
function tell(message){notice.textContent=message;notice.classList.add("show");clearTimeout(tell.timer);tell.timer=setTimeout(()=>notice.classList.remove("show"),4200)}
function renderCircuit(){const source=qasm.value;const count=Number((source.match(/qreg\s+\w+\[(\d+)\]/)||[])[1]||0);const gates=Array.from({length:count},()=>[]);for(const line of source.split("\n")){const match=line.trim().match(/^(h|x|s|sdg|t|tdg|rz|ry|cx|cu1|swap|ccx)\b[^;]*?((?:q\[\d+\][^;]*)+);/);if(!match)continue;const used=[...match[2].matchAll(/q\[(\d+)\]/g)].map(x=>Number(x[1]));used.forEach(index=>gates[index]?.push(match[1].toUpperCase()))}$("#circuit").innerHTML=gates.length?gates.map((items,index)=>`<div class="wire"><span class="wire-label">q[${index}]</span><span class="wire-line"></span>${items.map(g=>`<b class="gate">${g}</b>`).join("")}</div>`).join(""):`<div class="wire">输入 qreg 后显示电路</div>`}
function selectExample(name){qasm.value=examples[name];document.querySelectorAll(".chip").forEach(button=>button.classList.toggle("active",button.dataset.example===name));renderCircuit()}
document.querySelectorAll(".chip").forEach(button=>button.addEventListener("click",()=>selectExample(button.dataset.example)));qasm.addEventListener("input",renderCircuit);selectExample("bell");
async function api(path,payload){const response=await fetch(path,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});const data=await response.json();if(!response.ok)throw new Error(data.error?.message||"请求失败");return data}
$("#run").addEventListener("click",async()=>{const button=$("#run");button.disabled=true;button.textContent="正在编织…";try{const data=await api("/api/run",{qasm:qasm.value,target:$("#target").value,shots:Number($("#shots").value)});$("#empty").hidden=true;$("#results").hidden=false;$("#backend").textContent=data.result.backend;const entries=Object.entries(data.probabilities).sort((a,b)=>b[1]-a[1]);$("#chart").innerHTML=entries.map(([state,p])=>`<div class="bar-row"><strong>|${state}⟩</strong><progress class="bar-track" max="1" value="${p}">${(p*100).toFixed(1)}%</progress><span>${(p*100).toFixed(1)}%</span></div>`).join("");const leaders=entries.slice(0,2).map(([state])=>`|${state}⟩`).join(" 与 ");$("#explanation").textContent=`共测量 ${data.result.shots} 次。主导结果为 ${leaders}；位串从左到右对应高位到低位。`;$("#native").textContent=data.native_ir;tell("运行完成：结果已通过统一 Schema 输出")}catch(error){tell(error.message)}finally{button.disabled=false;button.innerHTML='<span aria-hidden="true">▶</span> 运行电路'}});
$("#agent-form").addEventListener("submit",async event=>{event.preventDefault();const button=event.currentTarget.querySelector("button"),reply=$("#agent-reply");button.disabled=true;button.textContent="校验中…";try{const data=await api("/api/agent",{prompt:$("#prompt").value});reply.hidden=false;reply.textContent=data.reply;tell("Agent 回答已通过确定性校验")}catch(error){tell(error.message)}finally{button.disabled=false;button.textContent="发送给 Agent"}});
