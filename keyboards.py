# ============================================
# ⌨️ Клавиатуры (Inline Keyboards)
# ============================================
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from config import PLANS, TBANK_PAYMENT_URL


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню с тарифами."""
    buttons = []
    for key, plan in PLANS.items():
        buttons.append([
            InlineKeyboardButton(
                text=f"{plan['emoji']} {plan['label']} — {plan['price']}₽",
                callback_data=f"plan:{key}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(text="⭐ Отзывы клиентов", callback_data="reviews"),
        InlineKeyboardButton(text="📞 Связаться", url="https://t.me/namyayanami"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def plan_confirm_keyboard(plan_key: str) -> InlineKeyboardMarkup:
    """Подтверждение выбранного тарифа."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="💳 Перейти к оплате",
            callback_data=f"pay:{plan_key}"
        )],
        [InlineKeyboardButton(
            text="🔙 Выбрать другой тариф",
            callback_data="back_to_menu"
        )],
    ])


def payment_keyboard(order_id: int, plan_key: str) -> InlineKeyboardMarkup:
    """Клавиатура оплаты через Ozon."""
    plan = PLANS[plan_key]
    buttons = [
        # Ссылка на Ozon (открывается в браузере / WebView)
        [InlineKeyboardButton(
            text="💳 Оплатить картой / T-Pay",
            url=TBANK_PAYMENT_URL
        )],
        [InlineKeyboardButton(
            text="✅ Я оплатил",
            callback_data=f"paid:{order_id}"
        )],
        [InlineKeyboardButton(
            text="❌ Отменить заказ",
            callback_data=f"cancel:{order_id}"
        )],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def review_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для оценки заказа."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍 Отлично!", callback_data=f"review:{order_id}:positive"),
            InlineKeyboardButton(text="👎 Есть проблемы", callback_data=f"review:{order_id}:negative"),
        ]
    ])


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Кнопка назад в меню."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Вернуться в меню", callback_data="back_to_menu")]
    ])


# ============================================
# 👨‍💼 Админ-клавиатуры
# ============================================

def admin_order_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Клавиатура управления заказом для админа."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"admin_confirm:{order_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"admin_reject:{order_id}"),
        ],
        [
            InlineKeyboardButton(text="ℹ️ Детали", callback_data=f"admin_details:{order_id}"),
        ],
    ])


def admin_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню админ-панели."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Активные заказы", callback_data="admin_pending")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📜 Все заказы", callback_data="admin_all_orders")],
    ])
