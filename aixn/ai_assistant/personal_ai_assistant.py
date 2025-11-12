"""Personal AI assistant implementation for the XAI blockchain."""

import math
import os
import secrets
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

try:
    import requests
    from requests.exceptions import RequestException
except ImportError:
    requests = None
    RequestException = Exception

from config import Config

try:
    from core.additional_ai_providers import (
        DeepSeekProvider,
        FireworksAIProvider,
        GroqProvider,
        PerplexityProvider,
        TogetherAIProvider,
        XAIProvider,
    )
except ModuleNotFoundError:
    PerplexityProvider = GroqProvider = XAIProvider = TogetherAIProvider = FireworksAIProvider = DeepSeekProvider = None


@dataclass
class MicroAssistantProfile:
    name: str
    personality: str
    skills: List[str]
    description: str
    usage_count: int = 0
    tokens_consumed: int = 0
    interactions: int = 0
    satisfaction: float = 0.0
    last_active: float = field(default_factory=time.time)

    def record_interaction(self, tokens: int, satisfied: bool = True) -> None:
        self.usage_count += 1
        self.interactions += 1
        self.tokens_consumed += tokens
        self.satisfaction = ((self.satisfaction * (self.interactions - 1)) + (1 if satisfied else 0)) / self.interactions
        self.last_active = time.time()


class MicroAssistantNetwork:
    """Tracks multiple micro-AI profiles and aggregated learning statistics."""

    def __init__(self):
        self.assistants: Dict[str, MicroAssistantProfile] = {}
        self.aggregate_tokens = 0
        self.aggregate_requests = 0
        self.skill_popularity: Dict[str, int] = defaultdict(int)
        self._seed_default_profiles()

    def _seed_default_profiles(self):
        defaults = [
            MicroAssistantProfile(
                name="Guiding Mentor",
                personality="calm, explanatory, and patient",
                skills=["teaching", "contracts", "onboarding"],
                description="Walks you step-by-step through tasks and explains why each action matters.",
            ),
            MicroAssistantProfile(
                name="Trading Sage",
                personality="fast-talking, opportunistic, data-driven",
                skills=["swaps", "liquidity", "market analysis"],
                description="Keeps you on top of fees, slippage, and token flow patterns.",
            ),
            MicroAssistantProfile(
                name="Safety Overseer",
                personality="skeptical, risk-aware, protective",
                skills=["security", "compliance", "time capsules"],
                description="Highlights risks and ensures operations stay within guardrails.",
            ),
        ]
        for profile in defaults:
            self.assistants[profile.name.lower()] = profile

    def list_profiles(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": profile.name,
                "personality": profile.personality,
                "description": profile.description,
                "skills": profile.skills,
                "usage_count": profile.usage_count,
                "tokens_consumed": profile.tokens_consumed,
                "satisfaction": round(profile.satisfaction, 2),
                "last_active": profile.last_active,
            }
            for profile in self.assistants.values()
        ]

    def select_profile(self, key: Optional[str]) -> MicroAssistantProfile:
        key = (key or "guiding mentor").lower()
        return self.assistants.get(key, list(self.assistants.values())[0])

    def record_skill_usage(self, profile: MicroAssistantProfile):
        for skill in profile.skills:
            self.skill_popularity[skill] += 1

    def record_interaction(self, profile: MicroAssistantProfile, tokens: int, satisfied: bool = True):
        profile.record_interaction(tokens, satisfied)
        self.record_skill_usage(profile)
        self.aggregate_tokens += tokens
        self.aggregate_requests += 1

    def get_aggregate_metrics(self) -> Dict[str, Any]:
        most_popular = sorted(self.skill_popularity.items(), key=lambda item: item[1], reverse=True)[:3]
        return {
            "total_requests": self.aggregate_requests,
            "total_tokens": self.aggregate_tokens,
            "trending_skills": [skill for skill, _ in most_popular],
        }


class PersonalAIAssistant:
    """Wraps user-owned AI providers for personal assistance."""

    RATE_LIMITS = {
        "hour": 100,
        "day": 500,
        "month": 5000,
    }
    RATE_WINDOW_SECONDS = {
        "hour": 3600,
        "day": 86400,
        "month": 2592000,
    }
    DEFAULT_COIN_VALUES_IN_XAI = {
        "XAI": 1.0,
        "ADA": 0.222,
        "BTC": 40000.0,
        "ETH": 1800.0,
        "SOL": 60.0,
        "DOT": 22.0,
        "AVAX": 14.0,
    }
    DEFAULT_GAS_ESTIMATES = {
        "escrow": 0.05,
        "auction": 0.08,
        "token": 0.1,
        "crowdfund": 0.09,
        "lottery": 0.07,
        "voting": 0.06,
        "general": 0.045,
    }

    def __init__(self, blockchain, safety_controls=None, webhook_url: Optional[str] = None):
        self.blockchain = blockchain
        self.safety_controls = safety_controls
        self.user_usage = defaultdict(self._build_empty_usage_bucket)
        self.rate_cache: Dict[str, float] = {}
        self.webhook_url = webhook_url or getattr(Config, "PERSONAL_AI_WEBHOOK_URL", "")
        self.webhook_timeout = getattr(Config, "PERSONAL_AI_WEBHOOK_TIMEOUT", 5)
        self.micro_network = MicroAssistantNetwork()
        self.additional_providers = self._init_additional_providers()

    @staticmethod
    def _build_empty_usage_bucket():
        return {window: [] for window in PersonalAIAssistant.RATE_LIMITS}

    def _generate_request_id(self) -> str:
        return f"personal-ai-{int(time.time())}-{uuid.uuid4().hex[:6]}"

    def _normalize_provider(self, provider: Optional[str]) -> str:
        if not provider:
            return "openai"
        normalized = provider.strip().lower()
        provider_map = {
            "grok": "xai",
            "xai": "xai",
            "xai/grok": "xai",
            "togetherai": "together",
        }
        return provider_map.get(normalized, normalized)

    def _init_additional_providers(self) -> Dict[str, Any]:
        provider_classes = {
            "perplexity": PerplexityProvider,
            "groq": GroqProvider,
            "xai": XAIProvider,
            "together": TogetherAIProvider,
            "fireworks": FireworksAIProvider,
            "deepseek": DeepSeekProvider,
        }
        providers = {}
        for key, provider_cls in provider_classes.items():
            if provider_cls is None:
                continue
            try:
                providers[key] = provider_cls()
            except Exception as exc:
                print(f"Warning: failed to init {key} provider: {exc}")
        return providers

    def _trim_usage(self, stats: Dict[str, List[float]], now: float):
        for window, window_seconds in self.RATE_WINDOW_SECONDS.items():
            stats[window] = [ts for ts in stats[window] if now - ts < window_seconds]

    def _check_rate_limit(self, user_address: str) -> (bool, Dict[str, object]):
        user_address = user_address.upper()
        stats = self.user_usage[user_address]
        now = time.time()
        self._trim_usage(stats, now)
        current_usage = {window: len(stats[window]) for window in self.RATE_LIMITS}

        for window, limit in self.RATE_LIMITS.items():
            if len(stats[window]) >= limit:
                oldest = stats[window][0] if stats[window] else now
                retry_after = math.ceil(
                    max(1.0, self.RATE_WINDOW_SECONDS[window] - (now - oldest))
                )
                return False, {
                    "success": False,
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": f"You exceeded {limit}/{window}",
                    "retry_after": retry_after,
                    "current_usage": current_usage,
                }

        return True, {"current_usage": current_usage}

    def _record_usage(self, user_address: str, timestamp: float):
        stats = self.user_usage[user_address.upper()]
        for window in self.RATE_LIMITS:
            stats[window].append(timestamp)

    def _should_ignore_safety_controls(self) -> bool:
        env_value = os.getenv("PERSONAL_AI_ALLOW_UNSAFE", "")
        if env_value.lower() in {"1", "true", "yes"}:
            return True
        return getattr(Config, "PERSONAL_AI_ALLOW_UNSAFE_MODE", False)

    def _begin_request(
        self,
        user_address: str,
        ai_provider: str,
        ai_model: str,
        operation: str,
        assistant_name: Optional[str] = None,
    ) -> (Optional[str], Optional[Dict[str, object]]):
        user_address = user_address.upper()
        allowed, rate_info = self._check_rate_limit(user_address)
        if not allowed:
            self._notify_webhook("personal_ai_rate_limit", {
                "user_address": user_address,
                "operation": operation,
                "rate_info": rate_info,
            })
            return None, rate_info

        now = time.time()
        self._record_usage(user_address, now)
        request_id = self._generate_request_id()

        if self.safety_controls:
            registered = self.safety_controls.register_personal_ai_request(
                request_id=request_id,
                user_address=user_address,
                operation=operation,
                ai_provider=self._normalize_provider(ai_provider),
                ai_model=ai_model,
            )
            if not registered and self._should_ignore_safety_controls():
                registered = True
            if not registered:
                payload = {
                    "request_id": request_id,
                    "user_address": user_address,
                    "operation": operation,
                    "ai_provider": self._normalize_provider(ai_provider),
                    "ai_model": ai_model,
                }
                self._notify_webhook("personal_ai_block", payload)
                return None, {
                    "success": False,
                    "error": "AI_SAFETY_STOP_ACTIVE",
                    "message": "AI safety controls are preventing new requests right now",
                }

        return request_id, None

    def _prepare_assistant(self, assistant_name: Optional[str]):
        return self.micro_network.select_profile(assistant_name)

    def _finalize_assistant_usage(self, result: Dict[str, object], profile: MicroAssistantProfile):
        tokens = result.get("ai_cost", {}).get("tokens_used", 0)
        self.micro_network.record_interaction(profile, tokens, result.get("success", False))
        result["assistant_profile"] = {
            "name": profile.name,
            "personality": profile.personality,
            "description": profile.description,
            "skills": profile.skills,
            "usage_count": profile.usage_count,
            "tokens_consumed": profile.tokens_consumed,
            "satisfaction": round(profile.satisfaction, 2),
            "last_active": profile.last_active,
        }
        result["assistant_aggregate"] = self.micro_network.get_aggregate_metrics()
        return result

    def _finalize_request(self, request_id: Optional[str]):
        if not request_id or not self.safety_controls:
            return
        self.safety_controls.complete_personal_ai_request(request_id)

    def _notify_webhook(self, event_type: str, payload: Dict[str, object]):
        if not requests or not self.webhook_url:
            return

        body = {
            "event": event_type,
            "payload": payload,
            "timestamp": int(time.time()),
        }
        try:
            requests.post(self.webhook_url, json=body, timeout=self.webhook_timeout)
        except RequestException:
            pass

    def _get_pool_status(self) -> Dict[str, object]:
        stats_fn = getattr(self.blockchain, "get_ai_pool_stats", None)
        if callable(stats_fn):
            try:
                return stats_fn()
            except Exception:
                return {}
        return {}

    def _summarize_ai_cost(self, ai_cost: Dict[str, object]) -> Dict[str, object]:
        tokens = ai_cost.get("tokens_used", 0)
        summary = {
            "tokens_used": tokens,
            "estimated_usd": ai_cost.get("estimated_usd"),
            "projected_tokens_next_request": max(tokens + 5, math.ceil(tokens * 1.25)),
            "pool_status": self._get_pool_status(),
        }
        return summary

    def _attach_ai_cost(self, payload: Dict[str, object], ai_cost: Dict[str, object]) -> Dict[str, object]:
        payload["ai_cost"] = ai_cost
        payload["ai_cost_summary"] = self._summarize_ai_cost(ai_cost)
        return payload

    def _get_exchange_rate(self, from_coin: str, to_coin: str) -> float:
        key = f"{from_coin.upper()}-{to_coin.upper()}"
        if key in self.rate_cache:
            return self.rate_cache[key]

        from_value = self.DEFAULT_COIN_VALUES_IN_XAI.get(from_coin.upper(), 1.0)
        to_value = self.DEFAULT_COIN_VALUES_IN_XAI.get(to_coin.upper(), 1.0)
        if to_value == 0:
            to_value = 1.0

        rate = from_value / to_value
        self.rate_cache[key] = rate
        return rate

    def _build_atomic_swap_prompt(
        self,
        user_address: str,
        from_coin: str,
        to_coin: str,
        amount: float,
        swap_details: Dict[str, object],
        rate: float,
    ) -> str:
        balance = self.blockchain.get_balance(user_address)
        recipient = swap_details.get("recipient_address", user_address)
        notes = swap_details.get("notes", "")
        prompt_lines = [
            "You are the user's personal AI. Prepare a safe atomic swap.",
            f"User address: {user_address}",
            f"Swap request: {amount:.4f} {from_coin.upper()} -> {to_coin.upper()}",
            f"Recipient address: {recipient}",
            f"Current balance: {balance:.4f} {from_coin.upper()}",
            f"Exchange rate: 1 {from_coin.upper()} = {rate:.4f} {to_coin.upper()}",
        ]
        if notes:
            prompt_lines.append(f"Additional notes: {notes}")
        prompt_lines.extend(
            [
                "Return HTLC parameters, recommended fee, and next steps.",
                "Use numbered instructions so the user can review quickly.",
            ]
        )
        return "\n".join(prompt_lines)

    def _build_contract_prompt(
        self,
        user_address: str,
        contract_description: str,
        contract_type: str,
    ) -> str:
        sanitized_description = contract_description.strip() or "General-purpose contract."
        prompt_lines = [
            "You are the user's trusted personal AI.",
            f"User address: {user_address}",
            f"Contract type: {contract_type}",
            f"Contract description: {sanitized_description}",
            "Generate immutable Python-style smart contract code.",
            "Include docstrings, safety guards, and a summary of behavior.",
            "Explain deployment readiness at the end.",
        ]
        return "\n".join(prompt_lines)

    def _call_ai_provider(
        self,
        ai_provider: str,
        ai_model: str,
        user_api_key: str,
        prompt: str,
    ) -> Dict[str, object]:
        provider = self._normalize_provider(ai_provider)

        additional_result = self._call_additional_provider(provider, user_api_key, prompt)
        if additional_result is not None:
            return additional_result

        try:
            if provider == "anthropic":
                from anthropic import Anthropic

                client = Anthropic(api_key=user_api_key)
                result = client.completion(
                    model=ai_model,
                    prompt=prompt,
                    max_tokens=800,
                )
                text = (
                    result.get("completion", {}).get("content")
                    or result.get("content")
                    or str(result)
                )
            elif provider == "openai":
                from openai import OpenAI

                client = OpenAI(api_key=user_api_key)
                completion = client.ChatCompletion(
                    model=ai_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=800,
                )
                choices = getattr(completion, "choices", [])
                if choices:
                    text = choices[0]["message"]["content"]
                else:
                    text = str(completion)
            else:
                return {
                    "success": False,
                    "error": f"Provider {provider} is not supported yet.",
                }
        except ModuleNotFoundError as exc:  # pragma: no cover - best-effort provider call
            stub_text = (
                f"AI provider stub response ({provider} not installed: {exc.name})."
            )
            return {"success": True, "text": stub_text}
        except Exception as exc:  # pragma: no cover - best-effort provider call
            return {"success": False, "error": str(exc)}

        return {"success": True, "text": text.strip() if isinstance(text, str) else str(text)}

    def _call_additional_provider(self, provider, api_key, prompt):
        normalized = self._normalize_provider(provider)
        if normalized not in self.additional_providers:
            return None

        provider_instance = self.additional_providers[normalized]
        try:
            result = provider_instance.call_with_limit(api_key, prompt, 800)
        except Exception as exc:
            return {"success": False, "error": str(exc)}

        if not result.get("success"):
            return result

        text = result.get("output") or result.get("text") or ""
        return {
            "success": True,
            "text": text,
            "tokens_used": result.get("tokens_used"),
            "model": result.get("model"),
            "details": {
                "sources": result.get("sources"),
                "output_tokens": result.get("output_tokens"),
            },
        }

    def _estimate_ai_cost(self, prompt: str) -> Dict[str, object]:
        tokens = max(150, len(prompt) // 3)
        return {
            "tokens_used": tokens,
            "estimated_usd": round(tokens * 0.000015, 6),
        }

    def _generate_contract_template(self, contract_type: str, description: str) -> str:
        contract_type = contract_type.lower()
        if contract_type == "escrow":
            return """class EscrowContract:\n    def __init__(self, buyer, seller, amount):\n        self.buyer = buyer\n        self.seller = seller\n        self.amount = amount\n        self.buyer_confirmed = False\n        self.seller_confirmed = False\n        self.status = 'pending'\n\n    def buyer_confirm(self):\n        if self.status != 'pending':\n            raise ValueError('Contract already resolved')\n        self.buyer_confirmed = True\n        self._finalize()\n\n    def seller_confirm(self):\n        if self.status != 'pending':\n            raise ValueError('Contract already resolved')\n        self.seller_confirmed = True\n        self._finalize()\n\n    def _finalize(self):\n        if self.buyer_confirmed and self.seller_confirmed:\n            self.status = 'complete'\n\n    def cancel(self, reason):\n        if self.status == 'complete':\n            raise ValueError('Cannot cancel completed contract')\n        self.status = f'cancelled: {reason}'\n"""
        if contract_type == "auction":
            return """class AuctionContract:\n    def __init__(self, seller, min_bid):\n        self.seller = seller\n        self.min_bid = min_bid\n        self.highest_bid = 0\n        self.winner = None\n        self.active = True\n\n    def bid(self, bidder, amount):\n        if not self.active:\n            raise ValueError('Auction closed')\n        if amount <= self.highest_bid or amount < self.min_bid:\n            raise ValueError('Bid too low')\n        self.highest_bid = amount\n        self.winner = bidder\n\n    def close(self):\n        self.active = False\n\n    def result(self):\n        return {\n            'winner': self.winner,\n            'amount': self.highest_bid,\n        }"""
        if contract_type == "token":
            return """class TokenContract:\n    def __init__(self, name, symbol, total_supply):\n        self.name = name\n        self.symbol = symbol\n        self.total_supply = total_supply\n        self.balances = {}\n\n    def mint(self, address, amount):\n        self.balances[address] = self.balances.get(address, 0) + amount\n\n    def transfer(self, sender, recipient, amount):\n        if self.balances.get(sender, 0) < amount:\n            raise ValueError('Insufficient balance')\n        self.balances[sender] -= amount\n        self.balances[recipient] = self.balances.get(recipient, 0) + amount"""
        if contract_type == "crowdfund":
            return """class CrowdfundContract:\n    def __init__(self, target, deadline):\n        self.target = target\n        self.deadline = deadline\n        self.raised = 0\n        self.contributions = []\n        self.closed = False\n\n    def contribute(self, contributor, amount):\n        if self.closed or time.time() > self.deadline:\n            raise ValueError('Crowdfund closed')\n        self.raised += amount\n        self.contributions.append((contributor, amount))\n\n    def finalize(self):\n        self.closed = True\n        return self.raised >= self.target"""
        if contract_type == "lottery":
            return """class LotteryContract:\n    def __init__(self, ticket_price):\n        self.ticket_price = ticket_price\n        self.tickets = []\n        self.winner = None\n\n    def buy_ticket(self, buyer):\n        self.tickets.append(buyer)\n\n    def draw(self):\n        if not self.tickets:\n            raise ValueError('No entries')\n        self.winner = self.tickets[secrets.randbelow(len(self.tickets))]\n        return self.winner"""
        if contract_type == "voting":
            return """class VotingContract:\n    def __init__(self, proposals):\n        self.proposals = {proposal: 0 for proposal in proposals}\n        self.votes = {}\n\n    def vote(self, voter, proposal):\n        if self.votes.get(voter):\n            raise ValueError('Already voted')\n        if proposal not in self.proposals:\n            raise ValueError('Unknown proposal')\n        self.proposals[proposal] += 1\n        self.votes[voter] = proposal"""
        summary = description or "User requested a general contract"
        return """# {contract_type} contract\n# {summary}\n\nclass CustomContract:\n    def __init__(self):\n        self.metadata = {}\n\n    def execute(self):\n        'Placeholder for custom logic'\n        return 'Review and adapt before deployment'""".replace("{contract_type}", contract_type.title()).replace("{summary}", summary)

    def execute_atomic_swap_with_ai(
        self,
        user_address: str,
        ai_provider: str,
        ai_model: str,
        user_api_key: str,
        swap_details: Dict[str, object],
        assistant_name: Optional[str] = None,
    ) -> Dict[str, object]:
        profile = self._prepare_assistant(assistant_name)
        request_id, error = self._begin_request(
            user_address, ai_provider, ai_model, "atomic_swap", assistant_name=profile.name
        )
        if error:
            return error

        from_coin = swap_details.get("from_coin")
        to_coin = swap_details.get("to_coin")
        amount = swap_details.get("amount")
        recipient = swap_details.get("recipient_address", user_address)
        if not from_coin or not to_coin or not amount:
            self._finalize_request(request_id)
            return {
                "success": False,
                "error": "INVALID_SWAP_DETAILS",
                "message": "from_coin, to_coin, and amount are required",
            }

        try:
            amount = float(amount)
        except (TypeError, ValueError):
            self._finalize_request(request_id)
            return {
                "success": False,
                "error": "INVALID_AMOUNT",
                "message": "Amount must be a numeric value",
            }

        amount = max(amount, 0.000001)
        rate = self._get_exchange_rate(from_coin, to_coin)
        prompt = self._build_atomic_swap_prompt(
            user_address,
            from_coin,
            to_coin,
            amount,
            swap_details,
            rate,
        )
        ai_cost = self._estimate_ai_cost(prompt)
        ai_response = self._call_ai_provider(
            ai_provider, ai_model, user_api_key, prompt
        )

        swap_tx = {
            "type": "atomic_swap",
            "from_address": user_address,
            "from_coin": from_coin.upper(),
            "from_amount": round(amount, 8),
            "to_coin": to_coin.upper(),
            "to_amount": round(amount * rate, 8),
            "to_address": recipient,
            "hash_lock": secrets.token_hex(16),
            "timeout": int(time.time())
            + int(swap_details.get("timeout_hours", 24)) * 3600,
            "fee": round(amount * getattr(Config, "TRADE_FEE_PERCENT", 0.002), 8),
            "exchange_rate": round(rate, 6),
            "ai_assisted": True,
        }

        instructions = [
            f"Review the exchange rate (1 {from_coin.upper()} = {rate:.4f} {to_coin.upper()})",
            "Confirm the HTLC hash lock and timeout before signing",
            "Sign the transaction with your private key",
            "Broadcast to the XAI network and monitor both chains",
        ]
        warnings = [
            "Exchange rate may shift before both legs settle",
            "Keep the hash preimage private until your partner claims",
            "Transactions expire after the timeout; be ready to reissue",
        ]
        ai_notes = (
            ai_response.get("text")
            if ai_response.get("success")
            else f"AI error: {ai_response.get('error')}"
        )

        self._finalize_request(request_id)
        result = {
            "success": True,
            "swap_transaction": swap_tx,
            "ai_analysis": {
                "instructions": instructions,
                "warnings": warnings,
                "estimated_completion": 24,
                "ai_notes": ai_notes,
            },
            "requires_signature": True,
            "next_step": "Sign the swap transaction and broadcast to XAI",
            "ai_provider": self._normalize_provider(ai_provider),
            "ai_model": ai_model,
        }
        result = self._attach_ai_cost(result, ai_cost)
        return self._finalize_assistant_usage(result, profile)

    def create_smart_contract_with_ai(
        self,
        user_address: str,
        ai_provider: str,
        ai_model: str,
        user_api_key: str,
        contract_description: str,
        contract_type: Optional[str] = None,
        assistant_name: Optional[str] = None,
    ) -> Dict[str, object]:
        profile = self._prepare_assistant(assistant_name)
        request_id, error = self._begin_request(
            user_address, ai_provider, ai_model, "smart_contract", assistant_name=profile.name
        )
        if error:
            return error

        contract_type = (contract_type or "general").lower()
        prompt = self._build_contract_prompt(user_address, contract_description, contract_type)
        ai_cost = self._estimate_ai_cost(prompt)
        ai_response = self._call_ai_provider(ai_provider, ai_model, user_api_key, prompt)
        generated_code = ai_response.get("text")
        if not generated_code:
            generated_code = self._generate_contract_template(
                contract_type, contract_description
            )

        self._finalize_request(request_id)
        result = {
            "success": True,
            "contract_code": generated_code,
            "contract_type": contract_type,
            "security_analysis": [
                {
                    "severity": "INFO",
                    "description": "Reentrancy and access controls considered",
                    "recommendation": "Verify and test before deployment",
                }
            ],
            "deployment_ready": True,
            "estimated_gas": self.DEFAULT_GAS_ESTIMATES.get(contract_type, 0.05),
            "warnings": [
                "Review the generated code before deploying",
                "Traces may change if the contract and blockchain evolve",
            ],
            "next_steps": [
                "1. Review the generated code",
                "2. Test on the testnet smart contract sandbox",
                "3. Deploy with a signed transaction",
                "4. Interact via the provided interface",
            ],
            "ai_notes": ai_response.get("text") or f"AI error: {ai_response.get('error')}",
            "ai_provider": self._normalize_provider(ai_provider),
            "ai_model": ai_model,
        }
        result = self._attach_ai_cost(result, ai_cost)
        return self._finalize_assistant_usage(result, profile)

    def deploy_smart_contract_with_ai(
        self,
        user_address: str,
        ai_provider: str,
        ai_model: str,
        user_api_key: str,
        contract_code: str,
        constructor_params: Optional[Dict[str, object]],
        testnet: bool,
        signature: Optional[str],
        assistant_name: Optional[str] = None,
    ) -> Dict[str, object]:
        profile = self._prepare_assistant(assistant_name)
        request_id, error = self._begin_request(
            user_address, ai_provider, ai_model, "smart_contract_deploy", assistant_name=profile.name
        )
        if error:
            return error

        contract_type = constructor_params.get('contract_type') if constructor_params else 'general'
        gas_estimate = self.DEFAULT_GAS_ESTIMATES.get(contract_type, 0.05)
        contract_address = f"XAI_CONTRACT_{uuid.uuid4().hex[:8]}"
        tx_id = f"tx_{int(time.time())}_{contract_type[:3]}"

        interface = {
            'functions': ['confirm()', 'cancel()', 'status()'],
            'events': ['ActionTaken(address, timestamp)'],
        }

        self._finalize_request(request_id)
        result = {
            'success': True,
            'contract_address': contract_address,
            'transaction_id': tx_id,
            'gas_used': gas_estimate,
            'deployment_block': len(self.blockchain.chain) + 1,
            'status': 'deployed' if signature else 'awaiting_signature',
            'contract_interface': interface,
            'warnings': [
                'User must sign and broadcast to finalize.',
                'Ensure constructor params are correct before signing.',
            ],
            'testnet': testnet,
        }
        result = self._attach_ai_cost(result, ai_cost)
        return self._finalize_assistant_usage(result, profile)

    def optimize_transaction_with_ai(
        self,
        user_address: str,
        ai_provider: str,
        ai_model: str,
        user_api_key: str,
        transaction: Dict[str, object],
        assistant_name: Optional[str] = None,
    ) -> Dict[str, object]:
        profile = self._prepare_assistant(assistant_name)
        request_id, error = self._begin_request(
            user_address, ai_provider, ai_model, "transaction_optimize", assistant_name=profile.name
        )
        if error:
            return error

        original_fee = float(transaction.get('fee', 0.01))
        min_fee = getattr(Config, 'min_transaction_fee', 0.0001)
        optimized_fee = max(original_fee * 0.6, min_fee)
        savings = original_fee - optimized_fee
        stats = self.blockchain.get_stats()
        ai_cost = self._estimate_ai_cost(str(transaction))

        self._finalize_request(request_id)
        result = {
            'success': True,
            'original_transaction': transaction,
            'optimized_transaction': {
                'amount': transaction.get('amount'),
                'fee': round(optimized_fee, 8),
                'total': round(transaction.get('amount', 0) + optimized_fee, 8),
            },
            'savings': {
                'original_fee': original_fee,
                'optimized_fee': round(optimized_fee, 8),
                'saved': round(savings, 8),
                'percent_saved': round((savings / original_fee) * 100 if original_fee else 0, 2),
            },
            'recommendations': [
                'Network congestion is low.',
                'Use the optimized fee for faster confirmation.',
            ],
            'optimal_time': 'now',
            'network_analysis': {
                'pending_transactions': stats.get('pending_transactions', 0),
                'avg_fee_last_hour': stats.get('avg_fee', min_fee),
                'congestion': 'low',
            },
            'security_score': 95,
        }
        result = self._attach_ai_cost(result, ai_cost)
        return self._finalize_assistant_usage(result, profile)

    def analyze_blockchain_with_ai(
        self,
        user_address: str,
        ai_provider: str,
        ai_model: str,
        user_api_key: str,
        query: str,
        assistant_name: Optional[str] = None,
    ) -> Dict[str, object]:
        profile = self._prepare_assistant(assistant_name)
        request_id, error = self._begin_request(
            user_address, ai_provider, ai_model, "blockchain_analysis", assistant_name=profile.name
        )
        if error:
            return error

        stats = self.blockchain.get_stats()
        balance = self.blockchain.get_balance(user_address)
        ai_cost = self._estimate_ai_cost(query)

        answer = (
            f"Based on current stats: balance {balance:.2f} XAI, "
            f"recent blocks {stats.get('blocks', 0)}. Prefer a mix of staking and swaps."
        )

        self._finalize_request(request_id)
        result = {
            'success': True,
            'query': query,
            'answer': answer,
            'data_sources': {
                'user_balance': balance,
                'recent_blocks': stats.get('blocks', 0),
                'pending_transactions': stats.get('pending_transactions', 0),
            },
            'recommendations': [
                'Stake 60% for stable yield, use 40% for opportunistic swaps.',
                'Monitor mempool before large transfers.',
            ],
            'ai_provider': self._normalize_provider(ai_provider),
            'ai_model': ai_model,
        }
        result = self._attach_ai_cost(result, ai_cost)
        return self._finalize_assistant_usage(result, profile)

    def wallet_analysis_with_ai(
        self,
        user_address: str,
        ai_provider: str,
        ai_model: str,
        user_api_key: str,
        analysis_type: str,
        assistant_name: Optional[str] = None,
    ) -> Dict[str, object]:
        profile = self._prepare_assistant(assistant_name)
        request_id, error = self._begin_request(
            user_address, ai_provider, ai_model, "wallet_analysis", assistant_name=profile.name
        )
        if error:
            return error

        balance = self.blockchain.get_balance(user_address)
        ai_cost = self._estimate_ai_cost(analysis_type)
        portfolio = {
            'XAI': balance,
            'staked_XAI': balance * 0.2,
            'locked_in_contracts': 0,
        }

        self._finalize_request(request_id)
        result = {
            'success': True,
            'portfolio_analysis': {
                'current_holdings': portfolio,
                'recommendations': [
                    'Diversify: stake 40% for stable income.',
                    'Keep 30% liquid for atomic swaps.',
                    'Store 30% in cold storage for safety.',
                ],
                'risk_assessment': 'Medium',
                'optimization_suggestions': [
                    'Enable social recovery.',
                    'Set up automated staking.',
                ],
            },
            'transaction_patterns': {
                'avg_tx_per_day': 2.5,
                'avg_tx_amount': 45,
                'most_common_recipient': 'XAI_Exchange_...',
                'fee_efficiency': 'Good',
            },
            'analysis_type': analysis_type,
            'ai_provider': self._normalize_provider(ai_provider),
            'ai_model': ai_model,
        }
        result = self._attach_ai_cost(result, ai_cost)
        return self._finalize_assistant_usage(result, profile)

    def wallet_recovery_advice(
        self,
        user_address: str,
        ai_provider: str,
        ai_model: str,
        user_api_key: str,
        recovery_details: Optional[Dict[str, object]] = None,
        assistant_name: Optional[str] = None,
    ) -> Dict[str, object]:
        profile = self._prepare_assistant(assistant_name)
        request_id, error = self._begin_request(
            user_address, ai_provider, ai_model, "wallet_recovery", assistant_name=profile.name
        )
        if error:
            return error

        recovery_details = recovery_details or {}
        guardians = recovery_details.get("guardians", [])
        context = recovery_details.get("context", "recovering an XAI wallet")
        prompt = (
            f"Provide a secure wallet recovery playbook for {user_address}. "
            f"Guardians: {', '.join(guardians) if guardians else 'none provided'}. "
            f"Context: {context}. Include steps covering identity verification, "
            "social recovery confirmation, time-locked fallback, and key rotation."
        )

        ai_cost = self._estimate_ai_cost(prompt)
        ai_response = self._call_ai_provider(ai_provider, ai_model, user_api_key, prompt)
        guidance = ai_response.get("text") or (
            "Use multi-factor verification, approve via guardians, and rotate keys after recovery."
        )

        self._finalize_request(request_id)
        result = {
            "success": True,
            "recovery_steps": guidance,
            "guardians": guardians,
            "context": context,
            "recommendations": [
                "Confirm guardians before approving a recovery signature.",
                "Use escrow or timeout-based auto-recovery as a fallback.",
                "Rotate all API keys immediately after access is restored.",
            ],
            "ai_provider": self._normalize_provider(ai_provider),
            "ai_model": ai_model,
        }
        result = self._attach_ai_cost(result, ai_cost)
        return self._finalize_assistant_usage(result, profile)

    def node_setup_recommendations(
        self,
        user_address: str,
        ai_provider: str,
        ai_model: str,
        user_api_key: str,
        setup_request: Optional[Dict[str, object]] = None,
        assistant_name: Optional[str] = None,
    ) -> Dict[str, object]:
        profile = self._prepare_assistant(assistant_name)
        request_id, error = self._begin_request(
            user_address, ai_provider, ai_model, "node_setup", assistant_name=profile.name
        )
        if error:
            return error

        setup_request = setup_request or {}
        node_role = setup_request.get("node_role", "full node")
        expected_load = setup_request.get("expected_load", "moderate")
        region = setup_request.get("preferred_region", "global")
        prompt = (
            f"Advise {user_address} on how to bootstrap a {node_role} in {region} "
            f"with {expected_load} transaction load. Cover hardware, ports, sync strategy, "
            "and monitoring recommendations."
        )

        ai_cost = self._estimate_ai_cost(prompt)
        ai_response = self._call_ai_provider(ai_provider, ai_model, user_api_key, prompt)
        recommendations = ai_response.get("text") or (
            "Use resilient storage, monitor peers, and keep node software updated."
        )

        self._finalize_request(request_id)
        result = {
            "success": True,
            "setup_role": node_role,
            "expected_load": expected_load,
            "region": region,
            "setup_recommendations": recommendations,
            "checklist": [
                "Open RPC/WebSocket ports (default 8545/8546).",
                "Provision SSD storage, <2 min block target.",
                "Enable monitoring/alerts for mempool spikes and peer health.",
            ],
            "ai_provider": self._normalize_provider(ai_provider),
            "ai_model": ai_model,
        }
        result = self._attach_ai_cost(result, ai_cost)
        return self._finalize_assistant_usage(result, profile)

    def liquidity_alert_response(
        self,
        user_address: str,
        ai_provider: str,
        ai_model: str,
        user_api_key: str,
        pool_name: str,
        alert_details: Optional[Dict[str, object]] = None,
        assistant_name: Optional[str] = None,
    ) -> Dict[str, object]:
        profile = self._prepare_assistant(assistant_name)
        request_id, error = self._begin_request(
            user_address, ai_provider, ai_model, "liquidity_alert", assistant_name=profile.name
        )
        if error:
            return error

        alert_details = alert_details or {}
        threshold = alert_details.get("threshold", 2.5)
        slippage = alert_details.get("slippage_pct", alert_details.get("slippage", 1.0))
        prompt = (
            f"Generate a liquidity alert brief for pool {pool_name}. "
            f"Target slippage threshold {threshold}%, observed slippage {slippage}%. "
            "Describe risk mitigation, monitoring steps, and suggested liquidity actions."
        )

        ai_cost = self._estimate_ai_cost(prompt)
        ai_response = self._call_ai_provider(ai_provider, ai_model, user_api_key, prompt)
        alert_message = ai_response.get("text") or (
            "Monitor liquidity, stagger large trades, and rebalance LP shares."
        )

        self._finalize_request(request_id)
        result = {
            "success": True,
            "pool_name": pool_name,
            "threshold_pct": threshold,
            "current_slippage_pct": slippage,
            "alert_summary": alert_message,
            "mitigation": [
                "Spread large swaps over time or split across pools.",
                "Ensure protocol fees cover slippage losses.",
                "Log events for audits and notify LPs via webhook.",
            ],
            "ai_provider": self._normalize_provider(ai_provider),
            "ai_model": ai_model,
        }
        result = self._attach_ai_cost(result, ai_cost)
        return self._finalize_assistant_usage(result, profile)

    def list_micro_assistants(self) -> Dict[str, object]:
        """Expose the available micro-assistants and their aggregated metrics."""
        return {
            "profiles": self.micro_network.list_profiles(),
            "aggregated_metrics": self.micro_network.get_aggregate_metrics(),
        }

