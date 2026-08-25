import pytest
from pydantic import ValidationError

from server.infrastructure.config.prompts import PromptsConfig, get_prompts

_VALID_DATA = {
    "document_classification": {"system": "classify", "instructions_template": "{options}"},
    "document_type_configuration": {"system": "configure", "instructions_template": "{type_name}"},
    "ocr_extraction": {"system": "extract"},
}


def test_get_prompts_loads_the_real_config() -> None:
    prompts = get_prompts()

    assert prompts.document_classification.system
    assert prompts.document_classification.instructions_template
    assert prompts.document_type_configuration.instructions_template
    assert prompts.ocr_extraction.system


def test_templated_prompt_requires_a_non_empty_instructions_template() -> None:
    data = {**_VALID_DATA, "document_classification": {"system": "classify"}}

    with pytest.raises(ValidationError, match="instructions_template"):
        PromptsConfig.model_validate(data)


def test_prompt_rejects_an_empty_system() -> None:
    data = {**_VALID_DATA, "ocr_extraction": {"system": ""}}

    with pytest.raises(ValidationError, match="system"):
        PromptsConfig.model_validate(data)


def test_the_extraction_prompt_asks_for_everything_the_document_states() -> None:
    """The completeness rule lived only in the configurator's prompt — at
    design time. At extraction time the engine was told to follow the type's
    instructions and return the requested fields, and nothing said that
    omitting a value is itself a claim about the document."""
    system = get_prompts().ocr_extraction.system

    assert "Account for everything the document states" in system
    # The failure this was written for: a table entry left out because two of
    # its columns did not apply to it, though a third carried a real figure.
    assert "never a reason to leave the entry out" in system
