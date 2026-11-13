"""In-memory sliding window rate limiter with secure trusted-proxy IP extraction."""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
import ipaddress
import math
import time
from typing import Callable, Deque, Dict, List, Optional
from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.logging import logger


class ClientIpResolver:
    """Extracts client IP securely, respecting configured trusted upstream proxies."""

    def __init__(self, trusted_proxies_csv: str) -> None:
        self.trusted_networks: List[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
        for item in trusted_proxies_csv.split(","):
            raw = item.strip()
            if not raw:
                continue
            try:
                # Support single IP or CIDR network
                if "/" in raw:
                    self.trusted_networks.append(ipaddress.ip_network(raw, strict=False))
                else:
                    addr = ipaddress.ip_address(raw)
                    self.trusted_networks.append(ipaddress.ip_network(f"{addr}/{32 if addr.version == 4 else 128}"))
            except ValueError:
                logger.warning("Invalid trusted proxy IP/network ignored: %s", raw)

    def is_trusted(self, ip_str: str) -> bool:
        """Check if an IP address falls within the trusted upstream proxy set."""
        try:
            ip = ipaddress.ip_address(ip_str)
            return any(ip in net for net in self.trusted_networks)
        except ValueError:
            return False

    def resolve_client_ip(self, request: Request) -> str:
        """
        Resolve the real client IP.
        Only trusts X-Forwarded-For or CF-Connecting-IP if the immediate peer is in trusted proxies.
        """
        peer_ip = request.client.host if request.client else "127.0.0.1"

        if not self.is_trusted(peer_ip):
            # Immediate peer is not a trusted proxy: ignore all forwarded headers
            return peer_ip

        # If behind Cloudflare and peer is trusted
        cf_ip = request.headers.get("CF-Connecting-IP")
        if cf_ip and cf_ip.strip():
            return cf_ip.strip()

        # Parse X-Forwarded-For: client, proxy1, proxy2
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        if x_forwarded_for:
            ips = [ip.strip() for ip in x_forwarded_for.split(",") if ip.strip()]
            if ips:
                # Return leftmost client IP
                return ips[0]

        return peer_ip


class SlidingWindowRateLimiter:
    """Lightweight in-memory sliding window rate limiter."""

    def __init__(self) -> None:
        # key -> deque of timestamps
        self._windows: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()
        self._last_cleanup = time.time()

    async def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: float = 60.0,
    ) -> None:
        """
        Check and record request against sliding time window.
        Raises HTTP 429 if limit is exceeded.
        """
        if not settings.RATE_LIMIT_ENABLED or max_requests <= 0:
            return

        now = time.time()
        cutoff = now - window_seconds

        async with self._lock:
            # Periodic cleanup of empty or fully expired queues every 60 seconds
            if now - self._last_cleanup > 60.0:
                self._cleanup_stale_keys(cutoff)
                self._last_cleanup = now

            timestamps = self._windows[key]

            # Pop timestamps older than the sliding window
            while timestamps and timestamps[0] < cutoff:
                timestamps.popleft()

            if len(timestamps) >= max_requests:
                oldest = timestamps[0]
                retry_after = max(1, math.ceil(window_seconds - (now - oldest)))
                logger.warning(
                    "Rate limit exceeded for key=%s (requests=%d, limit=%d). Retry-After=%ds",
                    key,
                    len(timestamps),
                    max_requests,
                    retry_after,
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "message": "Too many requests. Please slow down.",
                        "limit": max_requests,
                        "window_seconds": int(window_seconds),
                        "retry_after": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )

            timestamps.append(now)

    def _cleanup_stale_keys(self, cutoff: float) -> None:
        """Remove keys with no remaining active timestamps to prevent unbounded memory growth."""
        keys_to_delete = []
        for k, dq in self._windows.items():
            while dq and dq[0] < cutoff:
                dq.popleft()
            if not dq:
                keys_to_delete.append(k)
        for k in keys_to_delete:
            del self._windows[k]

    def reset(self) -> None:
        """Reset all rate limit tracking (useful in tests)."""
        self._windows.clear()


# Global singletons
ip_resolver = ClientIpResolver(settings.TRUSTED_PROXIES)
rate_limiter = SlidingWindowRateLimiter()


def rate_limit(
    limit: int | Callable[[], int],
    endpoint_name: str,
    window_seconds: float = 60.0,
):
    """
    FastAPI dependency factory enforcing rate limits on endpoints per client IP.
    """
    async def dependency(request: Request) -> None:
        max_reqs = limit() if callable(limit) else limit
        client_ip = ip_resolver.resolve_client_ip(request)
        key = f"{endpoint_name}:{client_ip}"
        await rate_limiter.check_rate_limit(
            key=key,
            max_requests=max_reqs,
            window_seconds=window_seconds,
        )

    return dependency
