const CASES = {
  "eightieth-year": { number: "第一案 · 她的第八十年", title: "她的第八十年", theme: "数字记忆与同意", art: "assets/story/eighty-years-window.png", intro: "沈遥八十岁那天，系统把一个年轻版本的她送回观测站。这个版本记得她二十岁时的脸，也记得她曾经签过的文件，却不一定记得每一次犹豫从哪里开始。沈遥没有马上删除它，也没有马上相信它。她决定先做一个最小的观察：如果只改变一个条件，两个版本的选择会不会走向不同的结果？", question: "如果年轻的副本替你做决定，你会先检查什么？", lesson: "你学到的是：量子实验可以帮助我们比较两个条件，但它不能判定一个人是否仍然是同一个人，也不能替任何人重新同意。我们只能诚实地记录，改变从哪里开始，证据又停在哪里。", public: "白天的她：正在重新决定自己要不要把生活交给一个更稳定的版本。", hidden: "夜里的她：一个替她保管记忆、预约和签字的年轻副本。" },
  "second-badge": { number: "第二案 · 第二个工牌", title: "第二个工牌", theme: "谁替谁签字", art: "assets/story/second-badge.png", intro: "林澈把两枚工牌放到桌上。一枚属于今天的自己，另一枚属于更快、更稳定、也更容易被系统相信的版本。医院希望所有建议都能迅速得到签字，系统也因此更喜欢那个从不迟疑的副本。林澈想知道，速度变快以后，原来被忽略的人是否会从记录里消失。", question: "当两个版本都说‘这是我的决定’，你愿意比较哪一处差异？", lesson: "你学到的是：关联不等于身份，稳定的输出也不等于更好的判断。量子线路只会告诉你两个条件下的结果如何不同，公平与责任仍然需要人来承担。", public: "白天的她：替医疗系统复核建议的人类员工。", hidden: "夜里的她：替被算法降权的人修改记录的匿名复核员。" },
  "inside-tide-line": { number: "第三案 · 潮线以内", title: "潮线以内", theme: "预测与被预测者", art: "assets/story/inside-tide-line.png", intro: "城市地图说红线以内的人会离开。阿芙却记得那里的水井、夜班车和不能独自走到避难所的老人。她想知道，如果政策先撤走了学校和公交，后来发生的离开还算不算地图原来预测的未来。", question: "地图改变以前，你愿意先留下谁的声音？", lesson: "你学到的是：预测会影响条件本身。一次量子对照可以展示‘只改一个条件，观测如何改变’，但它不能替代社区经验、气候研究或公共协商。", public: "白天的她：绘制城市安全线的规划师。", hidden: "夜里的她：把水井、公交和可以借宿的房子补回地图的人。" },
  "night-grid": { number: "第四案 · 电网的夜班", title: "电网的夜班", theme: "谁承担最优的代价", art: "assets/story/night-grid.png", intro: "控制室里的数字都很整齐。算力中心得到稳定电力，小镇的灯却在夜里一盏盏变暗。周岑发现，系统把一间医院和一座服务器机房压缩成了同一个‘负载’，于是最容易计算的选择也最容易被称为最优。", question: "当结果只有一个‘最优’，你会先问谁承担代价？", lesson: "你学到的是：干涉可以让一个结果增强，也可以让另一个结果消失；但‘更大’不等于‘更应该得到’。量子结果可以帮助我们看见条件变化，不能替公共程序做价值判断。", public: "白天的她：保障算力中心稳定运行的调度员。", hidden: "夜里的她：替呼吸机、水泵和冷藏药物争取电力的值班长。" },
  "testimony-checker": { number: "第五案 · 证词校验器", title: "证词校验器", theme: "不知道也要留下", art: "assets/story/evidence-tower.png", intro: "一段影像没有被机器验证，因为拍摄者没有系统承认的设备。阿禾没有把它叫作假的，也没有把它包装成真的。她把录音、时间和听见过它的人一起放进档案，留下一个不漂亮却诚实的标签：我们还不知道。", question: "当你还不能判断真假时，什么信息值得先保存？", lesson: "你学到的是：测量只告诉我们这次看到了什么。没有观测到的部分不能被想象填满；‘未知’也可以是一种需要被保护的证据状态。", public: "白天的她：全球证词校验器的工程师。", hidden: "夜里的她：保存没有认证设备拍下的证词的人。" },
};

const params = new URLSearchParams(window.location.search);
const data = CASES[params.get("case")] || CASES["eightieth-year"];
const $ = (selector) => document.querySelector(selector);
const identityCopy = $("[data-identity-copy]");
const feedback = $("[data-case-feedback]");
const caseActions = {
  "eightieth-year": ["先听她自己的声音", "只改一条记忆", "查看两份选择"],
  "second-badge": ["先看谁在签字", "只改一个身份", "比较两枚工牌"],
  "inside-tide-line": ["先听居民的地图", "只改一条道路", "查看联合结果"],
  "night-grid": ["先看夜班日志", "只改一项负载", "观察电力分布"],
  "testimony-checker": ["先保存未知", "只改一个证据", "查看观测记录"],
};

$("[data-case-number]").textContent = data.number;
$("[data-case-title]").textContent = data.title;
$("[data-case-theme]").textContent = data.theme;
$("[data-case-intro]").textContent = data.intro;
$("[data-case-question]").textContent = data.question;
$("[data-case-lesson]").textContent = data.lesson;
$("[data-case-art]").src = data.art;
$("[data-case-art]").alt = `${data.title} 场景插图`;
identityCopy.textContent = data.public;
document.querySelectorAll("[data-action]").forEach((button, index) => {
  button.textContent = caseActions[params.get("case")]?.[index] || button.textContent;
});

document.querySelectorAll("[data-identity]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-identity]").forEach((item) => item.classList.toggle("active", item === button));
    identityCopy.textContent = button.dataset.identity === "public" ? data.public : data.hidden;
  });
});

const actionText = {
  observe: "你先停下来。观察不是空白，它是在给结果留出位置。",
  change: "你只拨动一扇门。这样，后来发生的变化才有机会被看懂。",
  measure: "你现在看结果。测量告诉你这一次看见了什么，不替你编造没看见的部分。",
};
document.querySelectorAll("[data-action]").forEach((button) => button.addEventListener("click", () => {
  feedback.textContent = actionText[button.dataset.action];
}));

function renderBars(probabilities) {
  const host = $("[data-case-bars]");
  host.replaceChildren();
  Object.entries(probabilities).sort((a, b) => b[1] - a[1]).slice(0, 4).forEach(([state, probability]) => {
    const row = document.createElement("div");
    row.className = "case-bar";
    row.innerHTML = `<span>|${state}⟩</span><i style="width:${Math.max(4, probability * 100)}%"></i><span>${(probability * 100).toFixed(1)}%</span>`;
    host.append(row);
  });
}

$("#run-case-experiment").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  button.textContent = "观察中…";
  try {
    const response = await fetch("/api/inquiry", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mission: "bell-gates", prediction: "not-sure", conclusion: "h-opens-branches-cx-correlates", shots: 128 }) });
    if (!response.ok) throw new Error("请通过本地服务打开案件页");
    const passport = await response.json();
    const result = passport.experiment.control.probabilities;
    $("[data-case-result]").hidden = false;
    $("[data-result-title]").textContent = "两次观察的差异来自一个条件";
    $("[data-result-copy]").textContent = "小球的故事只是在帮你建立直觉；真正的记录来自重复测量。现在你可以回到主线，自己留下预测。";
    renderBars(result);
  } catch (error) {
    $("[data-case-result]").hidden = false;
    $("[data-result-title]").textContent = "故事先停在这里";
    $("[data-result-copy]").textContent = `${error.message}。打开主线仍可离线阅读并使用本地实验。`;
  } finally {
    button.disabled = false;
    button.textContent = "再做一次小实验";
  }
});
