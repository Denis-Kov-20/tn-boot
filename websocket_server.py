import asyncio
import websockets
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Список подключенных клиентов
connected_clients = set()

async def handle_client(websocket):
    """Обрабатывает подключение клиента."""
    connected_clients.add(websocket)
    logger.info(f"Клиент подключен: {websocket.remote_address}, всего клиентов: {len(connected_clients)}")
    try:
        async for message in websocket:
            logger.info(f"Получено сообщение: {message}")
            # Пересылаем сообщение всем подключенным клиентам
            if len(connected_clients) > 1:
                for client in connected_clients.copy():  # Копируем, чтобы избежать изменений во время итерации
                    if client != websocket:
                        try:
                            await client.send(message)
                            logger.info(f"Отправлено сообщение клиенту: {client.remote_address}")
                        except websockets.exceptions.ConnectionClosed:
                            logger.info(f"Клиент {client.remote_address} уже отключен")
                            connected_clients.discard(client)
                        except Exception as e:
                            logger.error(f"Ошибка отправки клиенту {client.remote_address}: {e}")
                    else:
                        logger.info(f"Пропущен клиент: {client.remote_address} (тот же клиент)")
            else:
                logger.info("Нет других клиентов для пересылки сообщения")
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"Клиент отключен: {websocket.remote_address}")
    except Exception as e:
        logger.error(f"Ошибка обработки клиента: {e}")
    finally:
        connected_clients.discard(websocket)
        logger.info(f"Клиент удален, осталось клиентов: {len(connected_clients)}")

async def main():
    """Запускает WebSocket-сервер."""
    try:
        server = await websockets.serve(handle_client, "localhost", 8765)
        logger.info("WebSocket-сервер запущен на ws://localhost:8765")
        await server.wait_closed()
    except Exception as e:
        logger.error(f"Ошибка сервера: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Сервер остановлен")
    except Exception as e:
        logger.error(f"Ошибка запуска сервера: {e}")