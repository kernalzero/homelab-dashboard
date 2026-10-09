"""HTTP reachability checks for service tiles."""
import asyncio
import time

import httpx


async def check(c: httpx.AsyncClient, url: str) -> dict:
    start = time.perf_counter()
    try:
        r = await c.get(url)
        # 401/403 still mean the app answered; only 5xx is "down".
        up = r.status_code < 500
        return {"up": up, "code": r.status_code, "ms": round(1000 * (time.perf_counter() - start))}
    except httpx.HTTPError as e:
        return {"up": False, "code": None, "ms": None, "error": type(e).__name__}


async def check_all(services: list[dict], timeout: float = 5, concurrency: int = 20) -> dict:
    sem = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(verify=False, timeout=timeout, follow_redirects=True) as c:
        async def one(s):
            async with sem:
                return s["id"], await check(c, s.get("check_url") or s["url"])
        results = await asyncio.gather(*(one(s) for s in services if s.get("url") and s.get("check", True)))
    return dict(results)
