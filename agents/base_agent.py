"""
Base Agent Class
Foundation for all specialized trading agents
"""
from __future__ import annotations

import json, os, socket
import requests
from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from datetime import datetime

# Settings is optional; we also read env directly to be resilient
try:
    from config.settings import Settings  # type: ignore
except Exception:
    class Settings:  # minimal shim
        LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openrouter.ai/v1/chat/completions")
        OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
        LLM_MODEL = os.getenv("LLM_MODEL", os.getenv("OPENROUTER_MODEL", "qwen/qwen3-coder:free"))
        LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
        GITHUB_REPO = os.getenv("GITHUB_REPO", "https://github.com/Q-alduaij/Lolo-Trading-Agent-.git")

from memory.agent_memory import AgentMemory
from memory.database import Database
from utils.logger import get_logger

logger = get_logger("agents")


class BaseAgent(ABC):
    """Base class for all trading agents"""

    def __init__(self, name: str):
        self.name = name
        self.memory = AgentMemory(name)
        self.db = Database()
        self.logger = get_logger(f"agents.{name}")

    @abstractmethod
    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    # ---------- LLM plumbing ----------

    @staticmethod
    def _env(name: str, default: Optional[str] = None) -> Optional[str]:
        v = os.getenv(name)
        return v if (v is not None and str(v).strip() != "") else default

    def _openrouter_payload(self, messages: List[Dict[str, str]], temperature: float) -> Dict[str, Any]:
        model = self._env("LLM_MODEL", Settings.LLM_MODEL) or self._env("OPENROUTER_MODEL", "qwen/qwen3-coder:free")
        return {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

    def _call_openrouter(self, messages: List[Dict[str, str]], temperature: float) -> Optional[Dict[str, Any]]:
        api_key = self._env("OPENROUTER_API_KEY", Settings.OPENROUTER_API_KEY or "")
        if not api_key:
            self.logger.warning("[LLM] OPENROUTER_API_KEY not set; skipping OpenRouter")
            return None
        url = self._env("LLM_BASE_URL", Settings.LLM_BASE_URL or "https://api.openrouter.ai/v1/chat/completions")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": Settings.GITHUB_REPO,
            "X-Title": "Lolo Trading Agent",
            "Content-Type": "application/json",
        }
        payload = self._openrouter_payload(messages, temperature)
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[LLM] OpenRouter error: {e}")
            return None

    def _call_deepseek_native(self, messages: List[Dict[str, str]], temperature: float) -> Optional[Dict[str, Any]]:
        """
        Native DeepSeek fallback (no OpenRouter). Requires:
          - DEEPSEEK_API_KEY
          - optional DEEPSEEK_MODEL (defaults to 'deepseek-chat')
        """
        api_key = self._env("DEEPSEEK_API_KEY", "")
        if not api_key:
            return None
        url = self._env("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1/chat/completions")
        model = self._env("DEEPSEEK_MODEL", "deepseek-chat")
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": messages, "temperature": temperature}
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"[LLM] DeepSeek error: {e}")
            return None

    def call_llm(self, messages: List[Dict[str, str]], temperature: float | None = None) -> Optional[Dict[str, Any]]:
        """
        Call LLM API for reasoning.
        Primary: OpenRouter (Qwen by default).
        Fallback: DeepSeek native if OpenRouter is down/unset.
        """
        temperature = Settings.LLM_TEMPERATURE if temperature is None else temperature

        # Tag with run id for auditing if set
        run_id = os.getenv("RUN_ID")
        if run_id:
            try:
                messages = list(messages) + [{"role": "system", "content": f"[audit] run_id={run_id} agent={self.name}"}]
            except Exception:
                pass

        # 1) Try OpenRouter
        result = self._call_openrouter(messages, temperature)
        if result:
            return result

        # 2) Fallback → DeepSeek native
        result = self._call_deepseek_native(messages, temperature)
        if result:
            self.logger.info("[LLM] Fallback: DeepSeek native used.")
            return result

        # 3) Nothing worked
        self.logger.error("[LLM] No provider available (OpenRouter failed and DeepSeek not configured).")
        return None

    # ---------- helpers ----------

    def extract_json_from_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        try:
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            if start_idx != -1 and end_idx > start_idx:
                return json.loads(response_text[start_idx:end_idx])
            return json.loads(response_text)
        except Exception as e:
            self.logger.error(f"Failed to parse JSON from LLM response: {e}")
            self.logger.debug(f"Response text: {response_text}")
            return None

    def create_system_message(self, role_description: str) -> Dict[str, str]:
        return {
            "role": "system",
            "content": (
                f"You are {self.name}, {role_description}. "
                f"Provide detailed, data-driven analysis for trading decisions. "
                f"Always respond in valid JSON format when requested."
            ),
        }

    def create_user_message(self, content: str) -> Dict[str, str]:
        return {"role": "user", "content": content}

    def log_decision(self, decision: Dict[str, Any]):
        self.memory.store_decision(decision)
        self.logger.info(f"[{self.name}] Decision: {decision.get('recommendation', 'N/A')}")

    def log_observation(self, observation: Dict[str, Any]):
        self.memory.store_observation(observation)

    def get_recent_decisions(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self.memory.get_recent_decisions(limit)

    def store_insight(self, insight: str, metadata: Dict[str, Any] | None = None):
        self.memory.store_insight(insight, metadata or {})

    def format_analysis_result(
        self,
        recommendation: str,
        confidence: float,
        reasoning: str,
        data: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        return {
            "agent": self.name,
            "recommendation": recommendation,
            "confidence": confidence,
            "reasoning": reasoning,
            "data": data or {},
            "timestamp": datetime.now().isoformat(),
        }
