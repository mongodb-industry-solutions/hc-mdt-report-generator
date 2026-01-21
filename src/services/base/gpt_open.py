"""Minimal client for GPT-OSS server."""

import json
import re
import time
import requests
from typing import Optional
import os


def count_tokens(text: str, model_hint: Optional[str] = None) -> int:
    """Estimate token count.

    Preference order:
    1) Use tiktoken if available with the best-fit encoding for the model.
    2) Fallback heuristic based on character length (~4 chars/token), with slight padding.
    """
    # Try tiktoken first
    try:
        import tiktoken  # type: ignore

        encoding_name = "cl100k_base"
        if model_hint:
            model_lower = model_hint.lower()
            # Prefer o200k_base for GPT-4o/GPT-5 style models
            if ("gpt-5" in model_lower) or ("gpt-4o" in model_lower) or ("o1" in model_lower):
                encoding_name = "o200k_base"
            # Keep cl100k_base default for others
        enc = tiktoken.get_encoding(encoding_name)
        return len(enc.encode(text))
    except Exception:
        # Robust fallback: ~4 chars per token + small padding by word count
        if not text:
            return 0
        approx = max(1, int(len(text) / 4))
        # Light padding for word boundaries/punctuation
        try:
            words = re.findall(r"\w+", text, re.UNICODE)
            approx += max(0, int(len(words) * 0.05))
        except Exception:
            pass
        return approx


class GptOpenClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        timeout: float = 300.0,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.model = model
        self.api_key = api_key or self._get_api_key_from_env()
        self.session = requests.Session()
        
    def _get_api_key_from_env(self) -> Optional[str]:
        """Get API key from environment variable"""
        import os
        return os.environ.get("OPENAI_API_KEY", "")

    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs,
    ) -> str:
        # Check which model we're using to adapt payload format
        current_model = model or self.model or ""
        is_gpt5_model = "gpt-5" in current_model.lower() if current_model else False
        is_gpt_oss_20b = "gpt-oss-20b" in current_model.lower() if current_model else False
        
        # Create messages array with appropriate role types
        messages = []
        if system:
            # For GPT-5 models, use "developer" role for system messages
            if is_gpt5_model:
                messages.append({"role": "developer", "content": system})
            else:
                messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        
        # Create model-specific payload with appropriate temperature
        if is_gpt5_model:
            # GPT-5 models only support the default temperature (1)
            payload = {"messages": messages}  # Don't set temperature, use default
        else:
            # Other models can use custom temperature
            payload = {"messages": messages, "temperature": 0.1}
        
        # Add model to payload if specified
        if current_model:
            payload["model"] = current_model
            
        # Add streaming parameter for GPT-5 models (they work better with streaming)
        if is_gpt5_model:
            # Default to streaming for GPT-5 models unless explicitly set to False
            if kwargs.get("stream") is not False:
                payload["stream"] = True
            
        # Handle token parameters based on model
        if is_gpt5_model:
            # For GPT-5 models:
            # 1. Remove max_tokens from kwargs if present
            if "max_tokens" in kwargs:
                kwargs.pop("max_tokens")
                
            # 2. Set max_completion_tokens if not already in kwargs
            payload["max_completion_tokens"] = 10000
            if "max_completion_tokens" not in kwargs:
                payload["max_completion_tokens"] = 10000
        elif is_gpt_oss_20b:
            # Heuristic token estimation for gpt-oss-20b
            combined_input = f"{system}\n\n{prompt}" if system else prompt
            tokens_in = count_tokens(combined_input, model_hint=current_model)
            # Share 50% budget between completion and reasoning (25% each)
            tokens_out = max(1, int(tokens_in * 0.25))
            reasoning_tokens = max(1, int(tokens_in * 0.25))

            # Trace log with all calculations in one line
            import logging
            _logger = logging.getLogger(__name__)
            _trace = (
                f"gpt-oss-20b heuristic | tokens_in={tokens_in}, max_tokens={tokens_out}, "
                f"max_reasoning_tokens={reasoning_tokens} (25%+25% of input)"
            )
            _logger.info(_trace)
            print(_trace)

            # Prefer heuristic defaults unless caller explicitly overrides with non-legacy values
            if "max_tokens" in kwargs:
                if kwargs.get("max_tokens") == 10000:
                    kwargs["max_tokens"] = tokens_out
                    _logger.info(f"Overriding legacy max_tokens=10000 with heuristic {tokens_out}")
                    print(f"Overriding legacy max_tokens=10000 with heuristic {tokens_out}")
            else:
                payload["max_tokens"] = tokens_out

            if "max_reasoning_tokens" in kwargs:
                # Respect caller-provided value
                pass
            else:
                payload["max_reasoning_tokens"] = reasoning_tokens
        else:
            # For other models, use max_tokens
            payload["max_completion_tokens"] = 10000
            if "max_tokens" not in kwargs:
                payload["max_tokens"] = 10000
            
        # Add any remaining kwargs to payload
        if kwargs:
            payload.update(kwargs)

        # Enforce reasoning_effort for gpt-oss-20b when present
        try:
            current_model_lower = (payload.get("model") or self.model or "").lower()
            if "gpt-oss-20b" in current_model_lower:
                # Default to 'low' if not explicitly provided
                payload["reasoning_effort"] = (payload.get("reasoning_effort") or "low")
        except Exception:
            # Non-fatal safeguard
            pass
            
        # SAFETY CHECKS for GPT-5 models:
        if is_gpt5_model:
            # 1. Ensure max_tokens is removed for GPT-5 models
            if "max_tokens" in payload:
                del payload["max_tokens"]
            
            # 2. Ensure temperature is removed for GPT-5 models (only default value 1 is supported)
            if "temperature" in payload:
                del payload["temperature"]

        # Setup headers
        headers = {}
        
        # Only add Authorization header if we have an API key
        # This is needed for OpenAI API but not for local GPT-OSS servers
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        # Check if we should route to Ollama
        # Priority: LLM_PROVIDER env var, then fallback to ":" in model name check
        try:
            current_model_lower = (payload.get("model") or self.model or "").lower()
        except Exception:
            current_model_lower = ""

        llm_provider = os.environ.get("LLM_PROVIDER", "").lower()
        is_ollama = (
            llm_provider == "ollama" or 
            ":" in current_model_lower  # Backward compatibility
        )

        if is_ollama:
            # Build Ollama-specific options from environment variables
            ollama_options = {}
            
            # OLLAMA_NUM_THREAD: CPU threads for inference (default: auto-detected by Ollama)
            num_thread = os.environ.get("OLLAMA_NUM_THREAD")
            if num_thread:
                try:
                    ollama_options["num_thread"] = int(num_thread)
                except ValueError:
                    pass
            
            # OLLAMA_NUM_GPU: GPU layers to offload (99 = all layers to GPU)
            num_gpu = os.environ.get("OLLAMA_NUM_GPU")
            if num_gpu:
                try:
                    ollama_options["num_gpu"] = int(num_gpu)
                except ValueError:
                    pass
            
            # Prepare Ollama payload
            ollama_payload = {
                "model": payload.get("model") or self.model,
                "prompt": messages[-1]["content"],
                "stream": payload.get("stream", False),
            }
            
            # Only add options if we have any configured
            if ollama_options:
                ollama_payload["options"] = ollama_options
            
            # Include system if present
            system_msg = next((m for m in messages if m.get("role") in ("system", "developer")), None)
            if system_msg:
                ollama_payload["system"] = system_msg.get("content")

            # Merge common optional params
            for k in ("temperature", "max_tokens"):
                if k in payload:
                    ollama_payload[k] = payload[k]

            import logging as _logging
            _logger = _logging.getLogger(__name__)
            options_str = f" | options={ollama_options}" if ollama_options else ""
            _logger.info(f"🔄 Routing to Ollama /api/generate | model={ollama_payload['model']}{options_str}")

            r = self.session.post(
                f"{self.base_url}/api/generate",
                json=ollama_payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
                stream=ollama_payload.get("stream", False),
            )
            r.raise_for_status()

            if ollama_payload.get("stream", False):
                # Collect streamed chunks
                chunks = []
                for line in r.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        chunks.append(data.get("response") or "")
                        if data.get("done"):
                            break
                    except Exception:
                        chunks.append(line)
                return "".join(chunks).strip()
            else:
                try:
                    data = r.json()
                    text = data.get("response")
                    if isinstance(text, str):
                        return text.strip()
                except ValueError:
                    pass
                return r.text.strip()

        # Log info about API call (without revealing full API key)
        import logging
        logger = logging.getLogger(__name__)
        api_key_status = "[SET]" if self.api_key else "[NONE]"
        
        # Log detailed payload info for debugging
        model_info = f"Model: {payload.get('model', 'Not specified')}"
        token_params = []
        if "max_tokens" in payload:
            token_params.append(f"max_tokens={payload['max_tokens']}")
        if "max_completion_tokens" in payload:
            token_params.append(f"max_completion_tokens={payload['max_completion_tokens']}")
        if "max_reasoning_tokens" in payload:
            token_params.append(f"max_reasoning_tokens={payload['max_reasoning_tokens']}")
        token_info = ", ".join(token_params) if token_params else "No token limits"
        stream_info = "streaming=True" if payload.get("stream") else "streaming=False"
        
        logger.info(f"🔄 Calling {self.base_url}/v1/chat/completions | {model_info} | {token_info} | {stream_info} | API key: {api_key_status}")
            
        try:
            # Check if we're using streaming mode
            is_streaming = payload.get("stream", False)

            # Retry settings
            max_retries = int(os.environ.get("GPT_OPEN_MAX_RETRIES", "3")) if 'os' in globals() else 3
            base_delay = float(os.environ.get("GPT_OPEN_RETRY_DELAY", "1.0")) if 'os' in globals() else 1.0

            last_exception = None
            for attempt in range(1, max_retries + 1):
                try:
                    # Send request
                    r = self.session.post(
                        f"{self.base_url}/v1/chat/completions",
                        json=payload,
                        headers=headers,
                        timeout=self.timeout,
                        stream=is_streaming
                    )
                    r.raise_for_status()

                    if is_streaming:
                        # Process streaming response
                        return self._process_streaming_response(r)
                    else:
                        # Process normal response with token-limit check
                        return self._process_standard_response(r, payload)
                except requests.exceptions.HTTPError as e:
                    last_exception = e
                    logger.error(f"❌ Attempt {attempt}/{max_retries} failed with status {getattr(r, 'status_code', 'N/A')}: {getattr(r, 'text', '')}")
                    if attempt < max_retries:
                        sleep_for = base_delay * (2 ** (attempt - 1))
                        logger.info(f"⏳ Retrying in {sleep_for:.1f}s...")
                        time.sleep(sleep_for)
                    else:
                        raise
        except requests.exceptions.HTTPError as e:
            # Log the actual error response for debugging
            logger.error(f"❌ API call failed with status {r.status_code}: {r.text}")
            # Add model and API key info to error (without revealing the key itself)
            logger.error(f"❌ Model: {model or self.model}, API Key Present: {'Yes' if self.api_key else 'No'}")
            raise
        
    def _process_standard_response(self, response, request_payload=None):
        """Process a standard (non-streaming) API response
        Also checks if token usage reached configured limits and logs it.
        """
        data = response.json()
        content = data["choices"][0]["message"]["content"]

        # Inspect usage if present
        try:
            usage = data.get("usage") or {}
            # OpenAI style fields: prompt_tokens, completion_tokens, total_tokens
            total_tokens = usage.get("total_tokens")
            completion_tokens = usage.get("completion_tokens")
            prompt_tokens = usage.get("prompt_tokens")

            # Compare against configured limits when available
            configured_max_tokens = None
            configured_max_reasoning = None

            if isinstance(request_payload, dict):
                configured_max_tokens = request_payload.get("max_tokens") or request_payload.get("max_completion_tokens")
                configured_max_reasoning = request_payload.get("max_reasoning_tokens")

            # Detect hits: max_tokens caps completion tokens; do not compare total_tokens to max_tokens
            hit_output_limit = (
                configured_max_tokens is not None
                and completion_tokens is not None
                and completion_tokens >= configured_max_tokens
            )
            hit_reasoning_limit = (
                configured_max_reasoning is not None
                and usage.get("reasoning_tokens") is not None
                and usage.get("reasoning_tokens") >= configured_max_reasoning
            )

            if hit_output_limit or hit_reasoning_limit:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    "⚠️ Token limit reached | "
                    f"completion_tokens={completion_tokens}/{configured_max_tokens} "
                    f"reasoning_tokens={usage.get('reasoning_tokens')}/{configured_max_reasoning} "
                    f"prompt_tokens={prompt_tokens} total_tokens={total_tokens}"
                )
                print(
                    "⚠️ Token limit reached:",
                    {
                        "completion_tokens": completion_tokens,
                        "max_tokens": configured_max_tokens,
                        "reasoning_tokens": usage.get("reasoning_tokens"),
                        "max_reasoning_tokens": configured_max_reasoning,
                        "prompt_tokens": prompt_tokens,
                        "total_tokens": total_tokens,
                    },
                )
        except Exception:
            # Swallow any telemetry/diagnostic errors
            pass

        return content.split("final", 1)[1].strip() if "final" in content else content
        
    def _process_streaming_response(self, response):
        """Process a streaming API response and return the full content"""
        import logging
        logger = logging.getLogger(__name__)
        
        # Store all raw lines for debugging if needed
        raw_lines = []
        full_content = ""
        
        logger.info("📥 Starting to process streaming response...")
        
        # Parse SSE format in the response
        try:
            for i, line in enumerate(response.iter_lines()):
                # Store raw line for debugging (up to 100 lines)
                if i < 100:  # Limit to avoid memory issues
                    raw_lines.append(line)
                
                if not line:
                    continue
                
                # Remove "data: " prefix
                if line.startswith(b"data: "):
                    line = line[6:]  # Remove "data: " prefix
                
                # Skip [DONE] line
                if line.strip() == b"[DONE]":
                    continue
                
                try:
                    # Parse JSON from the line
                    json_line = json.loads(line)
                    
                    # Extract content based on OpenAI's streaming format
                    if "choices" in json_line and len(json_line["choices"]) > 0:
                        choice = json_line["choices"][0]
                        if "delta" in choice and "content" in choice["delta"]:
                            content_piece = choice["delta"]["content"]
                            full_content += content_piece
                        # Handle alternative response formats
                        elif "message" in choice and "content" in choice["message"]:
                            content_piece = choice["message"]["content"]
                            full_content += content_piece
                        elif "text" in choice:
                            content_piece = choice["text"]
                            full_content += content_piece
                except Exception as e:
                    logger.warning(f"⚠️ Error parsing line {i}: {e}")
                    logger.warning(f"⚠️ Line content: {line}")
        except Exception as e:
            logger.error(f"❌ Error in streaming response processing: {e}")
            
        # Debug info about the response
        logger.info(f"📊 Streaming completed: collected {len(full_content)} characters")
        
        # If content is empty, dump the raw lines for debugging
        if not full_content:
            logger.error("❌ EMPTY RESPONSE DETECTED - Dumping raw response data:")
            logger.error(f"❌ Raw response lines count: {len(raw_lines)}")
            
            # Print some of the raw lines to help debug
            for i, line in enumerate(raw_lines):
                if i < 10:  # Print first 10 lines
                    logger.error(f"❌ Raw line {i}: {line}")
            
            # Try to combine the raw lines to see if there's any pattern
            try:
                raw_text = b"\n".join(raw_lines).decode('utf-8', errors='replace')
                logger.error(f"❌ Combined raw content: {raw_text[:1000]}...")
            except Exception as e:
                logger.error(f"❌ Error combining raw content: {e}")
            
            # Return a placeholder to avoid empty string
            return "No content could be parsed from streaming response"
                
        # Same post-processing as regular responses
        return full_content.split("final", 1)[1].strip() if "final" in full_content else full_content

    def health(self) -> bool:
        try:
            return self.session.get(f"{self.base_url}/health", timeout=5).ok
        except:
            return False