from aiogram.fsm.state import State, StatesGroup

class Registration(StatesGroup):
    waiting_for_parent_code = State()

class ParentSettings(StatesGroup): 
    waiting_for_custom_rate = State()
    waiting_for_child_age = State()
    waiting_for_coin_deduction = State()
    waiting_for_coin_addition = State()
    waiting_for_parent_pin = State()

class PlanCreation(StatesGroup):
    waiting_for_child = State()
    waiting_for_mode = State()
    waiting_for_marathon_name = State()
    waiting_for_marathon_prize = State()
    waiting_for_book_text = State()
    waiting_for_book_photo = State()

class PlanEditing(StatesGroup):
    waiting_for_new_name = State()
    waiting_for_new_prize = State()
    waiting_for_new_child = State()

class AITestCreation(StatesGroup):
    waiting_for_page_photo = State()

class ChildReading(StatesGroup):
    waiting_for_page_photo = State()
    waiting_for_audio = State()
    waiting_for_manual_page = State()

class BolaxonaMode(StatesGroup):
    waiting_for_pin_to_exit = State()

class ManualBookOverride(StatesGroup):
    waiting_for_manual_title = State()

class StoreSettings(StatesGroup):
    waiting_for_item_name = State()
    waiting_for_item_price = State()

class Feedback(StatesGroup):
    waiting_for_message = State()
