from fastapi import APIRouter

from .schemas import LabRequest, LabResult
from .service import analyze

router = APIRouter(prefix="/decision-lab", tags=["BreakPoint AI"])
router.add_api_route("/analyze", analyze, methods=["POST"], response_model=LabResult)
