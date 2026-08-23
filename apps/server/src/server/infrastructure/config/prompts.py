from functools import lru_cache
from importlib import resources

import yaml
from pydantic import BaseModel


class PromptSpec(BaseModel):
    system: str
    instructions_template: str | None = None


class PromptsConfig(BaseModel):
    document_classification: PromptSpec
    document_type_configuration: PromptSpec
    ocr_extraction: PromptSpec


@lru_cache
def get_prompts() -> PromptsConfig:
    text = resources.files("server.infrastructure.config").joinpath("prompts.yaml").read_text()
    return PromptsConfig.model_validate(yaml.safe_load(text))
