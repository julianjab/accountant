from __future__ import annotations

from server.reconciliation.core.concepts import ConceptCatalog
from server.reconciliation.core.kind import FactSourceSpec
from server.reconciliation.core.rules import ReconciliationRule
from server.reconciliation.kinds.exogena.concepts import build_catalog
from server.reconciliation.kinds.exogena.rules import build_rules
from server.reconciliation.kinds.exogena.xlsx_parser import (
    XLSX_MEDIA_TYPES,
    ExogenaXlsxExtractor,
)
from server.shared import FactRole, PeriodGranularity

KIND_ID = "exogena_dian"


class ExogenaReconciliation:
    """Checks a taxpayer's DIAN exogena report against the certificates the
    reporting parties issued them.

    Implements `reconciliation.core.kind.ReconciliationKind`. Nothing outside
    the registry that composes the application should import this class by
    name — that is what keeps a second reconciliation model a matter of adding
    a module rather than editing the engine.
    """

    def __init__(self) -> None:
        self._catalog = build_catalog()
        # The rules read their labels off the catalog, so the catalog is built
        # first and handed over rather than rebuilt behind the rule pack.
        self._rules = build_rules(self._catalog)
        self._sources = (
            FactSourceSpec(
                id="exogena_report",
                label="Reporte de información exógena (DIAN)",
                role=FactRole.SPINE,
                media_types=XLSX_MEDIA_TYPES,
                extractor=ExogenaXlsxExtractor(),
                required=True,
            ),
            FactSourceSpec(
                id="tax_certificate",
                label="Certificado tributario de la entidad reportante",
                role=FactRole.EVIDENCE,
                media_types=frozenset({"application/pdf", "image/jpeg", "image/png"}),
                # No extractor: certificates vary by issuer, so they go through
                # OCR and the document type's concept mapping instead.
                extractor=None,
            ),
        )

    @property
    def id(self) -> str:
        return KIND_ID

    @property
    def label(self) -> str:
        return "Conciliación de exógena (DIAN)"

    @property
    def period_granularity(self) -> PeriodGranularity:
        # The exogena is filed once per tax year; there is no monthly view.
        return PeriodGranularity.YEAR

    def concept_catalog(self) -> ConceptCatalog:
        return self._catalog

    def rules(self) -> tuple[ReconciliationRule, ...]:
        return self._rules

    def sources(self) -> tuple[FactSourceSpec, ...]:
        return self._sources
