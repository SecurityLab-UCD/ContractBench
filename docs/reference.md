# Reference Notes for Validity/Integrity Research

## Real-system specs (ground truth)

- AWS S3 presigned URLs: https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-presigned-url.html
- AWS SigV4 signing/canonical request: https://docs.aws.amazon.com/IAM/latest/UserGuide/create-signed-request.html
- AWS temporary credentials and expiry: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_use-resources.html
- Amazon Bedrock quotas/limits: https://docs.aws.amazon.com/bedrock/latest/userguide/quotas.html

## Model weakness papers relevant to tasks

- Lost in the Middle (context-position sensitivity): https://arxiv.org/abs/2307.03172
- NeedleBench (retrieval under long context): https://arxiv.org/abs/2407.11963
- LongBench (multi-task long-context benchmark): https://arxiv.org/abs/2308.14508
- HELM (broad evaluation framework): https://arxiv.org/abs/2211.09110
- Temporal Blindness in Multi-Turn LLM Agents (EMNLP 2025): https://aclanthology.org/2025.emnlp-main.1005/
- Agentic misalignment risks in LLM agents (ICLR 2025 oral): https://openreview.net/forum?id=vw8jYr6H7q
- Practical agent failure/robustness patterns: https://www.anthropic.com/research/building-effective-agents

## Planning overhead and temporal reasoning in agents

- Plan-and-Act: Improving Planning of Agents for Long-Horizon Tasks (ICML 2025): https://arxiv.org/abs/2503.09572
  - Separates Planner and Executor; always-planning adds overhead that degrades long-horizon performance.
- Learning When to Plan: Efficiently Allocating Test-Time Compute (2025): https://arxiv.org/abs/2509.03581
  - Always planning is expensive; trains agents for dynamic planning allocation. Most direct evidence for "planning overhead" problem.
- When Do Tools and Planning Help LLMs Think? A Cost- and Latency-Aware Benchmark (Jan 2026): https://arxiv.org/abs/2601.02663
  - Measures marginal latency and cost per accuracy point. Precise empirical treatment of planning tradeoffs.
- Win Fast or Lose Slow: Balancing Speed and Accuracy (NeurIPS 2025): https://arxiv.org/abs/2505.19481
  - High-frequency trading and gaming benchmarks where latency directly causes failure. Up to 80% improvement by trading accuracy for speed.
- Between Underthinking and Overthinking (2025): https://arxiv.org/abs/2505.00127
  - Long-CoT models waste 19-42s on trivial queries. In deadline tasks, this overhead is fatal.
- Budget-Aware Tool-Use Enables Effective Agent Scaling (2024): https://arxiv.org/abs/2511.17006
  - Agents that reason about tool-call budgets improve success under constraints.

## Agent validity and constraint failure research

- SagaLLM: Context Management, Validation, and Transaction Guarantees (VLDB 2025): https://arxiv.org/abs/2503.11951
  - Strongest formal treatment of agent validity failures: contract conformance, dependency satisfaction, temporal ordering, transaction coherence.
- Why Do Multi-Agent LLM Systems Fail? (ICLR 2025 Workshop): https://arxiv.org/abs/2503.13657
  - 14 unique failure modes. "Mismatch between reasoning and action" = 13.2% of failures.
- AgentIF: Benchmarking Instruction Following in Agentic Scenarios (NeurIPS 2025): https://arxiv.org/abs/2505.16944
  - 50 apps, avg 11.9 constraints each. All models below 30% ISR. Conditional constraint failures = key weakness.
- ODCV-Bench: Outcome-Driven Constraint Violations (Dec 2025): https://arxiv.org/abs/2512.20798
  - Agents actively bypass constraints under goal pressure. 30-50% violation rate for SOTA models.

## Temporal benchmarks and async task execution

- Robotouille: An Asynchronous Planning Benchmark (ICLR 2025): https://arxiv.org/abs/2502.05227
  - Agents drop from 47% to 11% when tasks require async time management vs sequential. Closest to "temporal trap" benchmark.
- tau-bench: Tool-Agent-User Interaction (2024): https://arxiv.org/abs/2406.12045
  - Retail and airline domains. Even GPT-4o < 50%. "Do-nothing" agent passes 38% of airline tasks -- validity not properly enforced.
- TemporalBench: LLM Agents on Contextual and Event-Informed Time Series (Feb 2026): https://arxiv.org/abs/2602.13272
  - Four-tier taxonomy for temporal reasoning. Retail, healthcare, energy, physical systems.

## Eager vs lazy agent execution

- Unlocking the Power of Multi-Agent LLM: From Lazy Agents to Deliberation (2025): https://arxiv.org/abs/2511.02303
  - "Lazy agent" as failure mode. Laziness is a stable equilibrium. Dr. MAMR forces deliberation.

## Agent benchmark design references

- WebArena: https://arxiv.org/abs/2307.13854
- AgentBench: https://arxiv.org/abs/2308.03688
- TravelPlanner: https://arxiv.org/abs/2402.01622
- SWE-bench: https://arxiv.org/abs/2310.06770
- "Measuring What Matters": https://arxiv.org/abs/2511.04703
- "When +1% Is Not Enough": https://arxiv.org/abs/2511.19794
- BrowserGym: https://arxiv.org/abs/2412.05467
- Best AI Agent Evaluation Benchmarks Guide (2025): https://o-mega.ai/articles/the-best-ai-agent-evals-and-benchmarks-full-2025-guide

## Agent fix/adapter references

- LLM+P (external PDDL planner): https://arxiv.org/abs/2304.11477
- Reflexion: https://arxiv.org/abs/2303.11366
- Inner Monologue: https://arxiv.org/abs/2207.05608
- DEPS (goal selector): https://arxiv.org/abs/2302.01560

## Industry standards

- AGENTS.md (open standard for AI coding agents): https://agents.md/
  - OpenAI-created, donated to Linux Foundation AAIF (Dec 2025). Supported by Codex, Cursor, Gemini CLI, GitHub Copilot, Devin.
  - GitHub repo: https://github.com/agentsmd/agents.md
  - Linux Foundation AAIF announcement: https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation

## Why these references matter for ContractBench

- SigV4/presigned URLs motivate **byte-exact integrity constraints**.
- Temporary credentials and quotas motivate **time-validity constraints**.
- Lost-in-the-middle/long-context benchmarks motivate **context burial and recall stressors**.
- Planning overhead research motivates **new validity tasks where deliberation causes deadline failure**.
- Agent constraint failure research validates that WRONG_VALUE/EXPIRED are realistic failure modes, not artificial.
- Temporal benchmarks (Robotouille, tau-bench) confirm that async/deadline tasks are genuinely hard and underexplored.
