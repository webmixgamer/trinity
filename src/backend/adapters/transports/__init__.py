"""
Channel transport implementations.

Transports handle HOW events arrive (Socket Mode, webhook, polling).
The adapter handles WHAT to do with them (parse, route, respond).
"""

from adapters.transports.base import ChannelTransport

__all__ = ["ChannelTransport"]
