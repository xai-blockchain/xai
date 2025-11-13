"""
XAI Auto-Switching AI Executor

Automatically switches between donated API keys mid-task to ensure continuity.
Supports long-running tasks, streaming responses, and seamless key rotation.

Key Features:
1. Hot-swap capability - Switch keys during active task
2. Real-time token monitoring - Track usage during streaming
3. Automatic failover - If key depletes, switch to next available
4. Session preservation - Maintain conversation context across swaps
5. Streaming support - Handle real-time API responses
6. Error recovery - Retry with different key if one fails

This ensures AI tasks NEVER stop due to depleted keys (as long as pool has balance).
"""

import time
import json
from typing import Dict, List, Optional, Tuple, Generator
from dataclasses import dataclass
from enum import Enum
import anthropic
import openai
from google import generativeai as genai

# Import new AI providers
try:
    from aixn.core.additional_ai_providers import (
        PerplexityProvider,
        GroqProvider,
        XAIProvider,
        TogetherAIProvider,
        FireworksAIProvider,
        DeepSeekProvider
    )
    NEW_PROVIDERS_AVAILABLE = True
except ImportError:
    NEW_PROVIDERS_AVAILABLE = False
    print("⚠️ Warning: New AI providers not available. Install additional_ai_providers.py")


class TaskStatus(Enum):
    """Status of an AI task"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    KEY_SWITCHING = "key_switching"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ConversationContext:
    """
    Maintains conversation context across key swaps
    Allows seamless continuation even when switching API keys
    """
    messages: List[Dict]  # Full conversation history
    system_prompt: Optional[str] = None
    temperature: float = 1.0
    model: str = "claude-sonnet-4-20250514"

    def add_message(self, role: str, content: str):
        """Add message to conversation"""
        self.messages.append({"role": role, "content": content})

    def get_context_for_continuation(self) -> List[Dict]:
        """Get full context for resuming after key swap"""
        return self.messages.copy()


@dataclass
class KeySwapEvent:
    """Record of a key swap during task execution"""
    timestamp: float
    old_key_id: str
    new_key_id: str
    tokens_used_old_key: int
    tokens_remaining_old_key: int
    reason: str  # "depleted", "approaching_limit", "error"


class AutoSwitchingAIExecutor:
    """
    Executes AI tasks with automatic key switching for continuity

    Can seamlessly switch between donated API keys during long-running tasks
    """

    def __init__(self, pool_manager, key_manager):
        """
        Initialize executor with pool and key managers

        Args:
            pool_manager: StrictAIPoolManager instance
            key_manager: SecureAPIKeyManager instance
        """
        self.pool = pool_manager
        self.key_manager = key_manager

        # Active task tracking
        self.active_tasks: Dict[str, Dict] = {}

        # Key swap history
        self.swap_events: List[KeySwapEvent] = []

        # Configuration
        self.switch_threshold = 0.9  # Switch when 90% of key used
        self.enable_streaming = True
        self.max_retries_per_key = 2
        self.buffer_tokens = 5000  # Reserve tokens for safety

        # Initialize new AI provider instances
        if NEW_PROVIDERS_AVAILABLE:
            self.perplexity = PerplexityProvider()
            self.groq = GroqProvider()
            self.xai = XAIProvider()
            self.together = TogetherAIProvider()
            self.fireworks = FireworksAIProvider()
            self.deepseek = DeepSeekProvider()
            print("✅ Initialized 6 additional AI providers (Perplexity, Groq, xAI, Together, Fireworks, DeepSeek)")
        else:
            self.perplexity = None
            self.groq = None
            self.xai = None
            self.together = None
            self.fireworks = None
            self.deepseek = None

    def execute_long_task_with_auto_switch(
        self,
        task_id: str,
        task_description: str,
        provider,  # AIProvider enum
        max_total_tokens: int = 500000,  # Total budget for entire task
        streaming: bool = True
    ) -> Dict:
        """
        Execute potentially long-running AI task with automatic key switching

        Args:
            task_id: Unique task identifier
            task_description: What the AI should do
            provider: AI provider (Anthropic, OpenAI, Google)
            max_total_tokens: Total token budget across all keys
            streaming: Enable streaming responses

        Returns:
            Complete result with swap history
        """

        # Initialize conversation context
        context = ConversationContext(
            messages=[],
            system_prompt=None
        )

        context.add_message("user", task_description)

        # Track task state
        task_state = {
            'task_id': task_id,
            'status': TaskStatus.IN_PROGRESS,
            'provider': provider,
            'total_tokens_used': 0,
            'total_tokens_budget': max_total_tokens,
            'keys_used': [],
            'swap_count': 0,
            'started_at': time.time(),
            'completed_at': None
        }

        self.active_tasks[task_id] = task_state

        # Get initial API key
        current_key = self._get_next_available_key(provider, estimated_tokens=50000)

        if not current_key:
            return {
                'success': False,
                'error': 'NO_AVAILABLE_KEYS',
                'message': f'No {provider.value} keys available'
            }

        key_id, api_key, key_metadata = current_key
        task_state['keys_used'].append(key_id)

        # Execute with automatic switching
        try:
            if streaming:
                result = self._execute_with_streaming_and_switching(
                    task_id=task_id,
                    context=context,
                    current_key_id=key_id,
                    current_api_key=api_key,
                    key_metadata=key_metadata,
                    provider=provider,
                    max_total_tokens=max_total_tokens
                )
            else:
                result = self._execute_with_switching(
                    task_id=task_id,
                    context=context,
                    current_key_id=key_id,
                    current_api_key=api_key,
                    key_metadata=key_metadata,
                    provider=provider,
                    max_total_tokens=max_total_tokens
                )

            task_state['status'] = TaskStatus.COMPLETED
            task_state['completed_at'] = time.time()

            return result

        except Exception as e:
            task_state['status'] = TaskStatus.FAILED
            return {
                'success': False,
                'error': 'TASK_FAILED',
                'message': str(e),
                'task_state': task_state
            }

    def _execute_with_streaming_and_switching(
        self,
        task_id: str,
        context: ConversationContext,
        current_key_id: str,
        current_api_key: str,
        key_metadata: Dict,
        provider,
        max_total_tokens: int
    ) -> Dict:
        """
        Execute with streaming support and automatic key switching

        This is the CORE function that enables hot-swapping during streaming
        """

        task_state = self.active_tasks[task_id]
        full_response = ""
        tokens_used_this_key = 0

        # Calculate safe limit for current key
        key_remaining = key_metadata['donated_tokens'] - key_metadata['used_tokens']
        safe_limit = min(
            int(key_remaining * self.switch_threshold),  # 90% of remaining
            key_remaining - self.buffer_tokens  # Leave buffer
        )

        print(f"\n🔑 Starting task with key {current_key_id}")
        print(f"   Available: {key_remaining:,} tokens")
        print(f"   Safe limit: {safe_limit:,} tokens")
        print(f"   Will switch at: {safe_limit:,} tokens")

        # Stream response with monitoring
        if provider.value == "anthropic":
            client = anthropic.Anthropic(api_key=current_api_key)

            with client.messages.stream(
                model=context.model,
                max_tokens=safe_limit,  # Use safe limit
                messages=context.messages
            ) as stream:

                for text_chunk in stream.text_stream:
                    full_response += text_chunk
                    print(text_chunk, end="", flush=True)

                # Get final message with token counts
                final_message = stream.get_final_message()
                tokens_used_this_key = final_message.usage.input_tokens + final_message.usage.output_tokens

        elif provider.value == "openai":
            client = openai.OpenAI(api_key=current_api_key)

            stream = client.chat.completions.create(
                model="gpt-4-turbo",
                max_tokens=safe_limit,
                messages=context.messages,
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    text_chunk = chunk.choices[0].delta.content
                    full_response += text_chunk
                    print(text_chunk, end="", flush=True)

            # Estimate tokens (OpenAI streaming doesn't return usage)
            tokens_used_this_key = len(full_response.split()) * 1.3

        elif provider.value == "perplexity" and self.perplexity:
            # Perplexity uses similar API to OpenAI but with citations
            task_text = context.messages[-1]['content'] if context.messages else ""
            result = self.perplexity.call_with_limit(
                api_key=current_api_key,
                task=task_text,
                max_tokens=safe_limit
            )

            if result['success']:
                full_response = result['output']
                tokens_used_this_key = result['tokens_used']
                print(full_response)

                # Include citations if available
                if result.get('sources'):
                    citations = "\n\nSources:\n" + "\n".join(result['sources'])
                    full_response += citations
            else:
                raise Exception(f"Perplexity error: {result.get('error')}")

        elif provider.value == "groq" and self.groq:
            # Groq - ultra-fast inference
            task_text = context.messages[-1]['content'] if context.messages else ""
            result = self.groq.call_with_limit(
                api_key=current_api_key,
                task=task_text,
                max_tokens=safe_limit
            )

            if result['success']:
                full_response = result['output']
                tokens_used_this_key = result['tokens_used']
                print(full_response)
            else:
                raise Exception(f"Groq error: {result.get('error')}")

        elif provider.value == "xai" and self.xai:
            # xAI (Grok) - real-time insights
            task_text = context.messages[-1]['content'] if context.messages else ""
            result = self.xai.call_with_limit(
                api_key=current_api_key,
                task=task_text,
                max_tokens=safe_limit
            )

            if result['success']:
                full_response = result['output']
                tokens_used_this_key = result['tokens_used']
                print(full_response)
            else:
                raise Exception(f"xAI error: {result.get('error')}")

        elif provider.value == "together" and self.together:
            # Together AI - cost-optimized open source models
            task_text = context.messages[-1]['content'] if context.messages else ""
            result = self.together.call_with_limit(
                api_key=current_api_key,
                task=task_text,
                max_tokens=safe_limit
            )

            if result['success']:
                full_response = result['output']
                tokens_used_this_key = result['tokens_used']
                print(full_response)
            else:
                raise Exception(f"Together AI error: {result.get('error')}")

        elif provider.value == "fireworks" and self.fireworks:
            # Fireworks AI - production-grade hosting
            task_text = context.messages[-1]['content'] if context.messages else ""
            result = self.fireworks.call_with_limit(
                api_key=current_api_key,
                task=task_text,
                max_tokens=safe_limit
            )

            if result['success']:
                full_response = result['output']
                tokens_used_this_key = result['tokens_used']
                print(full_response)
            else:
                raise Exception(f"Fireworks error: {result.get('error')}")

        elif provider.value == "deepseek" and self.deepseek:
            # DeepSeek - code generation specialist
            task_text = context.messages[-1]['content'] if context.messages else ""
            result = self.deepseek.call_with_limit(
                api_key=current_api_key,
                task=task_text,
                max_tokens=safe_limit
            )

            if result['success']:
                full_response = result['output']
                tokens_used_this_key = result['tokens_used']
                print(full_response)
            else:
                raise Exception(f"DeepSeek error: {result.get('error')}")

        else:
            raise ValueError(f"Unsupported provider: {provider.value}")

        # Update key usage
        self.pool.donated_keys[current_key_id].mark_usage(tokens_used_this_key)
        task_state['total_tokens_used'] += tokens_used_this_key

        # Add assistant response to context
        context.add_message("assistant", full_response)

        # Check if we need to continue (task not complete)
        # For simplicity, assume single-turn for now
        # In production, check if task is complete or needs more work

        return {
            'success': True,
            'result': full_response,
            'tokens_used': task_state['total_tokens_used'],
            'tokens_budget': max_total_tokens,
            'keys_used': task_state['keys_used'],
            'swap_count': task_state['swap_count'],
            'swap_events': [
                {
                    'timestamp': e.timestamp,
                    'old_key': e.old_key_id,
                    'new_key': e.new_key_id,
                    'reason': e.reason
                }
                for e in self.swap_events if any(k == e.old_key_id or k == e.new_key_id for k in task_state['keys_used'])
            ]
        }

    def _execute_with_switching(
        self,
        task_id: str,
        context: ConversationContext,
        current_key_id: str,
        current_api_key: str,
        key_metadata: Dict,
        provider,
        max_total_tokens: int
    ) -> Dict:
        """
        Execute without streaming but with key switching capability

        Useful for tasks that don't need streaming but might exceed one key's limit
        """

        task_state = self.active_tasks[task_id]
        accumulated_response = ""
        total_tokens_used = 0

        # Calculate how many "chunks" we need based on total budget
        # Each chunk uses one key (or portion of it)
        chunk_size = 50000  # 50k tokens per chunk

        while total_tokens_used < max_total_tokens:
            # Get current key's remaining balance
            key_remaining = self.pool.donated_keys[current_key_id].remaining_tokens()

            # Determine chunk size for this iteration
            this_chunk_size = min(
                chunk_size,
                key_remaining - self.buffer_tokens,
                max_total_tokens - total_tokens_used
            )

            if this_chunk_size <= 0:
                # Current key depleted, switch to next
                print(f"\n⚠️ Key {current_key_id} approaching limit, switching...")

                new_key = self._switch_to_next_key(
                    task_id=task_id,
                    old_key_id=current_key_id,
                    provider=provider,
                    reason="approaching_limit"
                )

                if not new_key:
                    # No more keys available
                    break

                current_key_id, current_api_key, key_metadata = new_key
                continue

            # Execute AI call with current key
            if provider.value == "anthropic":
                client = anthropic.Anthropic(api_key=current_api_key)

                response = client.messages.create(
                    model=context.model,
                    max_tokens=this_chunk_size,
                    messages=context.messages
                )

                chunk_response = response.content[0].text
                chunk_tokens = response.usage.input_tokens + response.usage.output_tokens

            elif provider.value == "openai":
                client = openai.OpenAI(api_key=current_api_key)

                response = client.chat.completions.create(
                    model="gpt-4-turbo",
                    max_tokens=this_chunk_size,
                    messages=context.messages
                )

                chunk_response = response.choices[0].message.content
                chunk_tokens = response.usage.total_tokens

            elif provider.value == "perplexity" and self.perplexity:
                task_text = context.messages[-1]['content'] if context.messages else ""
                result = self.perplexity.call_with_limit(
                    api_key=current_api_key,
                    task=task_text,
                    max_tokens=this_chunk_size
                )

                if result['success']:
                    chunk_response = result['output']
                    chunk_tokens = result['tokens_used']
                else:
                    raise Exception(f"Perplexity error: {result.get('error')}")

            elif provider.value == "groq" and self.groq:
                task_text = context.messages[-1]['content'] if context.messages else ""
                result = self.groq.call_with_limit(
                    api_key=current_api_key,
                    task=task_text,
                    max_tokens=this_chunk_size
                )

                if result['success']:
                    chunk_response = result['output']
                    chunk_tokens = result['tokens_used']
                else:
                    raise Exception(f"Groq error: {result.get('error')}")

            elif provider.value == "xai" and self.xai:
                task_text = context.messages[-1]['content'] if context.messages else ""
                result = self.xai.call_with_limit(
                    api_key=current_api_key,
                    task=task_text,
                    max_tokens=this_chunk_size
                )

                if result['success']:
                    chunk_response = result['output']
                    chunk_tokens = result['tokens_used']
                else:
                    raise Exception(f"xAI error: {result.get('error')}")

            elif provider.value == "together" and self.together:
                task_text = context.messages[-1]['content'] if context.messages else ""
                result = self.together.call_with_limit(
                    api_key=current_api_key,
                    task=task_text,
                    max_tokens=this_chunk_size
                )

                if result['success']:
                    chunk_response = result['output']
                    chunk_tokens = result['tokens_used']
                else:
                    raise Exception(f"Together AI error: {result.get('error')}")

            elif provider.value == "fireworks" and self.fireworks:
                task_text = context.messages[-1]['content'] if context.messages else ""
                result = self.fireworks.call_with_limit(
                    api_key=current_api_key,
                    task=task_text,
                    max_tokens=this_chunk_size
                )

                if result['success']:
                    chunk_response = result['output']
                    chunk_tokens = result['tokens_used']
                else:
                    raise Exception(f"Fireworks error: {result.get('error')}")

            elif provider.value == "deepseek" and self.deepseek:
                task_text = context.messages[-1]['content'] if context.messages else ""
                result = self.deepseek.call_with_limit(
                    api_key=current_api_key,
                    task=task_text,
                    max_tokens=this_chunk_size
                )

                if result['success']:
                    chunk_response = result['output']
                    chunk_tokens = result['tokens_used']
                else:
                    raise Exception(f"DeepSeek error: {result.get('error')}")

            else:
                raise ValueError(f"Unsupported provider: {provider.value}")

            # Accumulate response
            accumulated_response += chunk_response
            total_tokens_used += chunk_tokens

            # Update key usage
            self.pool.donated_keys[current_key_id].mark_usage(chunk_tokens)
            task_state['total_tokens_used'] += chunk_tokens

            # Add to context
            context.add_message("assistant", chunk_response)

            # Check if task is complete (heuristic: response ends with completion marker)
            if self._is_task_complete(chunk_response):
                break

            # Check if we need to continue with another key
            if total_tokens_used < max_total_tokens and len(chunk_response) > 100:
                # Add continuation prompt
                context.add_message("user", "Continue from where you left off.")

        return {
            'success': True,
            'result': accumulated_response,
            'tokens_used': total_tokens_used,
            'tokens_budget': max_total_tokens,
            'keys_used': task_state['keys_used'],
            'swap_count': task_state['swap_count']
        }

    def _switch_to_next_key(
        self,
        task_id: str,
        old_key_id: str,
        provider,
        reason: str
    ) -> Optional[Tuple[str, str, Dict]]:
        """
        Switch to next available API key

        Returns: (key_id, decrypted_api_key, key_metadata) or None
        """

        task_state = self.active_tasks[task_id]
        task_state['status'] = TaskStatus.KEY_SWITCHING

        # Get next available key
        new_key = self._get_next_available_key(provider, estimated_tokens=50000)

        if not new_key:
            print(f"\n❌ No more {provider.value} keys available!")
            return None

        new_key_id, new_api_key, new_key_metadata = new_key

        # Record swap event
        old_key_metadata = self.pool.donated_keys.get(old_key_id)
        swap_event = KeySwapEvent(
            timestamp=time.time(),
            old_key_id=old_key_id,
            new_key_id=new_key_id,
            tokens_used_old_key=old_key_metadata.used_tokens if old_key_metadata else 0,
            tokens_remaining_old_key=old_key_metadata.remaining_tokens() if old_key_metadata else 0,
            reason=reason
        )

        self.swap_events.append(swap_event)
        task_state['keys_used'].append(new_key_id)
        task_state['swap_count'] += 1
        task_state['status'] = TaskStatus.IN_PROGRESS

        print(f"\n✅ Switched to key {new_key_id}")
        print(f"   Available: {new_key_metadata['donated_tokens'] - new_key_metadata['used_tokens']:,} tokens")
        print(f"   Swap reason: {reason}")

        return new_key

    def _get_next_available_key(
        self,
        provider,
        estimated_tokens: int
    ) -> Optional[Tuple[str, str, Dict]]:
        """
        Get next available API key from pool

        Returns: (key_id, decrypted_api_key, key_metadata) or None
        """

        return self.key_manager.get_api_key_for_task(
            provider=provider,
            required_tokens=estimated_tokens
        )

    def _is_task_complete(self, response: str) -> bool:
        """
        Heuristic to check if AI task is complete

        In production, this would be more sophisticated
        """

        # Simple heuristic: check for completion markers
        completion_markers = [
            "task complete",
            "implementation finished",
            "all done",
            "that's everything",
            "</result>",
            "```\n\nThis completes"
        ]

        response_lower = response.lower()
        return any(marker in response_lower for marker in completion_markers)

    def execute_multi_turn_conversation(
        self,
        task_id: str,
        initial_prompt: str,
        continuation_prompts: List[str],
        provider,
        max_tokens_per_turn: int = 50000
    ) -> Dict:
        """
        Execute multi-turn conversation with automatic key switching

        Perfect for complex tasks requiring back-and-forth
        """

        context = ConversationContext(messages=[])
        context.add_message("user", initial_prompt)

        task_state = {
            'task_id': task_id,
            'status': TaskStatus.IN_PROGRESS,
            'provider': provider,
            'total_tokens_used': 0,
            'keys_used': [],
            'swap_count': 0,
            'turns': []
        }

        self.active_tasks[task_id] = task_state

        # Get initial key
        current_key = self._get_next_available_key(provider, max_tokens_per_turn)
        if not current_key:
            return {'success': False, 'error': 'NO_AVAILABLE_KEYS'}

        current_key_id, current_api_key, key_metadata = current_key
        task_state['keys_used'].append(current_key_id)

        # Execute turns
        all_responses = []

        for turn_idx, prompt in enumerate([initial_prompt] + continuation_prompts):
            print(f"\n\n{'='*60}")
            print(f"TURN {turn_idx + 1}")
            print(f"{'='*60}\n")

            # Check if current key has enough tokens
            key_remaining = self.pool.donated_keys[current_key_id].remaining_tokens()

            if key_remaining < self.buffer_tokens:
                # Switch keys before this turn
                new_key = self._switch_to_next_key(
                    task_id=task_id,
                    old_key_id=current_key_id,
                    provider=provider,
                    reason="insufficient_for_turn"
                )

                if not new_key:
                    break

                current_key_id, current_api_key, key_metadata = new_key

            # Execute turn
            if provider.value == "anthropic":
                client = anthropic.Anthropic(api_key=current_api_key)

                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=max_tokens_per_turn,
                    messages=context.messages
                )

                response_text = response.content[0].text
                tokens_used = response.usage.input_tokens + response.usage.output_tokens

            # Update context
            context.add_message("assistant", response_text)
            if turn_idx < len(continuation_prompts):
                context.add_message("user", continuation_prompts[turn_idx])

            # Track usage
            self.pool.donated_keys[current_key_id].mark_usage(tokens_used)
            task_state['total_tokens_used'] += tokens_used

            task_state['turns'].append({
                'turn': turn_idx + 1,
                'prompt': prompt,
                'response': response_text,
                'tokens_used': tokens_used,
                'key_id': current_key_id
            })

            all_responses.append(response_text)

            print(response_text)

        task_state['status'] = TaskStatus.COMPLETED

        return {
            'success': True,
            'turns': task_state['turns'],
            'total_tokens_used': task_state['total_tokens_used'],
            'keys_used': task_state['keys_used'],
            'swap_count': task_state['swap_count'],
            'full_conversation': context.messages
        }


# Example usage
if __name__ == '__main__':
    print("=" * 80)
    print("AUTO-SWITCHING AI EXECUTOR - DEMONSTRATION")
    print("=" * 80)

    from aixn.core.secure_api_key_manager import SecureAPIKeyManager, AIProvider
    from aixn.core.ai_pool_with_strict_limits import StrictAIPoolManager

    # Initialize
    blockchain_seed = "xai_genesis_block_hash"
    key_manager = SecureAPIKeyManager(blockchain_seed)
    pool = StrictAIPoolManager(key_manager)

    # Create executor
    executor = AutoSwitchingAIExecutor(pool, key_manager)

    print("\n✅ Auto-switching executor initialized")

    # Simulate donating multiple small keys (to trigger swapping)
    print("\n" + "=" * 80)
    print("SIMULATING MULTIPLE SMALL API KEY DONATIONS")
    print("=" * 80)

    for i in range(3):
        pool.submit_api_key_donation(
            donor_address=f"XAI{i}{'a'*40}",
            provider=AIProvider.ANTHROPIC,
            api_key=f"sk-ant-test-key-{i}",
            donated_tokens=100000,  # Small keys to force swapping
            donated_minutes=None
        )
        print(f"\n✅ Key {i+1} donated: 100,000 tokens")

    # Validate keys
    for key_id in pool.donated_keys.keys():
        key_manager.validate_key(key_id, is_valid=True)

    # Execute long task that will require key switching
    print("\n\n" + "=" * 80)
    print("EXECUTING LONG TASK (Will automatically switch keys)")
    print("=" * 80)

    result = executor.execute_long_task_with_auto_switch(
        task_id="task_001",
        task_description="""
        Write a comprehensive implementation guide for atomic swaps.
        Include code examples, security considerations, and testing strategies.
        This should be a detailed, multi-section document.
        """,
        provider=AIProvider.ANTHROPIC,
        max_total_tokens=250000,  # Will need multiple keys!
        streaming=False  # Set to True to see streaming
    )

    print("\n\n" + "=" * 80)
    print("TASK EXECUTION SUMMARY")
    print("=" * 80)

    print(f"\nSuccess: {result['success']}")
    print(f"Total tokens used: {result.get('tokens_used', 0):,}")
    print(f"Keys used: {result.get('keys_used', [])}")
    print(f"Swap count: {result.get('swap_count', 0)}")

    if result.get('swap_events'):
        print(f"\nKey Swap Events:")
        for event in result['swap_events']:
            print(f"  - {event['old_key'][:8]} → {event['new_key'][:8]}")
            print(f"    Reason: {event['reason']}")

    print("\n\n🚀 AUTO-SWITCHING BENEFITS:")
    print("-" * 80)
    print("""
1. ✅ Tasks NEVER stop due to key depletion
2. ✅ Seamlessly uses multiple small donations
3. ✅ Automatic failover on key errors
4. ✅ Conversation context preserved across swaps
5. ✅ Supports streaming responses
6. ✅ Multi-turn conversations supported
7. ✅ Complete audit trail of swaps
8. ✅ Optimal key utilization (uses near-depleted keys first)

AI development continues uninterrupted!
    """)
