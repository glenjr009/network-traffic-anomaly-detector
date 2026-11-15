"""
NetGuard AI - RAG Integration Module for src package.
Exposes all core components from Backend.rag for seamless in-package imports.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from Backend.rag import (
    RAGConfig,
    default_config,
    DocumentChunk,
    DocumentChunker,
    EmbeddingEngine,
    PersistentVectorStore,
    RAGIngestionPipeline,
    RAGRetriever,
    build_general_prompt,
    build_prediction_prompt,
    build_offline_fallback,
    call_llm,
    is_cybersecurity_domain,
    is_out_of_domain,
    OUT_OF_DOMAIN_REFUSAL,
)

__all__ = [
    "RAGConfig",
    "default_config",
    "DocumentChunk",
    "DocumentChunker",
    "EmbeddingEngine",
    "PersistentVectorStore",
    "RAGIngestionPipeline",
    "RAGRetriever",
    "build_general_prompt",
    "build_prediction_prompt",
    "build_offline_fallback",
    "call_llm",
    "is_cybersecurity_domain",
    "is_out_of_domain",
    "OUT_OF_DOMAIN_REFUSAL",
]
