from aiogram import Router
from handlers.registration import router as registration_router
from handlers.main_menu import router as main_menu_router
from handlers.payment import router as payment_router
from handlers.admin import router as admin_router


def setup_routers() -> Router:
    root_router = Router()
    root_router.include_router(admin_router)
    root_router.include_router(registration_router)
    root_router.include_router(main_menu_router)
    root_router.include_router(payment_router)
    return root_router
