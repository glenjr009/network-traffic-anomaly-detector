"""Tests for the live-capture <-> flow-extraction <-> inference integration.

These tests exercise the interfaces that PR #5's live pipeline depends on:

* ``src.live_capture.packet_to_record`` populating ``PacketRecord.payload_length``
  for TCP, UDP and header-only packets (and rejecting non-IPv4/non-TCP/UDP).
* ``src.flow_extractor.NetworkFlow.extract_features`` consuming live packets.
* ``src.prediction.predict_flow`` producing real model predictions.
* ``LiveCapture`` publishing downstream events in the schema the Chrome
  extension expects, using the real trained model where available.
* The ``realtime_api`` WebSocket broadcasting genuine detection events.

Scapy is required for the packet-level tests; they are skipped without it.
"""

import asyncio
import contextlib
import io
import unittest
from unittest import mock

from src.flow_extractor import FlowExtractor
from src.prediction import predict_flow

try:
    with contextlib.redirect_stderr(io.StringIO()):
        from scapy.all import Ether, ICMP, IP, IPv6, Raw, TCP, UDP

    from src.live_capture import LiveCapture, packet_to_record

    HAVE_SCAPY = True
except Exception:  # pragma: no cover - only without scapy
    HAVE_SCAPY = False


def _tcp_packet(
    *,
    src="10.0.0.1",
    dst="10.0.0.2",
    sport=51000,
    dport=443,
    payload=b"",
    ts=1000.0,
    flags="PA",
    window=1024,
):
    pkt = (
        Ether()
        / IP(src=src, dst=dst)
        / TCP(sport=sport, dport=dport, flags=flags, window=window)
    )
    if payload:
        pkt = pkt / Raw(load=payload)
    pkt.time = ts
    return pkt


def _udp_packet(*, src="10.0.0.9", dst="10.0.0.10", sport=53000, dport=53,
                payload=b"", ts=1.0):
    pkt = Ether() / IP(src=src, dst=dst) / UDP(sport=sport, dport=dport)
    if payload:
        pkt = pkt / Raw(load=payload)
    pkt.time = ts
    return pkt


@unittest.skipUnless(HAVE_SCAPY, "scapy is required for live-capture tests")
class TestPayloadLengthExtraction(unittest.TestCase):
    """payload_length must track the application payload, not the packet size."""

    def test_tcp_payload_length_is_application_payload(self):
        payload = b"x" * 512
        pkt = _tcp_packet(payload=payload)
        record = packet_to_record(pkt)

        self.assertIsNotNone(record)
        self.assertEqual(record.payload_length, 512)
        # Total length includes Ethernet + IP + TCP headers, so it must be
        # strictly larger than (and never confused with) the payload length.
        self.assertEqual(record.length, len(pkt))
        self.assertGreater(record.length, record.payload_length)

    def test_udp_payload_length_is_application_payload(self):
        payload = b"y" * 33
        pkt = _udp_packet(payload=payload)
        record = packet_to_record(pkt)

        self.assertIsNotNone(record)
        self.assertEqual(record.protocol, 17)
        self.assertEqual(record.payload_length, 33)
        self.assertEqual(record.tcp_header_length, 8)
        self.assertEqual(record.tcp_window_size, 0)

    def test_header_only_tcp_has_zero_payload(self):
        pkt = _tcp_packet(payload=b"", flags="S")
        record = packet_to_record(pkt)

        self.assertEqual(record.payload_length, 0)
        self.assertEqual(record.syn, True)
        self.assertEqual(record.length, len(pkt))

    def test_ack_only_packet_has_zero_payload(self):
        pkt = _tcp_packet(payload=b"", flags="A")
        record = packet_to_record(pkt)

        self.assertEqual(record.payload_length, 0)
        self.assertTrue(record.ack)

    def test_non_ipv4_packet_returns_none(self):
        icmp = Ether() / IP(src="1.1.1.1", dst="2.2.2.2") / ICMP()
        icmp.time = 1.0
        self.assertIsNone(packet_to_record(icmp))

    def test_ipv6_packet_returns_none(self):
        pkt = Ether() / IPv6() / TCP(sport=1, dport=2)
        pkt.time = 1.0
        self.assertIsNone(packet_to_record(pkt))

    def test_arp_like_non_ip_returns_none(self):
        self.assertIsNone(packet_to_record(Ether()))


@unittest.skipUnless(HAVE_SCAPY, "scapy is required for live-capture tests")
class TestPayloadDrivenFeaturesFromLivePackets(unittest.TestCase):
    """Payload-length propagation into the payload-dependent CICIDS features."""

    def _forward_payload_flow(self, payload_sizes, start=1000.0, spacing=0.01):
        extractor = FlowExtractor()
        for index, size in enumerate(payload_sizes):
            extractor.add_packet(packet_to_record(
                _tcp_packet(sport=51000, dport=80, payload=b"z" * size,
                            ts=start + index * spacing, flags="PA")
            ))
        return extractor.get_flows()[0]

    def test_act_data_pkt_fwd_counts_only_payload_packets(self):
        extractor = FlowExtractor()
        extractor.add_packet(packet_to_record(
            _tcp_packet(sport=51000, dport=80, payload=b"a" * 100, ts=1000.0,
                        flags="PA")
        ))
        extractor.add_packet(packet_to_record(
            _tcp_packet(sport=51000, dport=80, payload=b"b" * 300, ts=1000.01,
                        flags="PA")
        ))
        # Header-only ACK must NOT be counted as an application-data packet.
        extractor.add_packet(packet_to_record(
            _tcp_packet(sport=51000, dport=80, payload=b"", ts=1000.02, flags="A")
        ))
        extractor.add_packet(packet_to_record(
            _tcp_packet(src="10.0.0.2", dst="10.0.0.1", sport=80, dport=51000,
                        payload=b"c" * 50, ts=1000.03, flags="PA")
        ))
        flow = extractor.get_flows()[0]
        self.assertEqual(flow.act_data_pkt_fwd, 2)

    def test_min_seg_size_forward_uses_payload(self):
        flow = self._forward_payload_flow([100, 300, 120])
        self.assertEqual(flow.min_seg_size_forward, 100)

    def test_bulk_features_are_populated(self):
        # A bulk requires BULK_BOUND (4) payload packets in the same direction.
        flow = self._forward_payload_flow([100] * 5)
        features = flow.extract_features()
        # The forward direction carries a payload bulk; it must not be silently
        # zeroed out as it would be if payload_length were left at its default.
        self.assertGreater(features["Fwd Avg Bytes/Bulk"], 0)
        self.assertGreater(features["Fwd Avg Packets/Bulk"], 0)

    def test_header_only_flow_has_zero_payload_features(self):
        extractor = FlowExtractor()
        for i in range(4):
            extractor.add_packet(packet_to_record(
                _tcp_packet(payload=b"", ts=1000.0 + i, flags="A")
            ))
        flow = extractor.get_flows()[0]
        self.assertEqual(flow.act_data_pkt_fwd, 0)
        self.assertEqual(flow.min_seg_size_forward, 0)
        self.assertEqual(flow.extract_features()["Fwd Avg Bytes/Bulk"], 0)


@unittest.skipUnless(HAVE_SCAPY, "scapy is required for live-capture tests")
class TestInferenceCompatibility(unittest.TestCase):
    """Live flows must reach the model through extract_features/predict_flow."""

    def _flow(self):
        extractor = FlowExtractor()
        extractor.add_packet(packet_to_record(
            _tcp_packet(payload=b"hello", ts=1000.0, flags="PA")
        ))
        extractor.add_packet(packet_to_record(
            _tcp_packet(src="10.0.0.2", dst="10.0.0.1", sport=443, dport=51000,
                        payload=b"world", ts=1000.05, flags="PA")
        ))
        return extractor.get_flows()[0]

    def test_predict_flow_accepts_extracted_live_flow(self):
        result = predict_flow(self._flow())
        self.assertIn(result["prediction"], {"BENIGN", "ATTACK"})
        self.assertIsInstance(result["confidence"], float)
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)
        self.assertEqual(result["model"], "cicids_random_forest")

    def test_live_capture_uses_predict_flow_not_cicids_on_dict(self):
        capture = LiveCapture(interface_index=0, publish=lambda event: None)
        flow = self._flow()

        with mock.patch(
            "src.live_capture.predict_flow",
            return_value={
                "prediction": "BENIGN",
                "confidence": 0.9,
                "model": "cicids_random_forest",
            },
        ) as patched:
            capture._predict_flow(flow)

        # The canonical end-to-end entry point takes the flow object itself.
        patched.assert_called_once_with(flow)

    def test_attack_result_maps_to_extension_event(self):
        capture = LiveCapture(interface_index=0, publish=lambda event: None)
        events = []
        capture.publish = events.append

        with mock.patch(
            "src.live_capture.predict_flow",
            return_value={
                "prediction": "ATTACK",
                "confidence": 0.97,
                "model": "cicids_random_forest",
            },
        ):
            capture._predict_flow(self._flow())

        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event["prediction"], "ANOMALY")
        self.assertEqual(event["attack_type"], "ATTACK")
        self.assertEqual(event["severity"], "HIGH")
        self.assertEqual(event["confidence"], 0.97)
        self.assertEqual(event["model"], "cicids_random_forest")
        self.assertIn("timestamp", event)

    def test_real_model_prediction_reaches_event(self):
        events = []
        capture = LiveCapture(interface_index=0, publish=events.append)

        capture._predict_flow(self._flow())

        self.assertEqual(len(events), 1)
        event = events[0]
        # Values must come from the real trained model, not a simulation.
        self.assertEqual(event["model"], "cicids_random_forest")
        self.assertIn(event["prediction"], {"NORMAL", "ANOMALY"})
        self.assertIsInstance(event["confidence"], float)


@unittest.skipUnless(HAVE_SCAPY, "scapy is required for live-capture tests")
class TestLiveCaptureIntegration(unittest.TestCase):
    """Packet ingestion, flow expiry, lifecycle, and event publication."""

    def test_on_packet_builds_flow_and_flush_publishes(self):
        events = []
        capture = LiveCapture(interface_index=0, publish=events.append)

        capture._on_packet(_tcp_packet(payload=b"data", ts=1000.0))
        capture._on_packet(_tcp_packet(payload=b"more", ts=1000.1))
        self.assertEqual(len(capture.extractor.get_flows()), 1)

        capture._flush_flows()
        self.assertEqual(len(capture.extractor.get_flows()), 0)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["model"], "cicids_random_forest")

    def test_expire_flows_respects_idle_timeout(self):
        events = []
        capture = LiveCapture(interface_index=0, publish=events.append,
                              idle_timeout=5.0)
        capture._on_packet(_tcp_packet(payload=b"data", ts=1000.0))

        capture._expire_flows(1002.0)  # 2s idle -> still active
        self.assertEqual(len(capture.extractor.get_flows()), 1)
        self.assertEqual(events, [])

        capture._expire_flows(1006.0)  # 6s idle -> expired and published
        self.assertEqual(len(capture.extractor.get_flows()), 0)
        self.assertEqual(len(events), 1)

    def test_ignores_unsupported_packets(self):
        capture = LiveCapture(interface_index=0, publish=lambda event: None)
        icmp = Ether() / IP(src="1.1.1.1", dst="2.2.2.2") / ICMP()
        icmp.time = 1.0
        capture._on_packet(icmp)
        self.assertEqual(capture.extractor.get_flows(), [])

    def test_start_and_stop_lifecycle(self):
        capture = LiveCapture(interface_index=0, publish=lambda event: None)

        with mock.patch(
            "src.live_capture.conf.ifaces.dev_from_index",
            return_value="fake-iface",
        ), mock.patch("src.live_capture.sniff", return_value=None):
            capture.start()
            self.assertIsNotNone(capture.thread)
            self.assertTrue(capture.thread.is_alive())
            capture.stop()
            self.assertFalse(capture.thread.is_alive())

    def test_start_rejects_unknown_interface(self):
        capture = LiveCapture(interface_index=-1, publish=lambda event: None)
        with mock.patch(
            "src.live_capture.conf.ifaces.dev_from_index", return_value=None
        ):
            with self.assertRaises(ValueError):
                capture.start()


class TestDetectionHubBroadcast(unittest.TestCase):
    """The realtime_api hub must forward genuine events to subscribers."""

    def test_detection_hub_broadcasts_to_subscriber(self):
        from src.realtime_api import DetectionHub

        async def scenario():
            loop = asyncio.get_running_loop()
            hub = DetectionHub(loop)
            queue = hub.subscribe()
            event = {"prediction": "ANOMALY", "confidence": 0.99}
            hub._broadcast(event)
            return await asyncio.wait_for(queue.get(), timeout=1.0)

        received = asyncio.run(scenario())
        self.assertEqual(received["prediction"], "ANOMALY")
        self.assertEqual(received["confidence"], 0.99)

    def test_detection_hub_unsubscribe(self):
        from src.realtime_api import DetectionHub

        async def scenario():
            loop = asyncio.get_running_loop()
            hub = DetectionHub(loop)
            queue = hub.subscribe()
            hub.unsubscribe(queue)
            return hub.subscribers

        self.assertEqual(asyncio.run(scenario()), set())

    def test_websocket_endpoint_delivers_real_event(self):
        try:
            from fastapi.testclient import TestClient
        except Exception:  # pragma: no cover - optional dependency
            self.skipTest("fastapi TestClient dependencies are unavailable")

        from src.realtime_api import app

        with TestClient(app) as client:
            with client.websocket_connect("/ws/detections") as websocket:
                event = {
                    "prediction": "ANOMALY",
                    "attack_type": "ATTACK",
                    "confidence": 0.97,
                    "severity": "HIGH",
                    "timestamp": "2026-01-01T00:00:00+00:00",
                    "model": "cicids_random_forest",
                }
                app.state.detection_hub.publish_from_thread(event)
                received = websocket.receive_json()

        self.assertEqual(received["prediction"], "ANOMALY")
        self.assertEqual(received["model"], "cicids_random_forest")
        self.assertEqual(received["confidence"], 0.97)

    def test_root_reports_capture_disabled_by_default(self):
        try:
            from fastapi.testclient import TestClient
        except Exception:  # pragma: no cover - optional dependency
            self.skipTest("fastapi TestClient dependencies are unavailable")

        from src.realtime_api import app

        with TestClient(app) as client:
            response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["capture_enabled"])


if __name__ == "__main__":
    unittest.main()
