from dataclasses import dataclass


@dataclass
class AppSettings:
    api_url: str = "https://api.deepseek.com"
    api_key: str = ""
    model: str = "deepseek-v4-flash"

    def update(self, api_url: str, api_key: str, model: str) -> None:
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
