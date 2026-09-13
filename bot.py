"""
بوت تلجرام - لعبة حروب شبيهة بـ Clash of Clans
تشغيل: python bot.py
تأكد من ضبط التوكن في ملف config.py أو متغير البيئة BOT_TOKEN
"""
import logging
import time
import random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

import database as db
import game_logic as gl
from config import BOT_TOKEN

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ---------------- أدوات مساعدة ----------------

def sync_resources(user_id):
    """يحدّث موارد اللاعب في قاعدة البيانات بناءً على الوقت المنقضي"""
    player = db.get_player(user_id)
    gold, elixir, now = gl.calculate_resources(player)
    db.update_player(user_id, gold=gold, elixir=elixir, last_update=now)
    return db.get_player(user_id)


def village_text(player):
    return (
        f"🏰 *قرية {player['username']}*\n\n"
        f"👑 مبنى القيادة: المستوى {player['town_hall_level']}\n"
        f"💰 الذهب: {player['gold']}\n"
        f"🧪 الإكسير: {player['elixir']}\n"
        f"🏆 الكؤوس: {player['trophies']}\n\n"
        f"⛏️ منجم الذهب: مستوى {player['gold_mine_level']}\n"
        f"🧪 مُجمّع الإكسير: مستوى {player['elixir_collector_level']}\n"
        f"⛺ معسكر الجيش: مستوى {player['army_camp_level']}\n"
        f"💣 المدفع: مستوى {player['cannon_level']}\n\n"
        f"⚔️ الجيش: {player['barbarians']} برابرة | {player['archers']} رماة"
    )


def main_menu():
    keyboard = [
        [InlineKeyboardButton("🏰 قريتي", callback_data="village")],
        [InlineKeyboardButton("🏗️ البناء والترقية", callback_data="build_menu")],
        [InlineKeyboardButton("⚔️ تدريب الجيش", callback_data="train_menu")],
        [InlineKeyboardButton("🗡️ هجوم", callback_data="attack")],
        [InlineKeyboardButton("🏆 لوحة المتصدرين", callback_data="leaderboard")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_menu():
    keyboard = []
    for key, info in gl.BUILDINGS.items():
        if key == "town_hall":
            continue
        keyboard.append(
            [InlineKeyboardButton(f"⬆️ ترقية {info['name']}", callback_data=f"upgrade_{key}")]
        )
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="village")])
    return InlineKeyboardMarkup(keyboard)


def train_menu():
    keyboard = []
    for key, info in gl.TROOPS.items():
        keyboard.append(
            [InlineKeyboardButton(
                f"🎯 درّب {info['name']} ({info['cost_elixir']} إكسير)",
                callback_data=f"train_{key}",
            )]
        )
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="village")])
    return InlineKeyboardMarkup(keyboard)


# ---------------- الأوامر ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.create_player(user.id, user.first_name or user.username or "لاعب")
    player = sync_resources(user.id)
    await update.message.reply_text(
        "🎮 أهلاً بك في *حرب القرى*!\n\nقريتك جاهزة، ابدأ بجمع الموارد وبناء جيشك.",
        parse_mode="Markdown",
    )
    await update.message.reply_text(
        village_text(player), parse_mode="Markdown", reply_markup=main_menu()
    )


async def village_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    player = sync_resources(user_id)
    await update.message.reply_text(
        village_text(player), parse_mode="Markdown", reply_markup=main_menu()
    )


# ---------------- معالج الأزرار ----------------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    player = db.get_player(user_id)
    if not player:
        db.create_player(user_id, query.from_user.first_name or "لاعب")
        player = db.get_player(user_id)

    player = sync_resources(user_id)
    data = query.data

    if data == "village":
        await query.edit_message_text(
            village_text(player), parse_mode="Markdown", reply_markup=main_menu()
        )

    elif data == "build_menu":
        await query.edit_message_text(
            "🏗️ اختر مبنى لترقيته:", reply_markup=build_menu()
        )

    elif data.startswith("upgrade_"):
        building_key = data.replace("upgrade_", "")
        level_field = f"{building_key}_level"
        current_level = player[level_field]
        cost = gl.upgrade_cost(building_key, current_level)

        if player["gold"] < cost:
            await query.answer(f"لا يوجد ذهب كافٍ! تحتاج {cost} 💰", show_alert=True)
            return

        db.update_player(
            user_id,
            gold=player["gold"] - cost,
            **{level_field: current_level + 1},
        )
        name = gl.BUILDINGS[building_key]["name"]
        await query.answer(f"تمت ترقية {name} إلى المستوى {current_level + 1}!", show_alert=True)
        player = db.get_player(user_id)
        await query.edit_message_text(
            village_text(player), parse_mode="Markdown", reply_markup=main_menu()
        )

    elif data == "train_menu":
        await query.edit_message_text(
            "⚔️ اختر نوع الجندي للتدريب:", reply_markup=train_menu()
        )

    elif data.startswith("train_"):
        troop_key = data.replace("train_", "")
        info = gl.TROOPS[troop_key]

        if player["elixir"] < info["cost_elixir"]:
            await query.answer(f"لا يوجد إكسير كافٍ! تحتاج {info['cost_elixir']} 🧪", show_alert=True)
            return

        db.update_player(
            user_id,
            elixir=player["elixir"] - info["cost_elixir"],
            **{troop_key: player[troop_key] + 1},
        )
        await query.answer(f"تم تدريب {info['name']}!", show_alert=True)
        player = db.get_player(user_id)
        await query.edit_message_text(
            village_text(player), parse_mode="Markdown", reply_markup=main_menu()
        )

    elif data == "attack":
        opponents = db.get_all_players(exclude_user_id=user_id)
        if not opponents:
            await query.answer("لا يوجد لاعبون آخرون بعد!", show_alert=True)
            return

        defender = random.choice(opponents)
        result = gl.simulate_attack(player, defender)

        if not result["success"] and "message" in result:
            await query.answer(result["message"], show_alert=True)
            return

        # تحديث المهاجم
        new_trophies = max(0, player["trophies"] + result["trophy_change"])
        db.update_player(
            user_id,
            gold=player["gold"] + result["gold_stolen"],
            elixir=player["elixir"] + result["elixir_stolen"],
            trophies=new_trophies,
        )
        # تحديث المدافع (خسارة الموارد المنهوبة)
        db.update_player(
            defender["user_id"],
            gold=max(0, defender["gold"] - result["gold_stolen"]),
            elixir=max(0, defender["elixir"] - result["elixir_stolen"]),
        )

        if result["success"]:
            msg = (
                f"⚔️ *نتيجة الهجوم على {defender['username']}*\n\n"
                f"🌟 النجوم: {'⭐' * result['stars']}\n"
                f"💰 ذهب منهوب: {result['gold_stolen']}\n"
                f"🧪 إكسير منهوب: {result['elixir_stolen']}\n"
                f"🏆 تغيّر الكؤوس: +{result['trophy_change']}"
            )
        else:
            msg = (
                f"💥 *فشل الهجوم على {defender['username']}*\n\n"
                f"دفاعهم كان أقوى من جيشك!\n"
                f"🏆 تغيّر الكؤوس: {result['trophy_change']}"
            )

        player = db.get_player(user_id)
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=main_menu())

    elif data == "leaderboard":
        top = db.get_leaderboard(10)
        lines = ["🏆 *لوحة المتصدرين*\n"]
        for i, p in enumerate(top, 1):
            lines.append(f"{i}. {p['username']} — {p['trophies']} كأس")
        await query.edit_message_text(
            "\n".join(lines), parse_mode="Markdown", reply_markup=main_menu()
        )


def main():
    db.init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("village", village_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("البوت يعمل الآن...")
    app.run_polling()


if __name__ == "__main__":
    main()
