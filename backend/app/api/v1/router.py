from fastapi import APIRouter, Depends

from app.api.v1.endpoints import (
    auth,
    especialidades,
    medicos,
    pacientes,
    solicitudes_cancelacion,
    system,
    turnos,
)
from app.core.csrf import verificar_csrf

# El CSRF se declara una sola vez acá: todo router incluido hereda la
# dependencia, así que un endpoint nuevo queda protegido sin acordarse de nada.
api_router = APIRouter(dependencies=[Depends(verificar_csrf)])
api_router.include_router(system.router)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(pacientes.router, prefix="/pacientes", tags=["pacientes"])
api_router.include_router(especialidades.router, prefix="/especialidades", tags=["especialidades"])
api_router.include_router(medicos.router, prefix="/medicos", tags=["medicos"])
api_router.include_router(turnos.router, prefix="/turnos", tags=["turnos"])
api_router.include_router(
    solicitudes_cancelacion.router,
    prefix="/solicitudes-cancelacion",
    tags=["solicitudes-cancelacion"],
)
