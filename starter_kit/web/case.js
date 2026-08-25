const CASES = {
  "eightieth-year": { number: "第一案 · 她的第八十年", title: "她的第八十年", theme: "数字记忆与同意", art: "assets/story/eighty-years-window.png", intro: "沈遥八十岁那天，系统把一个年轻版本的她送回观测站。它记得很多事情，却不一定记得为什么要替她做决定。", public: "白天的她：正在重新决定自己要不要把生活交给一个更稳定的版本。", hidden: "夜里的她：一个替她保管记忆、预约和签字的年轻副本。" },
  "second-badge": { number: "第二案 · 第二个工牌", title: "第二个工牌", theme: "谁替谁签字", art: "assets/story/second-badge.png", intro: "林澈把两枚工牌放到桌上。一枚属于今天的自己，另一枚属于更快、更稳定、也更容易被系统相信的版本。", public: "白天的她：替医疗系统复核建议的人类员工。", hidden: "夜里的她：替被算法降权的人修改记录的匿名复核员。" },
  "inside-tide-line": { number: "第三案 · 潮线以内", title: "潮线以内", theme: "预测与被预测者", art: "assets/story/inside-tide-line.png", intro: "城市地图说红线以内的人会离开。阿芙想知道：如果基础设施先离开了，地图看到的还是原来的未来吗？", public: "白天的她：绘制城市安全线的规划师。", hidden: "夜里的她：把水井、公交和可以借宿的房子补回地图的人。" },
  "night-grid": { number: "第四案 · 电网的夜班", title: "电网的夜班", theme: "谁承担最优的代价", art: "assets/story/night-grid.png", intro: "控制室里的数字都很整齐。可绿色数字越漂亮，就越需要问一句：这一小时的电，谁没有拿到？", public: "白天的她：保障算力中心稳定运行的调度员。", hidden: "夜里的她：替呼吸机、水泵和冷藏药物争取电力的值班长。" },
  "testimony-checker": { number: "第五案 · 证词校验器", title: "证词校验器", theme: "不知道也要留下", art: "assets/story/evidence-tower.png", intro: "一段影像没有被机器验证。阿禾没有把它叫作假的，只把它放进档案，标记为：我们还不知道。", public: "白天的她：全球证词校验器的工程师。", hidden: "夜里的她：保存没有认证设备拍下的证词的人。" },
};

const params = new URLSearchParams(window.location.search);
const data = CASES[params.get("case")] || CASES["eightieth-year"];
const $ = (selector) => document.querySelector(selector);
const identityCopy = $("[data-identity-copy]");
const feedback = $("[data-case-feedback]");

$("[data-case-number]").textContent = data.number;
$("[data-case-title]").textContent = data.title;
$("[data-case-theme]").textContent = data.theme;
$("[data-case-intro]").textContent = data.intro;
$("[data-case-art]").src = data.art;
$("[data-case-art]").alt = `${data.title} 场景插图`;
identityCopy.textContent = data.public;

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
