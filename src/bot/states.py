from aiogram.fsm.state import State, StatesGroup


class AddProjectStates(StatesGroup):
    """States for the add project flow."""

    waiting_for_url = State()

