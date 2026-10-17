"""Opt-in live packet capture and CICIDS model inference.

This module connects three layers of the pipeline::

    packets -> PacketRecord -> NetworkFlow.extract_features()
            -> predict_flow() -> detection event -> WebSocket

It is written against the interfaces provided by
:mod:`src.flow_extractor` and :mod:`src.prediction`:

* ``FlowExtractor.add_packet(PacketRecord)`` groups packets into flows.
* ``NetworkFlow.extract_features()`` returns the canonical 78 CICIDS features.
* ``predict_flow(flow)`` is the end-to-end inference entry point
  (``predict_cicids(flow.extract_features())``).

Payload handling delegates to :func:`src.pcap_reader.packet_to_record` so that
live capture and saved-PCAP capture populate ``PacketRecord`` identically,
including the application-layer ``payload_length`` required by the
payload-driven features (``act_data_pkt_fwd``, ``min_seg_size_forward`` and the
directional bulk features).
"""

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
from src.pcap_reader import packet_to_record as _pcap_packet_to_record
from src.prediction import predict_flow

logger = logging.getLogger(__name__)


def packet_to_record(packet) -> Optional[PacketRecord]:
    """Convert an IPv4 TCP/UDP packet into the project's :class:`PacketRecord`.

    Delegates to the saved-PCAP adapter in :mod:`src.pcap_reader`. That adapter
    is the single source of truth for how captured packets map to
    ``PacketRecord`` fields, so live and offline captures stay consistent:

    * ``length`` is the full captured frame length.
    * ``payload_length`` is the application-layer (TCP/UDP payload) byte count,
      and is ``0`` for header-only packets such as pure ACK/SYN segments.

    Returns ``None`` for non-IPv4 and non-TCP/UDP packets.
    """

    return _pcap_packet_to_record(packet, IP, TCP, UDP)


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
            # Canonical end-to-end inference:
            # flow -> extract_features() -> model -> BENIGN/ATTACK.
            result = predict_flow(flow)

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
