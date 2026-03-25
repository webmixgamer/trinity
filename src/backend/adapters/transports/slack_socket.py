"""
Slack Socket Mode transport — outbound WebSocket connection.

No public URL needed. Trinity connects out to Slack.
Default transport for local development.

Requires:
- slack_sdk[socket-mode] package
- App-Level Token (xapp-...) with connections:write scope
- Socket Mode enabled in Slack App settings
"""

import logging
import asyncio
from adapters.transports.base import ChannelTransport

logger = logging.getLogger(__name__)


class SlackSocketTransport(ChannelTransport):
    """Slack Socket Mode — outbound WebSocket, no public URL needed."""

    def __init__(self, app_token: str, adapter, router):
        super().__init__(adapter, router)
        self.app_token = app_token
        self.client = None
        self._running = False

    async def start(self) -> None:
        """Connect to Slack via WebSocket."""
        try:
            from slack_sdk.socket_mode.aiohttp import SocketModeClient
            self.client = SocketModeClient(
                app_token=self.app_token,
                auto_reconnect_enabled=True,
            )
            self.client.socket_mode_request_listeners.append(self._handle_request)
            await self.client.connect()
            self._running = True
            logger.info("Slack Socket Mode transport connected")
        except ImportError:
            logger.error("slack_sdk[socket-mode] not installed. Run: pip install slack_sdk[socket-mode]")
            raise
        except Exception as e:
            logger.error(f"Failed to start Slack Socket Mode: {e}")
            raise

    async def stop(self) -> None:
        """Disconnect from Slack."""
        self._running = False
        if self.client:
            try:
                await self.client.disconnect()
                logger.info("Slack Socket Mode transport disconnected")
            except Exception as e:
                logger.warning(f"Error disconnecting Socket Mode: {e}")
            self.client = None

    async def _handle_request(self, client, req) -> None:
        """Handle incoming Socket Mode request."""
        from slack_sdk.socket_mode.response import SocketModeResponse

        logger.info(f"Socket Mode received: type={req.type}, payload_type={req.payload.get('event', {}).get('type') if isinstance(req.payload, dict) else 'n/a'}")

        # Acknowledge immediately — no timeout concerns
        response = SocketModeResponse(envelope_id=req.envelope_id)
        await client.send_socket_mode_response(response)

        if req.type == "events_api":
            # Process in a task but log errors
            async def _process():
                try:
                    await self.on_event(req.payload)
                except Exception as e:
                    logger.error(f"Error processing event: {e}", exc_info=True)
            asyncio.create_task(_process())
        elif req.type == "interactive":
            # Future: handle Block Kit button clicks (agent selection, etc.)
            logger.info(f"Received interactive event: {req.payload.get('type')}")
        else:
            logger.info(f"Unhandled Socket Mode request type: {req.type}")
