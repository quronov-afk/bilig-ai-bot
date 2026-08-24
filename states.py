from aiogram.fsm.state import State, StatesGroup

class Registration(StatesGroup):
    waiting_for_parent_code = State()

class ParentSettings(StatesGroup): 
    waiting_for_custom_rate = State()
    waiting_for_child_age = State()
    waiting_for_coin_deduction = State()

class PlanCreation(StatesGroup):
    waiting_for_child = State()
    waiting_for_name = State()
    waiting_for_prize = State()
    waiting_for_deadline = State()
    waiting_for_book_text = State()
    waiting_for_book_photo = State()

class AITestCreation(StatesGroup):
    waiting_for_page_photo = State()

class ChildReading(StatesGroup):
    waiting_for_page_photo = State()
    waiting_for_audio = State()

class StoreSettings(StatesGroup):
    waiting_for_item_name = State()
    waiting_for_item_price = State()

class Feedback(StatesGroup):
    waiting_for_message = State()
