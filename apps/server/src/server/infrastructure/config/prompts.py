from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel

_DEFAULT_PROMPTS_PATH = Path(__file__).resolve().parents[4] / "config" / "prompts.yaml"


class PromptSpec(BaseModel):
    system: str
    instructions_template: str | None = None


class PromptsConfig(BaseModel):
    document_classification: PromptSpec
    document_type_configuration: PromptSpec
    ocr_extraction: PromptSpec


@lru_cache
def get_prompts(path: Path = _DEFAULT_PROMPTS_PATH) -> PromptsConfig:
    data = yaml.safe_load(path.read_text())
    return PromptsConfig.model_validate(data)
