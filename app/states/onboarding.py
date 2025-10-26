from aiogram.fsm.state import State, StatesGroup

class OnboardingState(StatesGroup):
    """
    Состояния для процесса онбординга нового пользователя.
    """

    # Состояние, в котором бот ожидает, пока пользователь подпишется на спонсорский канал
    waiting_for_subscription = State()

    # Финальное состояние после успешной подписки
    subscription_complete = State()
