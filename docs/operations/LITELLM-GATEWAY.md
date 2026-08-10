# LiteLLM gateway for Fossil agents

Fossil can use the shared LiteLLM gateway for routine, non-sensitive model work.

- URL: `https://litellm-production-8656.up.railway.app/v1`
- Default execution model: `qwen3-coder-next`
- GitHub Actions secret: `LITELLM_PROXY_KEY`
- GitHub Actions variables: `LITELLM_URL`, `LITELLM_MODEL`
- Embeddings: `POST /v1/embeddings`, model `gemini-embedding-2`
- Reranking: `POST /v1/rerank`, model `rerank-v4-pro`

The gateway emits `X-LiteLLM-Data-Privacy-Warning` and bridged Responses include `metadata.data_privacy_warning`. This is an advisory warning, not a block. CKFF is not verified as zero-data-retention; agents must not send secrets, personal data, or confidential documents.

Chat requests may fall back to another configured provider/model. Check the returned requested model, actual model, and attempt diagnostics before recording benchmark results. Do not treat a fallback response as evidence that the requested model itself succeeded.

The embedding and reranking lanes are independent of chat fallback routing. Probe them before a retrieval run and fail loudly on non-2xx, empty vectors, or empty rankings. OpenCode Zen free models are not enabled here until their provider access passes a live probe; their documented privacy exceptions require the same non-sensitive-data rule.
