const API_BASE = "https://Aliabd.pythonanywhere.com";

const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

const USER_ID = tg?.initDataUnsafe?.user?.id || "test_user";
const USERNAME = tg?.initDataUnsafe?.user?.first_name || "لاعب";

let state = null;

const BUILDING_DEFS = {
  town_hall: { name: "مبنى القيادة", x: 50, y: 30, icon: iconTownHall, levelKey: "town_hall_level", upgradable: false },
  gold_mine: { name: "منجم الذهب", x: 25, y: 45, icon: iconGoldMine, levelKey: "gold_mine_level", upgradable: true, key: "gold_mine" },
  elixir_collector: { name: "مُجمّع الإكسير", x: 75, y: 45, icon: iconElixir, levelKey: "elixir_collector_level", upgradable: true, key: "elixir_collector" },
  army_camp: { name: "معسكر الجيش", x: 30, y: 68, icon: iconCamp, levelKey: "army_camp_level", upgradable: true, key: "army_camp" },
  cannon: { name: "المدفع", x: 70, y: 68, icon: iconCannon, levelKey: "cannon_level", upgradable: true, key: "cannon" },
};

const TROOP_DEFS = {
  barbarians: { name: "برابرة", icon: "⚔️", costElixir: 50 },
  archers: { name: "رماة", icon: "🏹", costElixir: 80 },
};

const TWEMOJI_BASE = "https://cdn.jsdelivr.net/npm/twemoji@14.0.2/assets/svg/";
function emojiIcon(codepoint) {
  return `<img src="${TWEMOJI_BASE}${codepoint}.svg" alt="" style="width:100%;height:100%" />`;
}
function iconTownHall() { return emojiIcon("1f3f0"); }
function iconGoldMine() { return emojiIcon("1f4b0"); }
function iconElixir()   { return emojiIcon("1f9ea"); }
function iconCamp()     { return emojiIcon("26fa"); }
function iconCannon()   { return emojiIcon("1f4a3"); }

async function fetchState() {
  try {
    const res = await fetch(`${API_BASE}/api/village?user_id=${USER_ID}&username=${encodeURIComponent(USERNAME)}`);
    if (!res.ok) throw new Error("فشل الاتصال بالخادم");
    state = await res.json();
    render();
  } catch (err) {
    showToast("تعذّر الاتصال بالخادم. تحقق من رابط API.");
    console.error(err);
  } finally {
    document.getElementById("loading-screen").classList.add("hidden");
    document.getElementById("app").classList.remove("hidden");
  }
}

async function postAction(action, payload = {}) {
  try {
    const res = await fetch(`${API_BASE}/api/action`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_id: USER_ID, action, ...payload }),
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.message || "حدث خطأ");
      return null;
    }
    return data;
  } catch (err) {
    showToast("تعذّر تنفيذ الإجراء");
    return null;
  }
}

function render() {
  if (!state) return;
  document.getElementById("gold-value").textContent = state.gold;
  document.getElementById("elixir-value").textContent = state.elixir;
  document.getElementById("trophies-value").textContent = state.trophies;
  renderBuildings();
}

function renderBuildings() {
  const layer = document.getElementById("building-layer");
  layer.innerHTML = "";
  for (const [key, def] of Object.entries(BUILDING_DEFS)) {
    const level = state[def.levelKey];
    const el = document.createElement("div");
    el.className = "building";
    el.style.left = def.x + "%";
    el.style.top = def.y + "%";
    el.innerHTML = def.icon() + `<span class="building-level-badge">Lv${level}</span>`;
    el.addEventListener("click", () => openBuildingPanel(key, def, level));
    layer.appendChild(el);
  }
}

function openBuildingPanel(key, def, level) {
  const panel = document.getElementById("building-panel");
  document.getElementById("panel-title").textContent = def.name;
  document.getElementById("panel-level").textContent = `المستوى الحالي: ${level}`;

  const costEl = document.getElementById("panel-cost");
  const actionBtn = document.getElementById("panel-action");

  if (!def.upgradable) {
    costEl.textContent = "هذا المبنى مركزي ولا يمكن ترقيته يدوياً.";
    actionBtn.classList.add("hidden");
  } else {
    const cost = state.upgrade_costs[def.key];
    costEl.textContent = `تكلفة الترقية للمستوى ${level + 1}: ${cost} 💰`;
    actionBtn.classList.remove("hidden");
    actionBtn.onclick = async () => {
      const result = await postAction("upgrade", { building: def.key });
      if (result) {
        state = result;
        render();
        showToast(`تمت ترقية ${def.name}! 🎉`);
        panel.classList.add("hidden");
      }
    };
  }
  panel.classList.remove("hidden");
}

document.getElementById("panel-close").addEventListener("click", () => {
  document.getElementById("building-panel").classList.add("hidden");
});

const views = { train: "train-view", attack: "attack-view", leaderboard: "leaderboard-view" };

document.querySelectorAll(".nav-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".nav-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const view = btn.dataset.view;

    document.querySelectorAll(".overlay-view").forEach((v) => v.classList.add("hidden"));
    document.getElementById("building-panel").classList.add("hidden");

    if (view === "village") return;
    const viewId = views[view];
    document.getElementById(viewId).classList.remove("hidden");
    if (view === "train") renderTroopList();
    if (view === "attack") renderAttackView();
    if (view === "leaderboard") renderLeaderboard();
  });
});

document.querySelectorAll(".overlay-close").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.getElementById(btn.dataset.close).classList.add("hidden");
    document.querySelectorAll(".nav-btn").forEach((b) => b.classList.remove("active"));
    document.querySelector('.nav-btn[data-view="village"]').classList.add("active");
  });
});

function renderTroopList() {
  const list = document.getElementById("troop-list");
  list.innerHTML = "";
  for (const [key, def] of Object.entries(TROOP_DEFS)) {
    const count = state[key];
    const card = document.createElement("div");
    card.className = "troop-card";
    card.innerHTML = `
      <div class="troop-info">
        <span class="troop-icon">${def.icon}</span>
        <div>
          <div class="troop-name">${def.name}</div>
          <div class="troop-meta">لديك: ${count} | التكلفة: ${def.costElixir} 🧪</div>
        </div>
      </div>
      <button class="troop-train-btn">تدريب</button>
    `;
    card.querySelector(".troop-train-btn").addEventListener("click", async () => {
      const result = await postAction("train", { troop: key });
      if (result) {
        state = result;
        render();
        renderTroopList();
        showToast(`تم تدريب ${def.name}! ⚔️`);
      }
    });
    list.appendChild(card);
  }
}

function renderAttackView() {
  const power = state.barbarians * 5 + state.archers * 8;
  document.getElementById("army-power").textContent = power;
  document.getElementById("attack-result").innerHTML = "";
}

document.getElementById("attack-btn").addEventListener("click", async () => {
  const result = await postAction("attack");
  if (result) {
    state = result.player;
    render();
    const r = result.battle;
    const resultBox = document.getElementById("attack-result");
    if (r.success) {
      resultBox.innerHTML = `
        <p>🌟 النجوم: ${"⭐".repeat(r.stars)}</p>
        <p>💰 ذهب منهوب: ${r.gold_stolen}</p>
        <p>🧪 إكسير منهوب: ${r.elixir_stolen}</p>
        <p>🏆 تغيّر الكؤوس: +${r.trophy_change}</p>
      `;
    } else {
      resultBox.innerHTML = `<p>${r.message || "فشل الهجوم! دفاعهم كان أقوى."}</p>`;
    }
  }
});

async function renderLeaderboard() {
  const list = document.getElementById("leaderboard-list");
  list.innerHTML = "<li>جارٍ التحميل...</li>";
  try {
    const res = await fetch(`${API_BASE}/api/leaderboard`);
    const top = await res.json();
    list.innerHTML = "";
    top.forEach((p, i) => {
      const li = document.createElement("li");
      li.innerHTML = `<span><span class="rank">#${i + 1}</span>${p.username}</span><span>${p.trophies} 🏆</span>`;
      list.appendChild(li);
    });
  } catch {
    list.innerHTML = "<li>تعذّر تحميل القائمة</li>";
  }
}

function showToast(msg) {
  const toast = document.getElementById("toast");
  toast.textContent = msg;
  toast.classList.remove("hidden");
  setTimeout(() => toast.classList.add("hidden"), 2500);
}

fetchState();
