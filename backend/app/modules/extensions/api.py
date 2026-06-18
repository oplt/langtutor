from __future__ import annotations

from fastapi import APIRouter

from backend.app.modules.extensions.api_auto import router as auto_router
from backend.app.modules.extensions.api_classroom import router as classroom_router
from backend.app.modules.extensions.api_partners import router as partners_router
from backend.app.modules.extensions.api_plugins import router as plugins_router
from backend.app.modules.extensions.api_sandbox import router as sandbox_router
from backend.app.modules.extensions.api_vision import router as vision_router
from backend.app.modules.extensions.api_visualize import router as visualize_router

router = APIRouter(tags=["extensions"])

router.include_router(auto_router)
router.include_router(visualize_router)
router.include_router(vision_router)
router.include_router(partners_router)
router.include_router(classroom_router)
router.include_router(plugins_router)
router.include_router(sandbox_router)
