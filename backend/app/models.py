from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class SheetProfile:
    file_name: str
    sheet_name: str
    detected_type: str
    confidence: int
    header_row: Optional[int] = None
    mapped_columns: Dict[str, str] = field(default_factory=dict)
    signals: List[str] = field(default_factory=list)
    row_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ParsedProjectData:
    project_name: Optional[str] = None
    currency: Optional[str] = None
    language_hint: Optional[str] = None
    planned_execution: Optional[float] = None
    actual_execution: Optional[float] = None
    delay_days: Optional[int] = None
    cost_variance_percent: Optional[float] = None
    workforce_current: Optional[int] = None
    workforce_required: Optional[int] = None
    baseline_finish: Optional[str] = None
    estimated_finish: Optional[str] = None
    total_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    planned_cost: Optional[float] = None
    sheets: List[SheetProfile] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["sheets"] = [s.to_dict() for s in self.sheets]
        return data
