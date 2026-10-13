
"""Opt-in live packet capture and CICIDS model inference."""

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Callable, Optional

from scapy.all import (
    IP,
    TCP,
    UDP,
    conf,
    sniff,
)

from src.flow_extractor import FlowExtractor, PacketRecord
from src.prediction import predict_cicids

logger = logging.getLogger(__name__)


def packet_to_record(packet) -> Optional[PacketRecord]:
    """Convert an IPv4 TCP/UDP packet into the project's PacketRecord."""
    if IP not in packet:
        return None

    ip = packet[IP]
    tcp = packet[TCP] if TCP in packet else None
    udp = packet[UDP] if UDP in packet else None

    if tcp is None and udp is None:
        return None

    flags = int(tcp.flags) if tcp is not None else 0

    return PacketRecord(
        timestamp=float(packet.time),
        src_ip=str(ip.src),
        dst_ip=str(ip.dst),
        src_port=int(tcp.sport if tcp is not None else udp.sport),
        dst_port=int(tcp.dport if tcp is not None else udp.dport),
        protocol=int(ip.proto),
        # Use IP-layer length, rather than Ethernet-frame length.
        length=int(len(ip)),
        ip_header_length=int(ip.ihl * 4),
        tcp_header_length=int(tcp.dataofs * 4) if tcp is not None else 0,
        fin=bool(flags & 0x01),
        syn=bool(flags & 0x02),
        rst=bool(flags & 0x04),
        psh=bool(flags & 0x08),
        ack=bool(flags & 0x10),
        urg=bool(flags & 0x20),
        ece=bool(flags & 0x40),
        cwe=bool(flags & 0x80),
        tcp_window_size=int(tcp.window) if tcp is not None else 0,
    )


def flow_to_features(flow) -> dict:
    """Assemble the 78 CICIDS features using the existing extractor."""
    parts = (
        flow.basic_cicids_features(),
        flow.rate_iat_cicids_features(),
        flow.forward_backward_iat_features(),
        flow.tcp_flag_and_rate_features(),
        flow.packet_length_and_tcp_flag_features(),
        flow.chunk8_features(),
        flow.chunk9_features(),
        flow.chunk10_features(),
        flow.chunk11_features(),
    )

    features = {}
    for part in parts:
        overlap = features.keys() & part.keys()
        if overlap:
            raise ValueError(f"Duplicate CICIDS features: {sorted(overlap)}")
        features.update(part)

    if len(features) != 78:
        raise ValueError(f"Expected 78 features, got {len(features)}")

    return features


class LiveCapture:
    """Capture packets, expire idle flows, and publish model detections."""

    def __init__(
        self,
        interface_index: int,
        publish: Callable[[dict], None],
        idle_timeout: float = 5.0,
    ):
        self.interface_index = interface_index
        self.publish = publish
        self.idle_timeout = idle_timeout
        self.extractor = FlowExtractor()
        self.stop_event = threading.Event()
        self.thread = None
        self.interface = None

    def start(self):
        if self.thread and self.thread.is_alive():
            return

        self.interface = conf.ifaces.dev_from_index(self.interface_index)
        if self.interface is None:
            raise ValueError(
                f"Scapy interface index {self.interface_index} was not found"
            )

        self.stop_event.clear()
        self.thread = threading.Thread(
            target=self._run,
            name="network-anomaly-capture",
            daemon=True,
        )
        self.thread.start()
        logger.info("Capture started on interface index %s", self.interface_index)

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=3)

    def _run(self):
        try:
            while not self.stop_event.is_set():
                sniff(
                    iface=self.interface,
                    timeout=1,
                    store=False,
                    prn=self._on_packet,
                )
                self._expire_flows(time.time())
        except Exception:
            logger.exception("Live packet capture stopped unexpectedly")
        finally:
            self._flush_flows()

    def _on_packet(self, packet):
        try:
            record = packet_to_record(packet)
            if record is None:
                return

            # Expire stale flows before adding this packet. This prevents a
            # returning connection from being merged into an old flow.
            self._expire_flows(record.timestamp)
            self.extractor.add_packet(record)
        except Exception:
            logger.exception("Could not process a captured packet")

    def _expire_flows(self, now: float):
        for key, flow in list(self.extractor.flows.items()):
            if now - flow.end_time >= self.idle_timeout:
                self.extractor.flows.pop(key, None)
                self._predict_flow(flow)

    def _flush_flows(self):
        for key, flow in list(self.extractor.flows.items()):
            self.extractor.flows.pop(key, None)
            self._predict_flow(flow)

    def _predict_flow(self, flow):
        if not flow.packets:
            return

        try:
            features = flow_to_features(flow)
            result = predict_cicids(features)

            is_attack = result["prediction"] == "ATTACK"

            event = {
                "prediction": "ANOMALY" if is_attack else "NORMAL",
                # The model is binary; it does not identify attack families.
                "attack_type": "ATTACK" if is_attack else "NONE",
                "confidence": float(result["confidence"]),
                "severity": "HIGH" if is_attack else "LOW",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "model": result["model"],
            }

            self.publish(event)
            logger.info(
                "Flow classified: %s (confidence %.4f)",
                result["prediction"],
                result["confidence"],
            )
        except Exception:
            logger.exception("Could not generate a prediction for a flow")
