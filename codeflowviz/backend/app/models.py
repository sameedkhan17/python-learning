from typing import Any, Dict, List, Optional, TypedDict
from pydantic import BaseModel, Field


class PreprocessRequest(BaseModel):
    code: str = Field(default="")
    use_gemini: bool = Field(default=True)


class PreprocessResponse(BaseModel):
    clean_code: str
    meta: Dict[str, Any] = Field(default_factory=dict)


class AnalyzeRequest(BaseModel):
    code: str = Field(default="")
    use_gemini: bool = Field(default=True)


class GraphElement(TypedDict):
    data: Dict[str, Any]


class AnalyzeResponse(BaseModel):
    clean_code: str
    graph: Dict[str, List[GraphElement]]
    diagnostics: List[str] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)
    stats: Dict[str, Any] = Field(default_factory=dict)