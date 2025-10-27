import pytest
import asyncpg
import os
from decimal import Decimal
from unittest.mock import Mock

from app.db.queries import add_user, get_user
from app.handlers.deposit import successful_payment

# Фикстура для создания и очистки тестовой БД
@pytest.fixture(scope="module")
async def db_pool():
    pool = await asyncpg.create_pool(
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
    )
    # Очистка перед тестами (на всякий случай)
    async with pool.acquire() as conn:
        await conn.execute("DROP TABLE IF EXISTS transactions, executions, tasks, users, sponsor_channels CASCADE;")
        with open("scripts/create_db.sql", "r") as f:
            await conn.execute(f.read())

    yield pool

    pool.close()


@pytest.mark.asyncio
async def test_successful_payment_idempotency(db_pool):
    """
    Проверяет, что обработчик successful_payment идемпотентен
    и не начисляет средства дважды за один и тот же платеж.
    """
    test_user_id = 12345
    test_username = "testuser"
    initial_balance = Decimal("0.00")
    payment_amount = Decimal("100.00")
    charge_id = "test_charge_id_123"

    # 1. Создаем пользователя
    await add_user(db_pool, test_user_id, test_username)

    # 2. Создаем мок сообщения от Telegram
    successful_payment_mock = Mock()
    successful_payment_mock.total_amount = int(payment_amount)
    successful_payment_mock.telegram_payment_charge_id = charge_id

    message_mock = Mock()
    message_mock.from_user.id = test_user_id
    message_mock.successful_payment = successful_payment_mock
    message_mock.answer = Mock() # Мокаем метод answer

    # 3. Вызываем обработчик ПЕРВЫЙ раз
    await successful_payment(message_mock, db_pool)

    # 4. Проверяем, что баланс обновился
    user_after_first_payment = await get_user(db_pool, test_user_id)
    assert user_after_first_payment["balance_stars"] == initial_balance + payment_amount

    # 5. Вызываем обработчик ВТОРОЙ раз с теми же данными
    await successful_payment(message_mock, db_pool)

    # 6. Проверяем, что баланс НЕ изменился
    user_after_second_payment = await get_user(db_pool, test_user_id)
    assert user_after_second_payment["balance_stars"] == initial_balance + payment_amount

    # 7. Проверяем, что было вызвано сообщение об ошибке
    message_mock.answer.assert_called_with("Этот платеж уже был обработан.")
