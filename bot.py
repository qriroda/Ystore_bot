import asyncio
import logging
import sys
import os

# ПРИНУДИТЕЛЬНАЯ НАСТРОЙКА ПУТЕЙ ДЛЯ RENDER
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# Загружаем конфиг после настройки путей
try:
    from config import BOT_TOKEN, PROXY_URL
    from database import init_db
    from handlers.client import router as client_router
    from handlers.admin import router as admin_router
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print(f"Текущая директория: {os.getcwd()}")
    print(f"Список файлов: {os.listdir(current_dir)}")
    raise

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

async def main():
    init_db()

    session = None
    if PROXY_URL:
        from aiogram.client.session.aiohttp import AiohttpSession
        if PROXY_URL.startswith("socks"):
            from aiohttp_socks import ProxyConnector
            connector = ProxyConnector.from_url(PROXY_URL)
            session = AiohttpSession(connector=connector)
        else:
            session = AiohttpSession()

    bot = Bot(
        token=BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()
    dp.include_router(admin_router)
    dp.include_router(client_router)

    # Веб-заглушка для Render
    from aiohttp import web
    async def health_check(request):
        return web.Response(text="Bot is online!")
    
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    bot_info = await bot.get_me()
    logger.info(f"🤖 Бот запущен: @{bot_info.username}")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
