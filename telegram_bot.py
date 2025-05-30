import asyncio
import logging
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from aiohttp import web, WSMsgType
from concurrent.futures import ThreadPoolExecutor

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота из переменной окружения
TOKEN = os.getenv("BOT_TOKEN")

# Список подключенных WebSocket-клиентов
connected_clients = set()

async def websocket_handler(request):
    """Обрабатывает WebSocket-соединения через /ws."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    connected_clients.add(ws)
    logger.info(f"Клиент подключен, всего клиентов: {len(connected_clients)}")
    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                logger.info(f"Получено сообщение: {msg.data}")
                if len(connected_clients) > 1:
                    for client in connected_clients.copy():
                        if client != ws and not client.closed:
                            try:
                                await client.send_str(msg.data)
                                logger.info(f"Отправлено сообщение клиенту")
                            except Exception as e:
                                logger.error(f"Ошибка отправки клиенту: {e}")
                                connected_clients.discard(client)
                else:
                    logger.info("Нет других клиентов для пересылки сообщения")
            elif msg.type == WSMsgType.ERROR:
                logger.error(f"Ошибка WebSocket: {ws.exception()}")
    except Exception as e:
        logger.error(f"Ошибка обработки клиента: {e}")
    finally:
        connected_clients.discard(ws)
        logger.info(f"Клиент отключен, осталось клиентов: {len(connected_clients)}")
    return ws

async def start_bot():
    """Запускает Telegram-бота."""
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Остановка бота...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение с основными кнопками."""
    keyboard = [
        [
            InlineKeyboardButton("ФПВ", callback_data="fpv"),
            InlineKeyboardButton("АРТ-ОБСТРІЛ", callback_data="art"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    main_message = await update.message.reply_text("Виберіть опцію:", reply_markup=reply_markup)
    context.chat_data["main_message_id"] = main_message.message_id

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    button_actions = {
        "fpv": {
            "message": "ФПВ обрано",
            "sound": "fpv_sound",
            "sub_buttons": [
                InlineKeyboardButton("Напрямок Нікополь", callback_data="fpv_1"),
                InlineKeyboardButton("Берегова лінія стара частина", callback_data="fpv_2"),
                InlineKeyboardButton("Богдан", callback_data="fpv_3"),
                InlineKeyboardButton("Напрямок 4", callback_data="fpv_4"),
                InlineKeyboardButton("Напрямок 5", callback_data="fpv_5"),
            ],
        },
        "art": {
            "message": "АРТ-ОБСТРІЛ обрано",
            "sound": "art_sound",
            "sub_buttons": [
                InlineKeyboardButton("стара частина", callback_data="art_1"),
                InlineKeyboardButton("Сектор 2", callback_data="art_2"),
                InlineKeyboardButton("Сектор 3", callback_data="art_3"),
                InlineKeyboardButton("Сектор 4", callback_data="art_4"),
                InlineKeyboardButton("Сектор 5", callback_data="art_5"),
                InlineKeyboardButton("Сектор 6", callback_data="art_6"),
            ],
        },
        "fpv_1": {"message": "ФПВ: Напрямок Нікополь", "sound": "fpv_sound_1"},
        "fpv_2": {"message": "ФПВ: Берегова лінія стара частина", "sound": "fpv_sound_2"},
        "fpv_3": {"message": "ФПВ: Богдан", "sound": "fpv_sound_3"},
        "fpv_4": {"message": "ФПВ: Напрямок 4", "sound": "fpv_sound_4"},
        "fpv_5": {"message": "ФПВ: Напрямок 5", "sound": "fpv_sound_5"},
        "art_1": {"message": "АРТ-ОБСТРІЛ: стара частина", "sound": "art_sound_1"},
        "art_2": {"message": "АРТ-ОБСТРІЛ: Сектор 2", "sound": "art_sound_2"},
        "art_3": {"message": "АРТ-ОБСТРІЛ: Сектор 3", "sound": "art_sound_3"},
        "art_4": {"message": "АРТ-ОБСТРІЛ: Сектор 4", "sound": "art_sound_4"},
        "art_5": {"message": "АРТ-ОБСТРІЛ: Сектор 5", "sound": "art_sound_5"},
        "art_6": {"message": "АРТ-ОБСТРІЛ: Сектор 6", "sound": "art_sound_6"},
    }

    action = button_actions.get(query.data)
    if action:
        logger.info(f"Отправка команды на WebSocket: {action['sound']}")
        for client in connected_clients.copy():
            if not client.closed:
                try:
                    await client.send_str(action["sound"])
                    logger.info(f"Команда {action['sound']} отправлена")
                except Exception as e:
                    logger.error(f"Ошибка отправки: {e}")
                    connected_clients.discard(client)

        temp_message = await query.message.reply_text(action["message"])
        asyncio.create_task(delete_message_after_delay(context, temp_message.chat_id, temp_message.message_id, 3))

        if "sub_buttons" in action:
            keyboard = [action["sub_buttons"][i:i+2] for i in range(0, len(action["sub_buttons"]), 2)]
            reply_markup = InlineKeyboardMarkup(keyboard)
            if "sub_message_id" in context.chat_data:
                try:
                    await context.bot.edit_message_text(
                        chat_id=query.message.chat_id,
                        message_id=context.chat_data["sub_message_id"],
                        text="Виберіть додаткову опцію:",
                        reply_markup=reply_markup
                    )
                except Exception as e:
                    logger.error(f"Ошибка при редактировании дополнительных кнопок: {e}")
                    sub_message = await query.message.reply_text("Виберіть додаткову опцію:", reply_markup=reply_markup)
                    context.chat_data["sub_message_id"] = sub_message.message_id
            else:
                sub_message = await query.message.reply_text("Виберіть додаткову опцію:", reply_markup=reply_markup)
                context.chat_data["sub_message_id"] = sub_message.message_id

async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int) -> None:
    """Удаляет сообщение после указанной задержки."""
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"Сообщение {message_id} удалено")
    except Exception as e:
        logger.error(f"Ошибка при удалении сообщения {message_id}: {e}")

async def main():
    """Запускает бота и WebSocket-сервер."""
    app = web.Application()
    app.router.add_get('/ws', websocket_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.getenv('PORT', 8080)))
    await site.start()
    logger.info(f"WebSocket-сервер запущен на ws://0.0.0.0:{os.getenv('PORT', 8080)}/ws")
    
    with ThreadPoolExecutor() as executor:
        loop = asyncio.get_event_loop()
        loop.run_in_executor(executor, lambda: asyncio.run(start_bot()))

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Ошибка запуска: {e}")