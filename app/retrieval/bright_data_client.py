import httpx

from app.config import get_settings

BASE_URL = "https://api.brightdata.com/request"


class BrightDataClient:
    def __init__(self, api_key: str, serp_zone: str, unlocker_zone: str) -> None:
        self.api_key = api_key
        self.serp_zone = serp_zone
        self.unlocker_zone = unlocker_zone

    async def fetch_serp(self, url: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                BASE_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "zone": self.serp_zone,
                    "url": url,
                    "format": "json",
                },
                timeout=60.0,
            )
            response.raise_for_status()
            return response.json()

    async def fetch_unlocker(self, url: str) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                BASE_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "zone": self.unlocker_zone,
                    "url": url,
                    "format": "raw",
                },
                timeout=60.0,
            )
            response.raise_for_status()
            return response.text


def get_bright_data_client() -> BrightDataClient:
    settings = get_settings()
    return BrightDataClient(
        api_key=settings.bright_data_api_key,
        serp_zone=settings.bright_data_serp_zone,
        unlocker_zone=settings.bright_data_unlocker_zone,
    )
