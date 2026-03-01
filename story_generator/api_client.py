import json
import requests
from typing import Generator, Optional
from story_generator.config import DEFAULT_MODEL, API_BASE_URL
from story_generator import settings


class APIClient:
    def __init__(self, api_key: str, model: str = None, config_key: str = "narrative"):
        self.api_key = api_key
        api_config = settings.get_settings().get("api", {})
        self.model = model or api_config.get("model", DEFAULT_MODEL)
        self.api_url = api_config.get("api_url", API_BASE_URL)
        
        config = getattr(settings, f"get_{config_key}_config", settings.get_narrative_config)()
        self.temperature = config.get("temperature", 0.8)
        self.max_tokens = config.get("max_tokens", 800)
        self.system_prompt = config.get("system_prompt", "")
    
    def _call_api(self, prompt: str, system_prompt: str = None) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt or self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"API 调用失败: {e}")
    
    def _call_api_stream(self, prompt: str, system_prompt: str = None) -> Generator[str, None, None]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt or self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": True
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=120, stream=True)
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]
                        if data == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data)
                            if chunk.get("choices") and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"API 调用失败: {e}")
