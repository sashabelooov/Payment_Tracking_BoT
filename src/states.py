from aiogram.fsm.state import State, StatesGroup


class UserState(StatesGroup):
    language = State()
    phone = State()
    fio = State()
    confirm = State()
    main_menu = State()
    payment_menu = State()
    payment_method = State()
    # Course browsing
    course_list = State()
    course_detail = State()
    course_payment_method = State()
    # Language change
    change_language = State()


class AdminState(StatesGroup):
    menu = State()
    broadcast = State()
    # Course creation FSM
    course_title = State()
    course_description = State()
    course_start_date = State()
    course_end_date = State()
    course_months_count = State()
    course_total_amount = State()
    course_group_id = State()
    course_invite_link = State()
    course_confirm = State()
    # Excel export
    export_select_course = State()
    # Language change
    change_language = State()
