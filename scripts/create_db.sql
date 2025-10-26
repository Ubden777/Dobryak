-- Файл для создания таблиц БД "Добряк Бот"
-- Версия: 1.0

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    balance_stars NUMERIC(18, 2) DEFAULT 0,
    hold_stars NUMERIC(18, 2) DEFAULT 0,
    ton_wallet_address TEXT,
    referred_by_id BIGINT REFERENCES users(user_id),
    ref_bonus_paid BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Таблица заданий
CREATE TABLE IF NOT EXISTS tasks (
    task_id SERIAL PRIMARY KEY,
    owner_user_id BIGINT NOT NULL REFERENCES users(user_id),
    task_type TEXT DEFAULT 'subscribe',
    target_url TEXT NOT NULL,
    cost_per_execution NUMERIC(18, 2) NOT NULL,
    executions_needed INTEGER NOT NULL,
    executions_done INTEGER DEFAULT 0,
    task_budget_stars NUMERIC(18, 2) NOT NULL,
    hold_days INTEGER DEFAULT 7,
    status TEXT DEFAULT 'active', -- ('active', 'paused', 'completed')
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Таблица выполнений заданий
CREATE TABLE IF NOT EXISTS executions (
    execution_id SERIAL PRIMARY KEY,
    task_id INTEGER NOT NULL REFERENCES tasks(task_id),
    worker_user_id BIGINT NOT NULL REFERENCES users(user_id),
    status TEXT DEFAULT 'pending_hold', -- ('pending_hold', 'paid', 'failed_unsubscribed')
    payout_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(task_id, worker_user_id) -- Один исполнитель может выполнить задание только один раз
);

-- Таблица транзакций (для логов и заявок на вывод)
CREATE TABLE IF NOT EXISTS transactions (
    tx_id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    type TEXT NOT NULL, -- ('deposit_stars', 'withdraw_ton', 'commission', 'ref_bonus')
    amount_stars NUMERIC(18, 2),
    amount_ton NUMERIC(18, 9),
    tx_hash TEXT,
    status TEXT NOT NULL, -- ('pending', 'completed', 'failed')
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Таблица спонсорских каналов для обязательной подписки
CREATE TABLE IF NOT EXISTS sponsor_channels (
    channel_id BIGINT PRIMARY KEY,
    channel_url TEXT NOT NULL
);

-- Индексы для ускорения выборок
CREATE INDEX IF NOT EXISTS idx_executions_status_payout ON executions (status, payout_at);
CREATE INDEX IF NOT EXISTS idx_transactions_type_status ON transactions (type, status);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status);
