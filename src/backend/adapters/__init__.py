"""
Channel adapter abstraction for external messaging integrations.

Provides a pluggable interface for Slack, Telegram, and future channels.
See docs/plans/channel-adapter-and-slack-improvements.md for architecture.
"""

from adapters.base import (
    ChannelAdapter,
    ChannelResponse,
    NormalizedMessage,
)
from adapters.transports.base import ChannelTransport

__all__ = [
    "ChannelAdapter",
    "ChannelTransport",
    "ChannelResponse",
    "NormalizedMessage",
]
