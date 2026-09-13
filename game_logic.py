"""
منطق اللعبة: حساب الموارد، تكاليف الترقية، القتال
"""
import time
import random

# ---------------- إعدادات المباني ----------------
BUILDINGS = {
    "town_hall": {"name": "مبنى القيادة 🏰", "base_cost_gold": 0},
    "gold_mine": {"name": "منجم الذهب 💰", "base_cost_gold": 300, "produces": "gold"},
    "elixir_collector": {"name": "مُجمّع الإكسير 🧪", "base_cost_gold": 300, "produces": "elixir"},
    "army_camp": {"name": "معسكر الجيش ⛺", "base_cost_gold": 400},
    "cannon": {"name": "المدفع 💣", "base_cost_gold": 500},
}

TROOPS = {
    "barbarians": {"name": "برابرة ⚔️", "cost_elixir": 50, "power": 5, "train_seconds": 30},
    "archers": {"name": "رماة 🏹", "cost_elixir": 80, "power": 8, "train_seconds": 45},
}

# إنتاج الموارد بالساعة حسب مستوى المبنى
PRODUCTION_PER_HOUR = {1: 100, 2: 180, 3: 300, 4: 450, 5: 650}
UPGRADE_TIME_SECONDS = {1: 60, 2: 180, 3: 420, 4: 900, 5: 1800}  # وقت الترقية للمستوى التالي


def upgrade_cost(building_key, current_level):
    """تكلفة ترقية المبنى للمستوى التالي"""
    base = BUILDINGS[building_key]["base_cost_gold"]
    return int(base * (1.6 ** (current_level - 1)))


def upgrade_time(current_level):
    return UPGRADE_TIME_SECONDS.get(current_level, 1800 + (current_level - 5) * 900)


def calculate_resources(player):
    """يحسب الموارد المتراكمة منذ آخر تحديث بناءً على مستوى المناجم"""
    now = time.time()
    elapsed_hours = (now - player["last_update"]) / 3600.0

    gold_rate = PRODUCTION_PER_HOUR.get(player["gold_mine_level"], 650)
    elixir_rate = PRODUCTION_PER_HOUR.get(player["elixir_collector_level"], 650)

    new_gold = player["gold"] + int(elapsed_hours * gold_rate)
    new_elixir = player["elixir"] + int(elapsed_hours * elixir_rate)

    # سقف تخزين بسيط مرتبط بمستوى مبنى القيادة
    storage_cap = 5000 * player["town_hall_level"]
    new_gold = min(new_gold, storage_cap)
    new_elixir = min(new_elixir, storage_cap)

    return new_gold, new_elixir, now


def army_power(player):
    return (
        player["barbarians"] * TROOPS["barbarians"]["power"]
        + player["archers"] * TROOPS["archers"]["power"]
    )


def defense_power(player):
    """قوة الدفاع = المدفع + نصف قوة الجيش المتبقي في القرية"""
    cannon_defense = player["cannon_level"] * 15
    return cannon_defense + army_power(player) // 2


def simulate_attack(attacker, defender):
    """
    محاكاة هجوم مبسطة:
    - نقارن قوة جيش المهاجم بقوة دفاع المدافع
    - نحدد نسبة نجاح ونهب عشوائي ضمن حدود منطقية
    """
    atk_power = army_power(attacker)
    def_power = defense_power(defender)

    if atk_power == 0:
        return {
            "success": False,
            "stars": 0,
            "gold_stolen": 0,
            "elixir_stolen": 0,
            "message": "لا تملك جيشاً كافياً للهجوم! درّب جنوداً أولاً.",
        }

    # نسبة القوة تحدد فرصة النجاح والنجوم
    ratio = atk_power / max(def_power, 1)
    success_chance = min(0.9, 0.3 + ratio * 0.3)
    success = random.random() < success_chance

    if success:
        stars = 3 if ratio > 1.5 else (2 if ratio > 0.9 else 1)
        loot_percent = min(0.3, 0.1 * stars)
        gold_stolen = int(defender["gold"] * loot_percent)
        elixir_stolen = int(defender["elixir"] * loot_percent)
        trophy_change = 10 + stars * 5
    else:
        stars = 0
        gold_stolen = 0
        elixir_stolen = 0
        trophy_change = -8

    return {
        "success": success,
        "stars": stars,
        "gold_stolen": gold_stolen,
        "elixir_stolen": elixir_stolen,
        "trophy_change": trophy_change,
    }
