# ============================================
# 👨‍💼 Обработчики администратора
# ============================================
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.enums import ParseMode

from config import PLANS, ADMIN_ID
from database import (
    get_order, update_order_status, get_pending_orders,
    get_stats, get_user_orders,
)
from keyboards import admin_main_keyboard, admin_order_keyboard, review_keyboard

logger = logging.getLogger(__name__)

router = Router(name="admin")


# ============================================
# Фильтр — только админ
# ============================================
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ============================================
# /admin — Админ-панель
# ============================================
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Админ-панель."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return

    stats = get_stats()

    text = (
        f"👨‍💼 *Админ\\-панель*\n\n"
        f"📊 *Статистика:*\n"
        f"├ 📦 Всего заказов: *{stats['total_orders']}*\n"
        f"├ ✅ Выполнено: *{stats['completed']}*\n"
        f"├ ⏳ В ожидании: *{stats['pending']}*\n"
        f"├ 💰 Выручка: *{stats['revenue']}₽*\n"
        f"└ ⭐ Stars потрачено: *{stats['stars_spent']}*"
    )

    await message.answer(
        text,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=admin_main_keyboard(),
    )


# ============================================
# ✅ Подтверждение заказа — активация Premium
# ============================================
@router.callback_query(F.data.startswith("admin_confirm:"))
async def admin_confirm_order(callback: CallbackQuery, bot: Bot):
    """Админ подтверждает заказ → бот дарит Premium."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    order_id = int(callback.data.split(":")[1])
    order = get_order(order_id)

    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    if order["status"] == "completed":
        await callback.answer("ℹ️ Заказ уже выполнен", show_alert=True)
        return

    plan = PLANS[order["plan_key"]]

    # ========================================
    # 🎁 Дарим Premium через Stars
    # ========================================
    try:
        await bot.gift_premium_subscription(
            user_id=order["user_id"],
            month_count=plan["months"],
            star_count=plan["stars"],
            text=f"🎉 Ваш Telegram Premium на {plan['label']} активирован! Спасибо за покупку!",
        )

        # Обновляем статус заказа
        update_order_status(order_id, "completed")

        # Обновляем сообщение у админа
        import datetime
        now = datetime.datetime.now().strftime("%H:%M %d.%m.%Y")

        admin_text = (
            f"✅ *ЗАКАЗ \\#{order_id} ВЫПОЛНЕН*\n\n"
            f"👤 @{order['username']}\n"
            f"📅 {plan['emoji']} {plan['label']} | *{plan['price']}₽*\n"
            f"⭐ Потрачено Stars: {plan['stars']}\n"
            f"🕐 Завершён: {now}\n\n"
            f"⚡ Статус: ✅ *Выполнен*"
        )

        await callback.message.edit_text(
            admin_text,
            parse_mode=ParseMode.MARKDOWN_V2,
        )

        # ========================================
        # 📩 Уведомляем клиента
        # ========================================
        client_text = (
            f"🎉 *Заказ \\#{order_id} успешно выполнен\\!*\n\n"
            f"✅ Premium активирован на *{plan['label']}*\n"
            f"📱 Откройте настройки Telegram → Premium\n\n"
            f"🧾 Чек: {plan['price']}₽ \\| \\#{order_id} \\| {now}\n\n"
            f"⭐ Спасибо за покупку\\! Оцените наш сервис:"
        )

        await bot.send_message(
            chat_id=order["user_id"],
            text=client_text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=review_keyboard(order_id),
        )

        await callback.answer("✅ Premium подарен! Клиент уведомлён.")

    except Exception as e:
        logger.error(f"Ошибка при дарении Premium: {e}")
        error_text = str(e)

        await callback.message.edit_text(
            f"❌ *Ошибка при активации Premium\\!*\n\n"
            f"📦 Заказ \\#{order_id}\n"
            f"🔴 Ошибка: `{error_text[:200]}`\n\n"
            f"Проверьте баланс Stars бота\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=admin_order_keyboard(order_id),
        )
        await callback.answer("❌ Ошибка! Проверьте логи.", show_alert=True)


# ============================================
# ❌ Отклонение заказа
# ============================================
@router.callback_query(F.data.startswith("admin_reject:"))
async def admin_reject_order(callback: CallbackQuery, bot: Bot):
    """Админ отклоняет заказ."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    order_id = int(callback.data.split(":")[1])
    order = get_order(order_id)

    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    plan = PLANS[order["plan_key"]]

    update_order_status(order_id, "rejected", "Отклонён администратором")

    # Обновляем сообщение у админа
    await callback.message.edit_text(
        f"❌ *ЗАКАЗ \\#{order_id} ОТКЛОНЁН*\n\n"
        f"👤 @{order['username']}\n"
        f"📅 {plan['emoji']} {plan['label']} | *{plan['price']}₽*\n\n"
        f"⚡ Статус: 🔴 *Отклонён*",
        parse_mode=ParseMode.MARKDOWN_V2,
    )

    # Уведомляем клиента
    try:
        await bot.send_message(
            chat_id=order["user_id"],
            text=(
                f"❌ *Заказ \\#{order_id} отклонён*\n\n"
                f"Оплата не найдена или произошла ошибка\\.\n"
                f"Если вы уверены, что оплата прошла — свяжитесь с поддержкой\\.\n\n"
                f"Вы можете оформить новый заказ:"
            ),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=admin_order_keyboard(order_id) if False else None,
        )
    except Exception as e:
        logger.error(f"Не удалось уведомить клиента: {e}")

    await callback.answer("❌ Заказ отклонён, клиент уведомлён.")


# ============================================
# ℹ️ Детали заказа
# ============================================
@router.callback_query(F.data.startswith("admin_details:"))
async def admin_order_details(callback: CallbackQuery):
    """Показывает подробную информацию о заказе."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    order_id = int(callback.data.split(":")[1])
    order = get_order(order_id)

    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    plan = PLANS.get(order["plan_key"], {})

    status_map = {
        "pending": "🟡 Ожидает",
        "paid": "🟢 Оплачен (по словам клиента)",
        "completed": "✅ Выполнен",
        "rejected": "🔴 Отклонён",
        "cancelled": "⚫ Отменён клиентом",
    }

    # Получаем историю заказов клиента
    user_orders = get_user_orders(order["user_id"])
    completed_count = sum(1 for o in user_orders if o["status"] == "completed")

    text = (
        f"📋 *ДЕТАЛИ ЗАКАЗА \\#{order_id}*\n\n"
        f"👤 *Клиент:*\n"
        f"├ Username: @{order['username']}\n"
        f"├ Имя: {order['first_name']}\n"
        f"├ ID: `{order['user_id']}`\n"
        f"└ Завершённых заказов: {completed_count}\n\n"
        f"📦 *Заказ:*\n"
        f"├ Тариф: {plan.get('emoji', '📅')} {plan.get('label', order['plan_key'])}\n"
        f"├ Цена: {order['price']}₽\n"
        f"├ Stars: {order['stars']}\n"
        f"└ Статус: {status_map.get(order['status'], order['status'])}\n\n"
        f"🕐 *Время:*\n"
        f"├ Создан: {order['created_at']}\n"
        f"├ Обновлён: {order.get('updated_at', '—')}\n"
        f"└ Завершён: {order.get('completed_at', '—')}\n\n"
        f"📝 Заметка: {order.get('note', '—')}"
    )

    await callback.answer()

    await bot_send_or_reply(callback, text, admin_order_keyboard(order_id))


async def bot_send_or_reply(callback: CallbackQuery, text: str, markup=None):
    """Отправляет как новое сообщение, чтобы не терять историю."""
    try:
        await callback.message.answer(
            text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=markup,
        )
    except Exception:
        # Fallback: отправляем без форматирования
        await callback.message.answer(text, reply_markup=markup)


# ============================================
# 📋 Список активных заказов
# ============================================
@router.callback_query(F.data == "admin_pending")
async def admin_pending_orders(callback: CallbackQuery):
    """Список ожидающих заказов."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    orders = get_pending_orders()

    if not orders:
        await callback.answer("📭 Нет активных заказов", show_alert=True)
        return

    for order in orders[:10]:  # Максимум 10
        plan = PLANS.get(order["plan_key"], {})
        status_emoji = "🟢" if order["status"] == "paid" else "🟡"

        text = (
            f"{status_emoji} *Заказ \\#{order['id']}*\n"
            f"👤 @{order['username']} | {plan.get('label', '?')}\n"
            f"💰 {order['price']}₽ | {order['created_at']}"
        )

        await callback.message.answer(
            text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=admin_order_keyboard(order["id"]),
        )

    await callback.answer(f"📋 Найдено заказов: {len(orders)}")


# ============================================
# 📊 Статистика
# ============================================
@router.callback_query(F.data == "admin_stats")
async def admin_statistics(callback: CallbackQuery):
    """Подробная статистика."""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён", show_alert=True)
        return

    stats = get_stats()

    text = (
        f"📊 *СТАТИСТИКА*\n\n"
        f"📦 *Заказы:*\n"
        f"├ Всего: *{stats['total_orders']}*\n"
        f"├ ✅ Выполнено: *{stats['completed']}*\n"
        f"└ ⏳ В ожидании: *{stats['pending']}*\n\n"
        f"💰 *Финансы:*\n"
        f"├ 💵 Выручка: *{stats['revenue']}₽*\n"
        f"└ ⭐ Stars потрачено: *{stats['stars_spent']}*\n\n"
        f"📈 Конверсия: "
        f"*{round(stats['completed'] / max(stats['total_orders'], 1) * 100)}%*"
    )

    await callback.message.answer(
        text,
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=admin_main_keyboard(),
    )
    await callback.answer()
