from server.domain.entities import ExtractedData
from server.domain.ports import ExtractedDataRepository


class GetExtractedData:
    def __init__(self, extracted_data: ExtractedDataRepository) -> None:
        self._extracted_data = extracted_data

    def execute(self, document_id: str) -> ExtractedData | None:
        return self._extracted_data.get_by_document(document_id)
