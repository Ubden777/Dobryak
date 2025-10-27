from aiogram.fsm.state import State, StatesGroup

class ExecuteTaskState(StatesGroup):
    """
    Состояния для FSM выполнения задания исполнителем.
    """
    viewing_task = State() # Просмотр предложенного задания
    checking_subscription = State() # Проверка подписки
