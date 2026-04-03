# ============================================
# 👤 Обработчики клиента
# ============================================
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode

from config import PLANS, WELCOME_TEXT, REVIEWS_TEXT, SUPPORT_TEXT, ADMIN_ID, PAYMENT_INSTRUCTIONS
from database import create_order, get_order, update_order_status, add_review
from keyboards import (
    main_menu_keyboard, plan_confirm_keyboard, payment_keyboard,
    review_keyboard, back_to_menu_keyboard, admin_order_keyboard,
)

logger = logging.getLogger(__name__)

router = Router(name="client")


# ============================================
# /start — Приветствие
# ============================================
@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start."""
    await message.answer(
        WELCOME_TEXT,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard(),
    )


# ============================================
# Выбор тарифа
# ============================================
@router.callback_query(F.data.startswith("plan:"))
async def select_plan(callback: CallbackQuery):
    """Клиент выбирает тариф."""
    plan_key = callback.data.split(":")[1]
    plan = PLANS.get(plan_key)

    if not plan:
        await callback.answer("❌ Тариф не найден", show_alert=True)
        return

    text = (
        f"✅ *Вы выбрали: {plan['label']} Premium*\n\n"
        f"💰 Итоговая цена: *{plan['price']} рублей*\n"
        f"⭐ Stars для активации: {plan['stars']}\n"
        f"⏱️ Выдача: *1–3 минуты* после подтверждения оплаты\n\n"
        f"Нажмите «💳 Перейти к оплате», чтобы продолжить."
    )

    await callback.message.edit_text(
        text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=plan_confirm_keyboard(plan_key),
    )
    await callback.answer()


# ============================================
# Переход к оплате — создание заказа
# ============================================
@router.callback_query(F.data.startswith("pay:"))
async def process_payment(callback: CallbackQuery, bot: Bot):
    """Создаёт заказ и показывает инструкцию по оплате."""
    plan_key = callback.data.split(":")[1]
    plan = PLANS.get(plan_key)

    if not plan:
        await callback.answer("❌ Тариф не найден", show_alert=True)
        return

    user = callback.from_user

    # Создаём заказ в БД
    order_id = create_order(
        user_id=user.id,
        username=user.username or "нет username",
        first_name=user.first_name or "Без имени",
        plan_key=plan_key,
        months=plan["months"],
        price=plan["price"],
        stars=plan["stars"],
    )

    # Формируем инструкцию по оплате
    payment_text = PAYMENT_INSTRUCTIONS.format(
        price=plan["price"],
        order_id=order_id,
    )

    order_text = (
        f"📦 *Заказ \\#{order_id}*\n\n"
        f"📅 Тариф: {plan['emoji']} {plan['label']}\n"
        f"💰 Сумма: *{plan['price']}₽*\n\n"
        f"{payment_text}\n\n"
        f"⏳ После оплаты нажмите «✅ Я оплатил»"
    )

    await callback.message.edit_text(
        order_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=payment_keyboard(order_id, plan_key),
    )

    # ========================================
    # 📩 Уведомление администратору
    # ========================================
    import datetime
    now = datetime.datetime.now().strftime("%H:%M")

    admin_text = (
        f"👨‍💼 *НОВЫЙ ЗАКАЗ \\#{order_id}*\n\n"
        f"👤 Клиент: @{user.username or 'без username'}\n"
        f"📛 Имя: {user.first_name or 'Не указано'}\n"
        f"🆔 ID: `{user.id}`\n"
        f"📅 {plan['emoji']} {plan['label']} | *{plan['price']}₽*\n"
        f"⏰ {now} | Ожидает оплаты\n\n"
        f"⚡ Статус: 🟡 *Ожидает*"
    )

    if ADMIN_ID:
        try:
            admin_msg = await bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=admin_order_keyboard(order_id),
            )
            # Сохраним message_id для дальнейшего редактирования
            from database import set_admin_message_id
            set_admin_message_id(order_id, admin_msg.message_id)
        except Exception as e:
            logger.error(f"Не удалось отправить уведомление админу: {e}")

    await callback.answer()


# ============================================
# Клиент нажал "Я оплатил"
# ============================================
@router.callback_query(F.data.startswith("paid:"))
async def client_paid(callback: CallbackQuery, bot: Bot):
    """Клиент подтвердил оплату."""
    order_id = int(callback.data.split(":")[1])
    order = get_order(order_id)

    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    if order["status"] not in ("pending",):
        await callback.answer("ℹ️ Заказ уже обработан", show_alert=True)
        return

    # Обновляем статус
    update_order_status(order_id, "paid")

    await callback.message.edit_text(
        f"⏳ *Оплата отправлена\\! Заказ \\#{order_id}*\n\n"
        f"Ожидаю подтверждения администратора\\.\\.\\.\n"
        f"⏱️ Обычно это занимает *1–2 минуты*\n\n"
        f"📋 Тариф: {PLANS[order['plan_key']]['label']}\n"
        f"💰 Сумма: {order['price']}₽",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=back_to_menu_keyboard(),
    )

    # Обновляем сообщение у админа
    if ADMIN_ID and order.get("admin_message_id"):
        try:
            user = callback.from_user
            plan = PLANS[order["plan_key"]]

            admin_text = (
                f"🔔 *ОПЛАТА ПОДТВЕРЖДЕНА КЛИЕНТОМ*\n\n"
                f"📦 Заказ \\#{order_id}\n"
                f"👤 @{user.username or 'без username'}\n"
                f"📅 {plan['emoji']} {plan['label']} | *{plan['price']}₽*\n\n"
                f"⚡ Статус: 🟢 *Клиент оплатил*\n\n"
                f"✅ Проверьте поступление и подтвердите\\!"
            )

            await bot.edit_message_text(
                chat_id=ADMIN_ID,
                message_id=order["admin_message_id"],
                text=admin_text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=admin_order_keyboard(order_id),
            )
        except Exception as e:
            logger.error(f"Не удалось обновить сообщение админа: {e}")

    await callback.answer("✅ Администратор уведомлён!")


# ============================================
# Отмена заказа клиентом
# ============================================
@router.callback_query(F.data.startswith("cancel:"))
async def cancel_order(callback: CallbackQuery):
    """Клиент отменяет заказ."""
    order_id = int(callback.data.split(":")[1])
    order = get_order(order_id)

    if not order:
        await callback.answer("❌ Заказ не найден", show_alert=True)
        return

    if order["status"] in ("completed", "rejected"):
        await callback.answer("ℹ️ Заказ уже обработан", show_alert=True)
        return

    update_order_status(order_id, "cancelled", "Отменён клиентом")

    await callback.message.edit_text(
        f"❌ *Заказ \\#{order_id} отменён*\n\n"
        f"Вы можете оформить новый заказ в любое время\\.",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=back_to_menu_keyboard(),
    )
    await callback.answer("Заказ отменён")


# ============================================
# Отзыв клиента
# ============================================
@router.callback_query(F.data.startswith("review:"))
async def leave_review(callback: CallbackQuery):
    """Клиент оставляет отзыв."""
    parts = callback.data.split(":")
    order_id = int(parts[1])
    rating = parts[2]  # positive / negative

    user = callback.from_user
    add_review(
        order_id=order_id,
        user_id=user.id,
        username=user.username or "аноним",
        rating=rating,
    )

    emoji = "👍" if rating == "positive" else "👎"

    await callback.message.edit_text(
        f"🙏 *Спасибо за отзыв\\!* {emoji}\n\n"
        f"Ваше мнение очень важно для нас\\.\n"
        f"Будем рады видеть вас снова\\!",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=back_to_menu_keyboard(),
    )
    await callback.answer("Спасибо за отзыв!")


# ============================================
# Отзывы и поддержка
# ============================================
@router.callback_query(F.data == "reviews")
async def show_reviews(callback: CallbackQuery):
    """Показывает отзывы."""
    await callback.message.edit_text(
        REVIEWS_TEXT,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_to_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "support")
async def show_support(callback: CallbackQuery):
    """Показывает контакты поддержки."""
    await callback.message.edit_text(
        SUPPORT_TEXT,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_to_menu_keyboard(),
    )
    await callback.answer()


# ============================================
# Назад в меню
# ============================================
@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    """Возврат в главное меню."""
    await callback.message.edit_text(
        WELCOME_TEXT,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()
