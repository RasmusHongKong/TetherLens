from __future__ import annotations

import html as html_lib
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from tetherlens_ingest.models import (
    AcquisitionObservation,
    CandidateClaim,
    ClaimSubjectType,
    ProductIdentity,
    ProductType,
    ReadinessIssue,
    SourceArtifact,
    SourceRequest,
)
from tetherlens_ingest.normalize import opening_action_count, parse_mass
from .base import ManufacturerAdapter
from