"""Kind-agnostic reconciliation: rules, matching, the engine, the report.

Nothing here may import a concrete reconciliation kind, and nothing here may
import another bounded context. Those two rules are enforced in CI
(`.importlinter`) rather than left to discipline.
"""

from server.reconciliation.core.concepts import Concept, ConceptCatalog
from server.reconciliation.core.contribution import (
    ContributionStatus,
    DocumentContribution,
    GatheredFacts,
)
from server.reconciliation.core.engine import ReconciliationEngine
from server.reconciliation.core.findings import (
    FindingStatus,
    ReconciliationFinding,
    ReconciliationReport,
    ReportSummary,
)
from server.reconciliation.core.kind import (
    FactExtractor,
    FactSourceSpec,
    ReconciliationKind,
    SourceContent,
)
from server.reconciliation.core.projection import (
    ConceptMapping,
    ConceptMappingEntry,
    project_facts,
)
from server.reconciliation.core.registry import KindRegistry, UnknownReconciliationKind
from server.reconciliation.core.rules import (
    DEFAULT_TOLERANCE,
    ReconciliationRule,
    RuleScope,
    Term,
    Tolerance,
    minus,
    spine_concepts_answered_by,
    terms,
)

__all__ = [
    "GatheredFacts",
    "DocumentContribution",
    "ContributionStatus",
    "DEFAULT_TOLERANCE",
    "Concept",
    "ConceptCatalog",
    "ConceptMapping",
    "ConceptMappingEntry",
    "FactExtractor",
    "FactSourceSpec",
    "FindingStatus",
    "KindRegistry",
    "ReconciliationEngine",
    "ReconciliationFinding",
    "ReconciliationKind",
    "ReconciliationReport",
    "ReconciliationRule",
    "ReportSummary",
    "RuleScope",
    "SourceContent",
    "Term",
    "Tolerance",
    "UnknownReconciliationKind",
    "minus",
    "project_facts",
    "spine_concepts_answered_by",
    "terms",
]
