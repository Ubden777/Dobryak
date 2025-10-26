from aiogram.fsm.state import State, StatesGroup

class CreateTaskState(StatesGroup):
    """
    Состояния для FSM создания нового задания.
    """
    choosing_task_type = State()
    getting_url = State()
    checking_admin = State()
    getting_cost = State()
    getting_amount = State()
    confirming = State()
