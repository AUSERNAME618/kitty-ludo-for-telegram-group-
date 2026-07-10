"""
mench_bot.py - Telegram Ludo (Mench) bot, core loop.

Setup on your own machine (this sandbox has no network, so this part
can't be tested here -- see the note at the bottom of the chat message):
    pip install python-telegram-bot --upgrade
    export BOT_TOKEN=xxxx
    python3 mench_bot.py

Covers: lobby + join, dice-based turns, turn/permission locking,
mention captions, board rendering, message cleanup. NOT yet included
(next step): the 3x3 corner keyboard layout and the 4-mode inline
query picker -- this version starts every game as Quick+Safe so the
turn loop can be tested end to end first.
"""
import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    InlineQueryHandler, ContextTypes, filters,
)

from game_engine import Game
from persistence import init_db, save_game, load_game, delete_game
from render_helper import render_game_png

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("mench")

MAX_PLAYERS = 4
COLORS_IN_JOIN_ORDER = ["Red", "Blue", "Green", "Yellow"]

# in-memory lobbies: chat_id -> {"user_ids": [...], "names": {user_id: name}}
LOBBIES = {}


def mention(user_id: int, name: str) -> str:
    return f'<a href="tg://user?id={user_id}">{name}</a>'


import uuid
from telegram import InlineQueryResultArticle, InputTextMessageContent

MODE_LABELS = {
    ("safe", "quick"): "🟢 سیف سریع (یه مهره برنده)",
    ("safe", "full"): "🟢 سیف کامل (هر ۴ مهره)",
    ("normal", "quick"): "🔴 نرمال سریع (یه مهره برنده)",
    ("normal", "full"): "🔴 نرمال کامل (هر ۴ مهره)",
}
MODE_MARKER = "MENCH_NEW::"  # prefix used to recognize a mode-picker selection in a normal message


async def on_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fires when someone types '@your_bot_username ' (with a trailing space) anywhere."""
    results = []
    for (safe, speed), label in MODE_LABELS.items():
        payload = f"{MODE_MARKER}{safe}:{speed}"
        results.append(
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=label,
                description="بزن تا لابی این حالت تو همین چت ساخته شه",
                input_message_content=InputTextMessageContent(payload),
            )
        )
    await update.inline_query.answer(results, cache_time=0)


async def on_possible_mode_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Catches the message Telegram sends after someone taps an inline mode result."""
    text = update.message.text or ""
    if not text.startswith(MODE_MARKER):
        return
    chat_id = update.effective_chat.id
    if load_game(chat_id):
        await update.message.reply_text("یه بازی همین الان در جریانه. اول /endmench بزن.")
        return
    _, rest = text.split(MODE_MARKER, 1)
    safe_str, speed_str = rest.split(":")
    LOBBIES[chat_id] = {"user_ids": [], "names": {}, "safe_mode": safe_str == "safe",
                        "quick_mode": speed_str == "quick"}
    label = MODE_LABELS[(safe_str, speed_str)]
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("بزن بریم 🎲", callback_data="join")],
                                [InlineKeyboardButton("شروع بازی ▶️", callback_data="startgame")]])
    await update.message.reply_text(f"لابی منچ ساخته شد ({label}).\nهرکی بازی می‌کنه بزنه «بزن بریم».",
                                      reply_markup=kb)
    chat_id = update.effective_chat.id
    if load_game(chat_id):
        await update.message.reply_text("یه بازی همین الان تو این چت در حاله. اول با /endmench تمومش کن.")
        return
    LOBBIES[chat_id] = {"user_ids": [], "names": {}}
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("بزن بریم 🎲", callback_data="join")],
                                [InlineKeyboardButton("شروع بازی ▶️", callback_data="startgame")]])
    await update.message.reply_text(
        "بازی منچ جدید ساخته شد! هرکی بازی می‌کنه بزنه «بزن بریم»، بعد سازنده «شروع بازی» رو بزنه.\n(۲ تا ۴ نفر)",
        reply_markup=kb,
    )


async def on_lobby_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = update.effective_chat.id
    user = query.from_user
    lobby = LOBBIES.get(chat_id)
    if lobby is None:
        await query.answer("لابی‌ای در کار نیست، با /newmench یکی بساز.", show_alert=True)
        return

    if query.data == "join":
        if user.id in lobby["user_ids"]:
            await query.answer("همین الانم تو بازی هستی.")
            return
        if len(lobby["user_ids"]) >= MAX_PLAYERS:
            await query.answer("لابی پره (حداکثر ۴ نفر).", show_alert=True)
            return
        lobby["user_ids"].append(user.id)
        lobby["names"][user.id] = user.first_name
        await query.answer("اضافه شدی!")
        names = "، ".join(lobby["names"][u] for u in lobby["user_ids"])
        await query.edit_message_text(
            f"بازی منچ جدید ساخته شد! هرکی بازی می‌کنه بزنه «بزن بریم».\nبازیکنا: {names}",
            reply_markup=query.message.reply_markup,
        )
        return

    if query.data == "startgame":
        if len(lobby["user_ids"]) < 2:
            await query.answer("حداقل ۲ نفر لازمه.", show_alert=True)
            return
        await query.answer()
        await start_game(chat_id, lobby, context)
        del LOBBIES[chat_id]
        return


async def start_game(chat_id, lobby, context: ContextTypes.DEFAULT_TYPE):
    colors = COLORS_IN_JOIN_ORDER[: len(lobby["user_ids"])]
    game = Game(colors, quick_mode=lobby.get("quick_mode", True), safe_mode=lobby.get("safe_mode", True))
    player_names = dict(zip(colors, (lobby["names"][u] for u in lobby["user_ids"])))
    player_user_ids = dict(zip(colors, lobby["user_ids"]))

    msg_id = await post_board(chat_id, game, player_names, player_user_ids, context,
                                extra_caption="بازی شروع شد!")
    save_game(chat_id, game, msg_id, player_names, player_user_ids)


async def post_board(chat_id, game, player_names, player_user_ids, context, extra_caption=""):
    """Sends a fresh board photo + caption, so it always lands at the bottom of the chat."""
    png = render_game_png(game)
    color = game.current.color
    uid = player_user_ids[color]
    name = player_names[color]
    caption = (extra_caption + "\n" if extra_caption else "") + f"نوبت بازیکن {mention(uid, name)} — تاس بنداز 🎲"
    msg = await context.bot.send_photo(chat_id=chat_id, photo=png, caption=caption, parse_mode="HTML")
    return msg.message_id


async def on_dice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    data = load_game(chat_id)
    if data is None:
        return  # no active game, ignore random dice in the chat

    game, board_message_id, player_names, player_user_ids = (
        data["game"], data["board_message_id"], data["player_names"], data["player_user_ids"],
    )

    current_color = game.current.color
    expected_user_id = player_user_ids[current_color]

    # only accept a dice roll from the current player, replying to the active board message
    if update.effective_user.id != expected_user_id:
        return
    if not update.message.reply_to_message or update.message.reply_to_message.message_id != board_message_id:
        return

    value = update.message.dice.value
    dice_message_id = update.message.message_id

    moves = game.movable_pieces(value)
    if len(moves) > 1:
        # ambiguous: ask the player which piece, via inline keyboard (simple version for now)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"مهره {i+1}", callback_data=f"move:{i}:{value}")]
                                     for i in moves])
        await update.message.reply_text("کدوم مهره؟", reply_markup=kb)
        context.chat_data["pending_dice_msg"] = dice_message_id
        return

    log_lines = (game.apply_move(moves[0], value) if moves else ["no legal move"])
    finished = False
    if moves and game.has_won(game.current):
        game.game_over = True
        game.winner = game.current.color
        finished = True
    elif not moves:
        game.end_turn(extra=(value == 6))
    else:
        game.end_turn(extra=(value == 6))

    await finish_turn(chat_id, game, player_names, player_user_ids, board_message_id,
                       dice_message_id, value, context, finished)


async def on_piece_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    chat_id = update.effective_chat.id
    data = load_game(chat_id)
    if data is None:
        await query.answer("بازی‌ای در جریان نیست.", show_alert=True)
        return
    game, board_message_id, player_names, player_user_ids = (
        data["game"], data["board_message_id"], data["player_names"], data["player_user_ids"],
    )
    current_color = game.current.color
    if query.from_user.id != player_user_ids[current_color]:
        await query.answer("نوبت تو نیست.", show_alert=True)
        return

    _, piece_idx, value = query.data.split(":")
    piece_idx, value = int(piece_idx), int(value)
    await query.answer()
    game.apply_move(piece_idx, value)
    finished = game.has_won(game.current)
    if finished:
        game.game_over = True
        game.winner = game.current.color
    else:
        game.end_turn(extra=(value == 6))

    await query.message.delete()
    await finish_turn(chat_id, game, player_names, player_user_ids, board_message_id,
                       None, value, context, finished)


async def finish_turn(chat_id, game, player_names, player_user_ids, old_board_message_id,
                       dice_message_id, value, context, finished):
    if finished:
        winner_name = player_names[game.winner]
        png = render_game_png(game)
        await context.bot.send_photo(chat_id=chat_id, photo=png,
                                       caption=f"🏆 {winner_name} برنده شد!")
        delete_game(chat_id)
    else:
        prev_color = None
        extra_caption = f"تاس: {value}"
        new_msg_id = await post_board(chat_id, game, player_names, player_user_ids, context,
                                        extra_caption=extra_caption)
        save_game(chat_id, game, new_msg_id, player_names, player_user_ids)
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=old_board_message_id)
        except Exception:
            pass

    if dice_message_id:
        context.job_queue.run_once(
            lambda ctx: ctx.bot.delete_message(chat_id=chat_id, message_id=dice_message_id),
            when=10,
        )


async def cmd_endmench(update: Update, context: ContextTypes.DEFAULT_TYPE):
    delete_game(update.effective_chat.id)
    LOBBIES.pop(update.effective_chat.id, None)
    await update.message.reply_text("بازی تموم شد.")


# ---------- health-check server (for Render Web Service + UptimeRobot) ----------
from aiohttp import web


async def _health(request):
    return web.Response(text="OK")


async def start_health_server():
    app = web.Application()
    app.router.add_get("/", _health)
    app.router.add_get("/health", _health)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    log.info(f"health server listening on port {port}")


async def main():
    init_db()
    token = os.environ["BOT_TOKEN"]
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("newmench", cmd_newmench))
    application.add_handler(CommandHandler("endmench", cmd_endmench))
    application.add_handler(InlineQueryHandler(on_inline_query))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(f"^{MODE_MARKER}"), on_possible_mode_pick))
    application.add_handler(CallbackQueryHandler(on_lobby_button, pattern="^(join|startgame)$"))
    application.add_handler(CallbackQueryHandler(on_piece_choice, pattern="^move:"))
    application.add_handler(MessageHandler(filters.Dice.ALL, on_dice))

    await start_health_server()

    async with application:
        await application.start()
        await application.updater.start_polling()
        log.info("bot polling started")
        await asyncio.Event().wait()  # run forever, until the process is killed
        await application.updater.stop()
        await application.stop()


if __name__ == "__main__":
    asyncio.run(main())


if __name__ == "__main__":
    main()
