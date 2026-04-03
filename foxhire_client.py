"""Async HTTP client for the FoxHire API."""

import httpx
import os


class FoxHireError(Exception):
    """Raised when a FoxHire API call fails."""

    def __init__(self, message: str, status_code: int = 0):
        self.status_code = status_code
        super().__init__(message)


class FoxHireClient:
    def __init__(self):
        self.base_url = os.environ.get("FOXHIRE_API_URL", "https://foxhire.fly.dev/api")
        self.email = os.environ["FOXHIRE_EMAIL"]
        self.password = os.environ["FOXHIRE_PASSWORD"]
        self.token = None
        self.client = httpx.AsyncClient(timeout=120.0)

    async def _login(self):
        resp = await self.client.post(
            f"{self.base_url}/auth/login",
            json={"email": self.email, "password": self.password},
        )
        if resp.status_code != 200:
            raise FoxHireError(f"Login failed: {resp.text}", resp.status_code)
        self.token = resp.json()["token"]

    async def _request(self, method: str, path: str, **kwargs) -> dict | list:
        if not self.token:
            await self._login()

        # Routes defined as "/" on a prefixed router (e.g. GET/POST /api/jobs) need
        # trailing slash. Routes with specific paths (e.g. /api/ai/parse-job) reject it.
        url = f"{self.base_url}{path}"
        if not url.endswith("/") and "/ai/" not in path:
            url += "/"

        resp = await self.client.request(
            method,
            url,
            headers={"Authorization": f"Bearer {self.token}"},
            **kwargs,
        )

        # Token expired — re-login once
        if resp.status_code == 401:
            await self._login()
            resp = await self.client.request(
                method,
                url,
                headers={"Authorization": f"Bearer {self.token}"},
                **kwargs,
            )

        if resp.status_code == 402:
            raise FoxHireError(
                "Insufficient credits. Visit https://foxhire.ai to add more.", 402
            )
        if resp.status_code >= 400:
            raise FoxHireError(
                f"API error {resp.status_code}: {resp.text}", resp.status_code
            )
        return resp.json()

    async def list_jobs(self) -> list:
        return await self._request("GET", "/jobs")

    async def parse_job(self, raw_text: str, url: str | None = None) -> dict:
        """Two-step: AI parses text, then we create the job record."""
        payload = {"raw_text": raw_text}
        if url:
            payload["url"] = url
        parsed = await self._request("POST", "/ai/parse-job", json=payload)
        job = await self._request("POST", "/jobs", json=parsed)
        return job

    async def parse_job_url(self, url: str) -> dict:
        """Two-step: AI parses URL, then we create the job record."""
        parsed = await self._request("POST", "/ai/parse-job-url", json={"url": url})
        job = await self._request("POST", "/jobs", json=parsed)
        return job

    async def discover_contacts(self, job_id: int) -> dict:
        return await self._request("POST", f"/ai/discover-contacts/{job_id}")

    async def research_contact(self, contact_id: int) -> dict:
        return await self._request("POST", f"/ai/research-contact/{contact_id}")

    async def draft_email(
        self,
        contact_id: int,
        selected_angles: list | None = None,
        draft_type: str = "initial",
        format: str = "email",
    ) -> dict:
        return await self._request(
            "POST",
            f"/ai/draft-email/{contact_id}",
            json={
                "draft_type": draft_type,
                "format": format,
                "selected_angles": selected_angles or [],
            },
        )
