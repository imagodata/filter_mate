"""/processing — find, describe and run the Processing algorithms the agent may run.

What may run is decided in ``core/agent/processing_policy.py``: algorithms of QGIS itself that make layers, on
layers of the project, their outputs written to temporary files and added to the project.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from ..accessor import AlgorithmDescription, AlgorithmList, AlgorithmRun

router = APIRouter(prefix="/processing", tags=["processing"])


@router.get("/algorithms", response_model=AlgorithmList)
def find_algorithms(request: Request, query: str = Query(..., min_length=1, max_length=200),
                    limit: int = Query(20, ge=1, le=50)) -> AlgorithmList:
    """The algorithms whose id, name, group or tags hold every word of ``query``."""
    return request.app.state.accessor.find_algorithms(query, limit=limit)


@router.get("/algorithm", response_model=AlgorithmDescription)
def describe_algorithm(request: Request, id: str = Query(..., min_length=1, max_length=200)) -> AlgorithmDescription:  # noqa: A002
    """What an algorithm does, its parameters and its outputs."""
    return request.app.state.accessor.describe_algorithm(id)


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    algorithm_id: str = Field(..., min_length=1, max_length=200)
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Values by parameter name")
    names: Optional[Dict[str, str]] = Field(None, description="Name of the layer made by each output")


@router.post("/run", response_model=AlgorithmRun)
def run_algorithm(payload: RunRequest, request: Request) -> AlgorithmRun:
    """Run an algorithm on layers of the project; the layers it makes are added to the project."""
    return request.app.state.accessor.run_algorithm(payload.algorithm_id, parameters=payload.parameters,
                                                    names=payload.names)
