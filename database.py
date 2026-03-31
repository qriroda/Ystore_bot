# ============================================
# 🗃️ Модуль базы данных — SQLite
# ============================================
import sqlite3
import datetime
from config import DATABASE_PATH


def get_connection():
    """Создаёт соединение с базой данных."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Инициализация базы данных — создание таблиц."""
    conn = get_connection()
    cursor = conn.cursor()

    # Таблица заказов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            first_name TEXT,
            plan_key TEXT NOT NULL,
            months INTEGER NOT NULL,
            price INTEGER NOT NULL,
            stars INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            admin_message_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            completed_at TEXT,
            note TEXT
        )
    """)

    # Таблица отзывов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            username TEXT,
            rating TEXT,
            text TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    """)

    # Статистика
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stats (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    conn.commit()
    conn.close()


# ============================================
# 📦 CRUD операции с заказами
# ============================================

def create_order(user_id: int, username: str, first_name: str,
                 plan_key: str, months: int, price: int, stars: int) -> int:
    """Создаёт новый заказ и возвращает его ID."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO orders (user_id, username, first_name, plan_key, months, price, stars, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?)
    """, (user_id, username, first_name, plan_key, months, price, stars, now))

    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id


def get_order(order_id: int) -> dict:
    """Получает заказ по ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_order_status(order_id: int, status: str, note: str = None):
    """Обновляет статус заказа."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if status == "completed":
        cursor.execute("""
            UPDATE orders SET status = ?, updated_at = ?, completed_at = ?, note = ?
            WHERE id = ?
        """, (status, now, now, note, order_id))
    else:
        cursor.execute("""
            UPDATE orders SET status = ?, updated_at = ?, note = ?
            WHERE id = ?
        """, (status, now, note, order_id))

    conn.commit()
    conn.close()


def set_admin_message_id(order_id: int, message_id: int):
    """Сохраняет ID сообщения админа для последующего редактирования."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE orders SET admin_message_id = ? WHERE id = ?
    """, (message_id, order_id))
    conn.commit()
    conn.close()


def get_pending_orders() -> list:
    """Получает все ожидающие заказы."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM orders WHERE status IN ('pending', 'paid')
        ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_user_orders(user_id: int) -> list:
    """Получает все заказы пользователя."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM orders WHERE user_id = ?
        ORDER BY created_at DESC
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats() -> dict:
    """Возвращает общую статистику."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM orders")
    total = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as completed FROM orders WHERE status = 'completed'")
    completed = cursor.fetchone()["completed"]

    cursor.execute("SELECT COUNT(*) as pending FROM orders WHERE status IN ('pending', 'paid')")
    pending = cursor.fetchone()["pending"]

    cursor.execute("SELECT COALESCE(SUM(price), 0) as revenue FROM orders WHERE status = 'completed'")
    revenue = cursor.fetchone()["revenue"]

    cursor.execute("SELECT COALESCE(SUM(stars), 0) as stars_spent FROM orders WHERE status = 'completed'")
    stars_spent = cursor.fetchone()["stars_spent"]

    conn.close()

    return {
        "total_orders": total,
        "completed": completed,
        "pending": pending,
        "revenue": revenue,
        "stars_spent": stars_spent,
    }


def add_review(order_id: int, user_id: int, username: str, rating: str, text: str = None):
    """Добавляет отзыв."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO reviews (order_id, user_id, username, rating, text, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (order_id, user_id, username, rating, text, now))

    conn.commit()
    conn.close()


def get_reviews(limit: int = 10) -> list:
    """Получает последние отзывы."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.*, o.plan_key, o.months, o.price
        FROM reviews r
        JOIN orders o ON r.order_id = o.id
        ORDER BY r.created_at DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
