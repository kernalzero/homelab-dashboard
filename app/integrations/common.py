import httpx


def client(cfg: dict, **kwargs) -> httpx.AsyncClient:
    """HTTP client honoring per-integration verify_ssl (home lab gear is usually self-signed)."""
    return httpx.AsyncClient(
        verify=cfg.get("verify_ssl", False),
        timeout=cfg.get("timeout", 8),
        **kwargs,
    )


def pct(used, total):
    return round(100 * used / total, 1) if total else 0.0
