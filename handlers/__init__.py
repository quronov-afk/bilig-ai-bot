from aiogram import Router
from .common import router as common_router
from .admin import router as admin_router
from .feedback import router as feedback_router
from .parent import router as parent_router
from .child import router as child_router

main_router = Router()
main_router.include_routers(
    common_router,
    admin_router,
    feedback_router,
    parent_router,
    child_router
)
