# Qwen tokenizer asset

Source: https://huggingface.co/Qwen/Qwen3.5-4B/resolve/main/tokenizer.json

Downloaded 2026-09-09. SHA-256: `5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42`.

Used only to count text tokens for Qwen3.5 context sizing, with 256 extra tokens reserved for Ollama chat framing. OCR text is never truncated to meet the budget. Other models fall back to a conservative UTF-8 byte bound. This is a tokenizer, not model weights. See LICENSE.txt for the upstream license.
