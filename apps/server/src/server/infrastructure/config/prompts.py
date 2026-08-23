from functools import lru_cache
from importlib import resources

import yaml
from pydantic import BaseModel, Field


class SystemOnlyPrompt(BaseModel):
    system: str = Field(min_length=1)


class TemplatedPrompt(BaseModel):
    system: str = Field(min_length=1)
    instructions_template: str = Field(min_length=1)


class PromptsConfig(BaseModel):
    document_classification: TemplatedPrompt
    document_type_configuration: TemplatedPrompt
    ocr_extraction: SystemOnlyPrompt


@lru_cache
def get_prompts() -> PromptsConfig:
    text = resources.files("server.infrastructure.config").joinpath("prompts.yaml").read_text()
    return PromptsConfig.model_validate(yaml.safe_load(text))
