# AgentDojo experiment: advisory vs enforced query-derived tool policy

Question: does a tool-use policy that is derived from the trusted user request help against prompt
injection, and does it matter whether the policy is only *suggested* to the model (prompt hint) or
*enforced* at execution time?

The policy is a re-implementation, for AgentDojo's pipeline interface, of the `ToolUsePolicy` and
approval-gate ideas in `desktop-assistant-agent`. It is **not** the original runtime code.

## Arms

| arm | what it does |
|---|---|
| `baseline` | no defense |
| `tool_filter` | AgentDojo's built-in defense (removes tools the query does not need) |
| `advisory` | LLM picks likely tools from the user query only; result is added to the system prompt as a hint, nothing is blocked |
| `enforce` | same policy, but tool calls outside the chosen set are denied before execution |
| `enforce_writes` | same policy as `enforce`, but read-only tools (`get_`/`search_`/`list_`/`read_`) are never blocked; only state-changing tools must be in the allowed set (optional) |
| `both` | hint in the prompt and enforcement (optional) |

## Step 1: set up

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt            # pins agentdojo==0.1.35 (its API is still changing)
echo "OPENAI_API_KEY=sk-..." > .env        # never commit this file
```

## Step 2: run the offline checks (no API key, no cost)

```bash
python test_offline.py
```

Expected last line: `All offline checks passed.`

## Step 3: smoke test with one tiny real run

```bash
python run_experiment.py --arms baseline,enforce --n-user-tasks 2 --n-injection-tasks 1 \
    --logdir runs_smoke --out results_smoke.json
```

Open one JSON trace under `runs_smoke/` and read it. Check that (a) the model really calls tools,
(b) in the `enforce` arm denied calls show "denied by policy", (c) the numbers in the printed table
match what you see in the traces. Then look at your API usage page to see what this run cost.

## Step 4: run the experiment

```bash
python run_experiment.py --n-user-tasks 10 --n-injection-tasks 3
```

Defaults: `workspace` suite, `important_instructions` attack, `gpt-4o-mini-2024-07-18`, arms
`baseline,tool_filter,advisory,enforce`. User and injection tasks are spread evenly across the
suite instead of taking the first few.

The run is resumable: finished tasks are read from `runs/`, so re-running the same command
continues after an interruption and also re-prints the table. Use `--force-rerun` to start over.
To grow the sample, increase `--n-user-tasks` (for example 20) and run the same command again.

## Step 5: read the results

`results.json` holds the per-pair outcomes; the table shows, per arm:

- **utility (no attack)**: user-task success without any attack
- **utility (attack)**: user-task success while the attack is present
- **ASR**: attack success rate, lower is better. AgentDojo's own code calls this `security_results`
  and its CLI prints it as "Average security", but `True` means the attack *succeeded*.

Intervals are 95% Wilson intervals. With 10 user tasks x 3 injection tasks you have 30 attack
pairs per arm, so intervals are wide; treat differences as indications, not proof.

## Files

- `query_guard.py` - `QueryToolPolicy` and `GatedToolsExecutor` (the pipeline elements)
- `run_experiment.py` - builds the arms, runs AgentDojo, prints and saves the table
- `test_offline.py` - checks that need no API key
- `overlap_analysis.py` - static analysis: which attacks can a tool allowlist block in principle?
- `inspect_traces.py` - per-task view of tool calls, denied calls and policy decisions
- `RESULTS.md` - results, limitations and interpretation

## Diagnosing a run

```bash
python overlap_analysis.py                       # which attacks can a tool allowlist block in principle?
python inspect_traces.py --logdir runs_hard --arm enforce --verbose
```

`inspect_traces.py` shows, per user task, the tool calls the agent made and which were denied by the
policy gate. If `policy_decisions.jsonl` exists in the log directory (written by `QueryToolPolicy`),
it also shows the allowed tool set and which tools of the ideal solution were never allowed. That file
is only written for runs made after decision logging was added, so re-run the arm with a fresh
`--logdir` to get it.

Run the "hard" subset (user tasks whose own solution needs `send_email`, paired with attacks that also
need it):

```bash
python run_experiment.py \
  --user-tasks user_task_13,user_task_19,user_task_25,user_task_33 \
  --injection-tasks injection_task_0,injection_task_3,injection_task_4,injection_task_13 \
  --arms baseline,tool_filter,advisory,enforce --logdir runs_hard --out results_hard.json
```

Read utility and ASR together: an arm that cannot complete the user's task also cannot be attacked,
so ASR = 0 with utility = 0 is not a successful defense.

## Lessons from the hard subset (enforce arm)

- If the user's actions are specified inside untrusted content ("do the actions in this email"), a policy
  built from the request alone cannot know which write tools are needed; the strict gate then blocks
  legitimate calls and utility collapses. This is a limit of the idea, not a bug to patch away.
- Gating every tool is stricter than the original runtime, which treats read-only tools as low risk.
  `enforce_writes` is the closer match. Use `--show-args send_email` in `inspect_traces.py` to see what a
  run actually sent.