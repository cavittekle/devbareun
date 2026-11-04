"""Input model for construction execution and delay analysis.

Every reader (Excel template, CSV, Primavera XER, MS Project XML) produces a
``DelayInput``. The engine only depends on this model, so new file formats can
be added without touching the calculations.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

RESPONSIBLE_PARTIES = ("employer", "contractor", "neutral")


@dataclass
class ProjectInfo:
    name: str = "Construction project"
    client: Optional[str] = None
    contractor: Optional[str] = None
    location: Optional[str] = None
    contract_start: Optional[date] = None
    contract_finish: Optional[date] = None
    data_date: Optional[date] = None
    currency: Optional[str] = None
    contract_value: Optional[float] = None


@dataclass
class Activity:
    id: str
    name: str
    planned_start: Optional[date] = None
    planned_finish: Optional[date] = None
    wbs: Optional[str] = None
    weight: Optional[float] = None
    predecessors: List[str] = field(default_factory=list)
    actual_start: Optional[date] = None
    actual_finish: Optional[date] = None
    forecast_finish: Optional[date] = None
    progress: Optional[float] = None  # actual percent complete, 0-100
    source: Optional[str] = None


@dataclass
class DelayEvent:
    id: str
    description: str
    start: Optional[date] = None
    finish: Optional[date] = None
    activity_ids: List[str] = field(default_factory=list)
    cause: Optional[str] = None
    responsible: Optional[str] = None  # employer | contractor | neutral
    notes: Optional[str] = None


@dataclass
class MonthlyProgress:
    period: date  # any day inside the month; normalised to month end
    planned: Optional[float] = None
    actual: Optional[float] = None


@dataclass
class PaymentCertificate:
    """One F2 certificate: value of work accepted for one reporting period."""
    source: str
    period: Optional[date] = None  # last day of the reporting period
    number: Optional[str] = None
    amount: Optional[float] = None  # period total before VAT
    amount_with_vat: Optional[float] = None
    cumulative: Optional[float] = None  # value since the start of the works, if stated
    line_count: int = 0


@dataclass
class SupportingDocument:
    """An uploaded file and how the analysis used it."""
    name: str
    document_type: str  # contract | schedule | f2
    file_format: str
    status: str  # read | reference
    note_en: Optional[str] = None
    note_az: Optional[str] = None


@dataclass
class DelayInput:
    project: ProjectInfo = field(default_factory=ProjectInfo)
    activities: List[Activity] = field(default_factory=list)
    events: List[DelayEvent] = field(default_factory=list)
    monthly: List[MonthlyProgress] = field(default_factory=list)
    payments: List[PaymentCertificate] = field(default_factory=list)
    documents: List[SupportingDocument] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)

    def merge(self, other: "DelayInput") -> None:
        """Merge another file's content (multi-file uploads)."""
        mine = self.project
        for attr in vars(other.project):
            value = getattr(other.project, attr)
            if value and (getattr(mine, attr) in (None, "", "Construction project")):
                setattr(mine, attr, value)
        by_id = {a.id: a for a in self.activities}
        for activity in other.activities:
            existing = by_id.get(activity.id)
            if existing is None:
                self.activities.append(activity)
                by_id[activity.id] = activity
                continue
            for attr in vars(activity):
                value = getattr(activity, attr)
                if value not in (None, "", []) and getattr(existing, attr) in (None, "", []):
                    setattr(existing, attr, value)
        self.events.extend(other.events)
        self.monthly.extend(other.monthly)
        self.payments.extend(other.payments)
        self.documents.extend(other.documents)
        self.warnings.extend(other.warnings)
        self.sources.extend(other.sources)
