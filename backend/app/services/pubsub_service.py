from __future__ import annotations

import json
import logging
from typing import Any

from backend.app.config import settings

logger = logging.getLogger(__name__)


class PubSubService:
    def __init__(self):
        self._publisher = None

    def _get_publisher(self):
        if self._publisher is None:
            try:
                from google.cloud import pubsub_v1

                self._publisher = pubsub_v1.PublisherClient()
            except Exception as e:
                logger.warning(f"Pub/Sub unavailable: {e}")
        return self._publisher

    def publish(self, message: dict[str, Any], topic: str | None = None) -> bool:
        publisher = self._get_publisher()
        if not publisher:
            logger.info(f"Pub/Sub unavailable, dropping message: {message}")
            return False
        try:
            topic_path = publisher.topic_path(settings.GOOGLE_PROJECT_ID, topic or settings.PUBSUB_TOPIC)
            data = json.dumps(message).encode("utf-8")
            publisher.publish(topic_path, data=data)
            return True
        except Exception as e:
            logger.error(f"Pub/Sub publish failed: {e}")
            return False

    def publish_document_event(self, document_id: str, event_type: str, metadata: dict | None = None) -> bool:
        return self.publish(
            {
                "document_id": document_id,
                "event_type": event_type,
                "metadata": metadata or {},
            }
        )


pubsub_service = PubSubService()
