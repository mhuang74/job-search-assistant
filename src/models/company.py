"""Company profile models"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class CompanyProfile:
    """Company information from LinkedIn APIs"""
    id: str
    name: str
    linkedin_url: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    headquarters_location: Optional[str] = None
    description: Optional[str] = None

    # Employee data
    total_employees: Optional[int] = None
    taiwan_employee_count: int = 0  # Asia employee count (Taiwan, China, Singapore, Hong Kong)
    taiwan_employees: List[dict] = field(default_factory=list)  # Asia employees

    # Metadata
    enriched_at: Optional[datetime] = None
    source: Optional[str] = None  # peopledatalabs, coresignal, etc.
