# Contributing to ContractBench

Thanks for your interest in improving ContractBench. The current paper suite
contains 33 API-centered observation-contract tasks. Community extensions are
proposals until they have been reviewed, implemented, and released separately;
see [Community Task Packs](docs/community-task-packs.md).

## Ways to contribute

- **Propose a task:** [Open a task proposal](https://github.com/SecurityLab-UCD/ContractBench/issues/new?template=task-proposal.yml)
  before building a new scenario. A useful proposal can be reviewed without a
  model API key or a completed implementation.
- **Improve an adapter or reproducibility:** Open a pull request with the
  affected task, adapter version, run command, and expected behavior.
- **Report a bug or result discrepancy:** Use the
  [bug report form](https://github.com/SecurityLab-UCD/ContractBench/issues/new?template=bug-report.yml) and include the task
  version, model or oracle, and a redacted trace when available.
- **Improve documentation:** Fix an unclear instruction, add a grounded
  example, or update an installation path. Small pull requests are welcome.

Anyone can contribute through a fork and pull request; repository write access
is not required.

## Setup

ContractBench requires **Python 3.10+**. Always use [`uv`](https://github.com/astral-sh/uv)
for dependency management.

```bash
uv sync --extra all
```

You need API keys only when running tasks against a live model. For a no-key
starting point, run the reference oracle through Harbor:

```bash
uv tool install harbor
harbor run -p harbor/cookbook-export/scheduled-maintenance -a oracle -k 1 -n 1
```

See [QUICKSTART.md](QUICKSTART.md) for setup details. To use a live model, copy
`.env.example` to `.env` and add your own provider keys.

## Run one task

```bash
uv run python experiments/scripts/run_task_docker.py \
  --agent <alias> \
  --tasks <task-name> \
  --k 1 \
  --timeout 600
```

`<alias>` is a model alias from `agents/config.py` (e.g. `gpt-5`); `<task-name>`
is a directory under `harbor/tasks/`.

## Run the suite

Omit `--tasks` to run all tasks for a model. See
`experiments/scripts/run_task_docker.py` for the full set of flags.

```bash
uv run python experiments/scripts/run_task_docker.py --agent <alias> --k 3 --timeout 600
```

## Propose a task before implementation

Use the [task proposal form](https://github.com/SecurityLab-UCD/ContractBench/issues/new?template=task-proposal.yml) to give
reviewers a concrete contract to assess. Include:

1. A primary specification or documented failure case, plus any licensing or
   data-use constraints.
2. The observable artifact or state, its producer, and the later action that
   consumes it.
3. The precise validity and integrity invariants. Specify what the agent can
   observe, how time advances, and which bytes must be preserved.
4. A compliant trace, a violating trace, and the expected deterministic verdict.
5. A proposed verifier and passing oracle, and the difference from existing
   tasks in the [task catalog](harbor/TASK_CATALOG.md).

Proposals involving new scoring dimensions belong in a separate experimental
track until their definitions and metrics are validated. An accepted proposal
does not automatically become part of the frozen 33-task paper suite.

## Implement an approved task

See the onboarding material under `docs/` (`docs/onboarding.md`) for a deep
dive. Task definitions live under `harbor/tasks/<name>/` and consist of:

- `environment/server.py` — FastAPI server implementing the contract
- `instruction.md` — what the agent sees
- `solution/solve.sh` — reference solution (must still pass)
- `task.toml` — metadata (difficulty, category)
- `tests/test_outputs.py` — verifier that computes the reward

Keep these files in sync: changes to the server contract must be reflected in
the instruction, solution, and verifier. The verifier should distinguish a
legitimate completion from a shortcut, and the reference solution should pass
without relying on external production services or credentials. Describe any
new failure labels and preserve enough artifacts to reproduce the verdict.

## Pull request checklist

- Link the proposal or bug report and identify the task and adapter versions.
- Explain the observable contract and how the verifier checks it.
- Include a passing oracle run and at least one intentional failure for a new
  task. Include the command and relevant redacted output in the pull request.
- Document changes to task definitions or scoring that could affect published
  results. Keep community-pack scores separate from paper-suite scores.
- Confirm that submitted files contain no live credentials or private traces.

## Pre-commit validation

For code changes, run the relevant checks before opening a pull request:

```bash
uv run python -m pytest -q tests/unit/
```
