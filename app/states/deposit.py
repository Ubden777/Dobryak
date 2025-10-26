from aiogram.fsm.state import State, StatesGroup

class DepositState(StatesGroup):
    """
    Состояния для процесса пополнения баланса.
    """
    choosing_package = State()
