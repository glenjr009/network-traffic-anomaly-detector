"""
Tests for RAG chatbot integration, endpoints, and domain filtering using standard unittest.
"""

import unittest
from fastapi.testclient import TestClient

from src.realtime_api import app
from src.rag import (
    RAGRetriever,
    default_config,
    is_cybersecurity_domain,
    is_out_of_domain,
    OUT_OF_DOMAIN_REFUSAL,
)


class TestRAGChatbot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_cm = TestClient(app)
        cls.client = cls.client_cm.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_cm.__exit__(None, None, None)

    def test_src_rag_reexports(self):
        """Verify that src.rag re-exports the required RAG components."""
        from src.rag import (
            RAGConfig,
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
        )
        self.assertIsNotNone(RAGConfig)
        self.assertIsNotNone(RAGRetriever)
        self.assertIsNotNone(call_llm)

    def test_domain_filtering(self):
        """Verify in-domain and out-of-domain classification."""
        self.assertTrue(is_cybersecurity_domain("What is SYN flood DDoS?"))
        self.assertTrue(is_cybersecurity_domain("Explain CICIDS2017 dataset features"))
        self.assertTrue(is_cybersecurity_domain("How to mitigate brute force SSH login?"))

        self.assertTrue(is_out_of_domain("How to bake a chocolate cake?"))
        self.assertTrue(is_out_of_domain("Who won the 1998 World Cup?"))

    def test_rag_retriever_grounding(self):
        """Verify that RAGRetriever finds relevant documents from pre-indexed store."""
        retriever = RAGRetriever(default_config)
        res = retriever.retrieve("What is SYN flood DoS attack?")
        self.assertTrue(res["has_evidence"])
        self.assertGreater(len(res["sources"]), 0)
        context = res["context_text"].lower()
        self.assertTrue(any(term in context for term in ["syn", "flood", "dos", "attack", "denial"]))

    def test_api_root_endpoint(self):
        """Verify root endpoint includes RAG availability."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "online")
        self.assertTrue(data["rag_available"])

    def test_api_rag_status_endpoint(self):
        """Verify /api/rag/status returns chunk count and provider configuration."""
        response = self.client.get("/api/rag/status")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "online")
        self.assertGreater(data["chunks_indexed"], 0)
        self.assertIn("llm_provider", data)
        self.assertIn("gemini_model", data)

    def test_api_chat_in_domain(self):
        """Verify /api/chat returns grounded answer for in-domain cybersecurity query."""
        response = self.client.post("/api/chat", json={"query": "What is SYN flood DoS?"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["query"], "What is SYN flood DoS?")
        self.assertTrue(data["has_evidence"])
        self.assertGreater(len(data["sources"]), 0)
        self.assertGreater(len(data["answer"]), 50)
        self.assertIn("latency_ms", data)

    def test_api_chat_out_of_domain(self):
        """Verify /api/chat refuses out-of-domain inquiries politely without calling external LLM."""
        response = self.client.post("/api/chat", json={"query": "Tell me a recipe for chocolate chip cookies."})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["mode"], "out_of_domain_refusal")
        self.assertFalse(data["has_evidence"])
        self.assertEqual(data["answer"], OUT_OF_DOMAIN_REFUSAL)

    def test_api_chat_explain_endpoint(self):
        """Verify /api/chat/explain accepts detection telemetry and returns SOC explanation."""
        telemetry = {
            "prediction": "ANOMALY",
            "attack_type": "ATTACK",
            "severity": "HIGH",
            "confidence": 0.96,
            "dataset": "CICIDS-2017",
            "total_flows": 1500,
            "attack_flows": 120,
        }
        response = self.client.post("/api/chat/explain", json={
            "detection": telemetry,
            "question": "Explain this anomaly detection and provide mitigation."
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreater(len(data["answer"]), 50)
        self.assertTrue(data["has_evidence"])

    def test_cors_rejects_wildcard_with_credentials(self):
        """CORS must use explicit origins; never allow_origins=['*'] with credentials."""
        from src.realtime_api import app as api_app

        cors_middleware = None
        for middleware in api_app.user_middleware:
            if middleware.cls is not None and middleware.cls.__name__ == "CORSMiddleware":
                cors_middleware = middleware
                break
        self.assertIsNotNone(cors_middleware)
        kwargs = cors_middleware.kwargs
        origins = kwargs.get("allow_origins", [])
        self.assertNotIn("*", origins)
        self.assertTrue(kwargs.get("allow_credentials", False))
        self.assertTrue(any("127.0.0.1" in o or "localhost" in o for o in origins))

    def test_ws_detections_endpoint_still_accepts(self):
        """Preserve live detection WebSocket used by the Chrome extension."""
        with self.client.websocket_connect("/ws/detections") as websocket:
            self.assertIsNotNone(websocket)

    def test_offline_fallback_without_llm(self):
        """When LLM providers are unavailable, grounded offline fallback still answers."""
        from unittest.mock import patch
        from src.rag import build_offline_fallback, RAGRetriever, default_config

        retriever = RAGRetriever(default_config)
        retrieval = retriever.retrieve("What is a DDoS attack?")
        self.assertTrue(retrieval["has_evidence"])

        with patch("src.realtime_api.call_llm", return_value=None):
            # Exercise endpoint path through chat with forced offline LLM
            with patch("src.rag.call_llm", return_value=None):
                response = self.client.post(
                    "/api/chat",
                    json={"query": "What is a DDoS attack?"},
                )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn(data["mode"], ("offline_knowledge_base", "llm_auto", "llm_offline_soc"))
        self.assertGreater(len(data["answer"]), 20)
        offline = build_offline_fallback(prediction=None, retrieval_result=retrieval)
        self.assertGreater(len(offline), 20)


if __name__ == "__main__":
    unittest.main()
