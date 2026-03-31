# ============================================
# 🤖 Telegram Premium Store Bot
# ============================================
# Точка входа — запуск бота
# ============================================

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from database import init_db
from handlers.client import router as client_router
from handlers.admin import router as admin_router

# ============================================
# 📝 Настройка логирования
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота."""

    # Инициализация базы данных
    logger.info("📦 Инициализация базы данных...")
    init_db()

    # Настройка прокси
    from config import BOT_TOKEN, PROXY_URL
    session = None
    if PROXY_URL:
        logger.info(f"🌐 Используем прокси: {PROXY_URL}")
        from aiogram.client.session.aiohttp import AiohttpSession
        if PROXY_URL.startswith("socks"):
            from aiohttp_socks import ProxyConnector
            connector = ProxyConnector.from_url(PROXY_URL)
            session = AiohttpSession(connector=connector)
        else:
            session = AiohttpSession()
            # Для обычного HTTP(S) прокси можно передать его в сам bot (через session)
            # Но для aiogram 3.x проще использовать коннектор

    # Создание бота
    bot = Bot(
        token=BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Создание диспетчера
    dp = Dispatcher()

    # Подключение роутеров
    dp.include_router(admin_router)   # Админ — приоритет выше
    dp.include_router(client_router)  # Клиент

    # Информация о боте
    bot_info = await bot.get_me()
    logger.info(f"🤖 Бот запущен: @{bot_info.username} ({bot_info.full_name})")
    logger.info(f"🆔 Bot ID: {bot_info.id}")

    # ============================================
    # 🌐 Запуск заглушки веб-сервера (для Render.com)
    # ============================================
    from aiohttp import web
    async def health_check(request):
        return web.Response(text="Bot is running 24/7!")
    
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render автоматически задает переменную PORT
    import os
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    logger.info(f"🌐 Fake Web-Server запущен на порту {port}")

    # Запуск polling телеграма
    logger.info("🚀 Запуск polling...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        logger.info("🛑 Бот остановлен.")
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем.")
