import asyncio
import websockets
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Токен бота, полученный от @BotFather
TOKEN = "7915084633:AAFYbQeFHdFlBIxavaHV94b39RtUkrA8PGQ"

# URL WebSocket-сервера
WEBSOCKET_URL = "ws://localhost:8765"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение с основными кнопками."""
    keyboard = [
        [
            InlineKeyboardButton("ФПВ", callback_data="fpv"),
            InlineKeyboardButton("АРТ-ОБСТРІЛ", callback_data="art"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Сохраняем сообщение с основными кнопками
    main_message = await update.message.reply_text("Виберіть опцію:", reply_markup=reply_markup)
    context.chat_data["main_message_id"] = main_message.message_id

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    # Определяем действия для кнопок
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
        # Отправляем команду через WebSocket
        print(f"Отправка команды на WebSocket: {action['sound']}")
        try:
            async with websockets.connect(WEBSOCKET_URL) as websocket:
                await websocket.send(action["sound"])
                print(f"Команда {action['sound']} отправлена")
        except Exception as e:
            print(f"Ошибка WebSocket: {e}")

        # Отправляем временное сообщение с действием
        temp_message = await query.message.reply_text(action["message"])
        asyncio.create_task(delete_message_after_delay(context, temp_message.chat_id, temp_message.message_id, 3))

        # Обновляем или создаем сообщение с дополнительными кнопками
        if "sub_buttons" in action:
            # Разбиваем кнопки на пары для компактного отображения
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
                    print(f"Ошибка при редактировании дополнительных кнопок: {e}")
                    sub_message = await query.message.reply_text("Виберіть додаткову опцію:", reply_markup=reply_markup)
                    context.chat_data["sub_message_id"] = sub_message.message_id
            else:
                sub_message = await query.message.reply_text("Виберіть додаткову опцію:", reply_markup=reply_markup)
                context.chat_data["sub_message_id"] = sub_message.message_id
        else:
            # Если выбрана дополнительная кнопка, не меняем дополнительные кнопки
            pass

async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int) -> None:
    """Удаляет сообщение после указанной задержки."""
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        print(f"Сообщение {message_id} удалено")
    except Exception as e:
        print(f"Ошибка при удалении сообщения {message_id}: {e}")

async def main() -> None:
    """Запускает бота."""
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Запуск polling
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    # Держим бота активным
    try:
        while True:
            await asyncio.sleep(3600)  # Спим 1 час, чтобы не завершать цикл
    except KeyboardInterrupt:
        print("Остановка бота...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

def run_bot():
    """Запускает бота в текущем событийном цикле."""
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # Если цикл уже работает, создаем задачу
        loop.create_task(main())
    else:
        # Если цикл не запущен, используем run_until_complete
        loop.run_until_complete(main())

if __name__ == "__main__":
    try:
        run_bot()
    except Exception as e:
        print(f"Ошибка запуска бота: {e}")