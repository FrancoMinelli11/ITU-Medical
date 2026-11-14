from fastapi import APIRouter, Depends

from app.api.v1.endpoints import auth, pacientes, system
from app.core.csrf import verificar_csrf

# El CSRF se declara una sola vez acá: todo router incluido hereda la
# dependencia, así que un endpoint nuevo queda protegido sin acordarse de nada.
api_router = APIRouter(dependencies=[Depends(verificar_csrf)])
api_router.include_router(system.router)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(pacientes.router, prefix="/pacientes", tags=["pacientes"])
