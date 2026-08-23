"""Reconciliation: comparing what a document claims against what other
documents evidence.

The product's model, and the reason for the module boundary this package sits
behind. `core` holds the model-agnostic engine, `kinds` holds one package per
reconciliation model (today only the DIAN exogena), `application` holds the use
cases, and `infrastructure` holds the adapters — including the only module that
is allowed to know both this context and intake.
"""
