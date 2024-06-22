import json
import time

import websocket
import threading
import logging
import copy
from uuid import uuid4

from pybit.unified_trading import HTTP, MarketHTTP, WebSocket

from pybit._websocket_stream import (
    logger, SUBDOMAIN_TESTNET, SUBDOMAIN_MAINNET, DOMAIN_MAIN
)


class ProxyHTTP(HTTP):
    def __init__(self, proxy: dict = None, **kwargs):
        super().__init__(**kwargs)
        if proxy:
            self.client.proxies.update(proxy)


class ProxyMarketHTTP(MarketHTTP):
    def __init__(self, proxy: dict = None, **kwargs):
        super().__init__(**kwargs)
        if proxy:
            self.client.proxies.update(proxy)


class ProxyWebsocket(WebSocket):
    def __init__(self,  proxy_type: str = None, http_proxy_host: str = None, http_proxy_port: str = None, http_proxy_auth: tuple = None, **kwargs):
        self.proxy_type = proxy_type
        self.http_proxy_host = http_proxy_host
        self.http_proxy_port = http_proxy_port
        self.http_proxy_auth = http_proxy_auth

        super().__init__(**kwargs)

    def _connect(self, url):
        """
        Open websocket in a thread.
        """

        def resubscribe_to_topics():
            if not self.subscriptions:
                # There are no subscriptions to resubscribe to, probably
                # because this is a brand new WSS initialisation so there was
                # no previous WSS connection.
                return

            for req_id, subscription_message in self.subscriptions.items():
                self.ws.send(subscription_message)

        self.attempting_connection = True

        # Set endpoint.
        subdomain = SUBDOMAIN_TESTNET if self.testnet else SUBDOMAIN_MAINNET
        domain = DOMAIN_MAIN if not self.domain else self.domain
        url = url.format(SUBDOMAIN=subdomain, DOMAIN=domain)
        self.endpoint = url

        # Attempt to connect for X seconds.
        retries = self.retries
        if retries == 0:
            infinitely_reconnect = True
        else:
            infinitely_reconnect = False

        while (
            infinitely_reconnect or retries > 0
        ) and not self.is_connected():
            logger.info(f"WebSocket {self.ws_name} attempting connection...")
            self.ws = websocket.WebSocketApp(
                url=url,
                on_message=lambda ws, msg: self._on_message(msg),
                on_close=lambda ws, *args: self._on_close(),
                on_open=lambda ws, *args: self._on_open(),
                on_error=lambda ws, err: self._on_error(err),
                on_pong=lambda ws, *args: self._on_pong(),
            )

            # Setup the thread running WebSocketApp.
            self.wst = threading.Thread(
                target=lambda: self.ws.run_forever(
                    ping_interval=self.ping_interval,
                    ping_timeout=self.ping_timeout,
                    # NEW
                    proxy_type=self.proxy_type,
                    http_proxy_auth=self.http_proxy_auth,
                    http_proxy_port=self.http_proxy_port,
                    http_proxy_host=self.http_proxy_host,
                )
            )

            # Configure as daemon; start.
            self.wst.daemon = True
            self.wst.start()

            retries -= 1
            while self.wst.is_alive():
                if self.ws.sock and self.is_connected():
                    break

            # If connection was not successful, raise error.
            if not infinitely_reconnect and retries <= 0:
                self.exit()
                raise websocket.WebSocketTimeoutException(
                    f"WebSocket {self.ws_name} ({self.endpoint}) connection "
                    f"failed. Too many connection attempts. pybit will no "
                    f"longer try to reconnect."
                )

        logger.info(f"WebSocket {self.ws_name} connected")

        # If given an api_key, authenticate.
        if self.api_key and self.api_secret:
            self._auth()

        resubscribe_to_topics()

        self.attempting_connection = False

