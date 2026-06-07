# CXWorkflow

[中文 README](./README.md)

CXWorkflow is a multi-session Codex development workflow. It turns one AI coding assistant into a small, persistent development team by giving each Codex thread a clear role, memory boundary, and collaboration responsibility.

This repository is also a Codex plugin. The plugin manifest lives in `.codex-plugin/plugin.json`, and the reusable workflow skill lives in `skills/cxworkflow/SKILL.md`.

## Codex Plugin

This project includes a Codex plugin configuration, so it can be installed and used as a Codex plugin.

- Plugin manifest: `.codex-plugin/plugin.json`
- Plugin name: `cxworkflow`
- Display name: `CXWorkflow`
- Category: `Productivity`
- Skills directory: `skills/`
- Workflow skill: `skills/cxworkflow/SKILL.md`

After installation, Codex can discover the CXWorkflow skill and use it when a user wants to create, explain, or operate a multi-session development team. The plugin default prompt is:

```text
Help me set up a CXWorkflow Codex development team for this project.
```

## Installation And Usage

### Use As A Codex Plugin

1. Clone this repository locally.

2. Add this local plugin in the Codex plugin management UI. The plugin root is the repository root:

```text
<your-local-path>/CXWorkflow
```

3. After installation, open a new Codex thread so the new plugin skill is loaded.

4. In the new thread, trigger CXWorkflow with a request such as:

```text
Help me set up a CXWorkflow Codex development team for this project.
```

or:

```text
Create a CXWorkflow multi-session development team for the current project.
```

### Manual Use

If you do not want to install the plugin yet, copy the one-click setup prompt below into Codex directly. The plugin mainly packages this workflow as a reusable skill so Codex can discover and apply it automatically in relevant situations.

## What It Solves

A single Codex session is convenient for quick edits and questions, but larger projects often overload one thread with planning, implementation, testing, decision memory, and progress reporting.

CXWorkflow separates those responsibilities:

- Commander owns direction and task breakdown.
- Secretary owns project memory and status synchronization.
- Developer owns implementation.
- Tester owns quality review and risk discovery.
- Reporter owns progress visibility.
- obs owns thread health monitoring and helps the team recover when collaboration drifts off track.

This structure is designed for long-running projects, multi-module features, complex refactors, AI-assisted product development, and any repo where a single chat thread becomes too crowded to manage safely.

## Core Principle

CXWorkflow prioritizes deterministic coordination over maximum parallelism. Agents communicate through events, Secretary acts as the single source of truth, and Commander schedules work using a rate-limit-aware sequential handoff strategy.

## Event-Driven Model

CXWorkflow is event-driven by default. Sessions should respond to relevant events instead of running continuously:

| Event | Emitted By | Responds |
| --- | --- | --- |
| `TaskCreated` | Commander | Developer reads the task and executes |
| `TaskFinished` | Developer | Commander schedules Tester |
| `TestFailed` | Tester | Commander assigns Developer a fix |
| `Blocked` | Any session | Commander decides, Secretary records |
| `MilestoneReached` | Commander or Secretary | Reporter generates a report |
| `RateLimitWarning` | Any session | Commander lowers concurrency, obs enters Watchdog mode |

This keeps roles decoupled: Developer does not directly drive Tester, Reporter does not poll every session, and important state goes through Secretary before Commander schedules the next step.

## Single Source Of Truth

Secretary is the single source of truth for CXWorkflow. All important events, task states, blockers, test results, decisions, and recovery actions should be written to Secretary.

When any role needs context, it should read Secretary first instead of asking other sessions directly. This prevents Developer, Tester, and Reporter from maintaining conflicting local versions of project state.

## Load Levels

CXWorkflow uses load levels to control cost and API pressure:

| Level | Active Roles | Use Case |
| --- | --- | --- |
| Level 0 | Commander | Clarification, lightweight planning, simple questions |
| Level 1 | Commander + Developer | Default mode for small implementation or fixes |
| Level 2 | Commander + Developer + Tester | Validation, regression checks, or code review |
| Level 3 | Commander + Secretary + Developer + Tester + Reporter + obs | Long-running projects, multi-module features, complex collaboration |

Start at Level 1 by default. Increase the load level only when task complexity, risk, or duration justifies it.

## Rate Limit Safety

To avoid API 429s, CXWorkflow defaults to minimum necessary concurrency instead of running all sessions at once.

- Commander is the only scheduling entry point.
- Developer and Tester use sequential handoff.
- Secretary, Reporter, and obs join only at stage boundaries, blockers, or abnormal events.
- Reporter avoids frequent polling and reads Secretary first.
- obs acts as a Watchdog: it sleeps during normal operation and wakes only on abnormal events.

## Circuit Breaker

When rate limits or request pressure appear, CXWorkflow uses a circuit breaker:

| Condition | Action |
| --- | --- |
| 1 consecutive `429` | Commander lowers the load level and pauses non-essential sessions |
| 3 consecutive `429`s | Stop non-critical roles such as Reporter and obs; keep only Commander and essential execution |
| 5 consecutive `429`s | Secretary saves state, Commander pauses the workflow, and the team waits for cooldown |

Recovery flow:

1. Secretary reads the last known state.
2. Commander confirms the current task, blockers, and next step.
3. Resume from a lower load level instead of returning directly to all-role concurrency.

## Team Roles

| Session | Role | Responsibility |
| --- | --- | --- |
| `Commander` / `指挥` | Project lead | Understands the whole project, breaks down work, assigns tasks, defines priorities, and makes final direction calls. |
| `Secretary` / `秘书` | PMO and project memory | Records decisions, tracks task status, keeps cross-thread context synchronized, and prevents project memory loss. |
| `Developer` / `开发` | Main engineer | Implements features, fixes bugs, refactors code, verifies changes, and reports results back to Commander and Secretary. |
| `Tester` / `测试` | QA and reviewer | Reviews code quality, runs tests, finds bugs, checks regression risk, and reports issues by severity. |
| `Reporter` / `汇报` | Progress reporter | Collects project status from other sessions and produces concise progress reports. |
| `Observer` / `obs` | Operations observer | Checks whether all sessions are running normally, detects dropped threads, blockers, role drift, or coordination gaps, and helps bring the team back on track. |

## How It Works

1. Start `Commander` first.
   Commander reads the project, understands the goal, and decomposes the work.

2. Start `Secretary`.
   Secretary records the plan, decisions, task ownership, blockers, and important context.

3. Start `Developer`.
   Developer follows Commander instructions and implements concrete code changes.

4. Start `Tester`.
   Tester reviews the implementation, runs validation, and reports risks or defects.

5. Start `Reporter`.
   Reporter summarizes what each thread is doing and gives the human owner a quick project snapshot.

6. Start `Observer`.
   Observer checks whether each session is fulfilling its role, flags abnormal collaboration patterns, and reports recovery suggestions to Commander and Secretary.

## Recommended One-Click Setup Prompt

Use this prompt in Codex to create the full team in one step:

```text
Please create a Codex multi-session development team for the current project. Every session should use the current repository as its working directory.

Create and name the following sessions:

1. Commander
Responsibility: You are the project lead. Read the whole project and existing context, understand the goal, break down tasks, define the development route, and assign work to the other sessions. Do not do large implementation work directly. Prioritize decisions, planning, coordination, and acceptance criteria.

2. Secretary
Responsibility: You are the project secretary. Record project decisions, task status, thread progress, todos, and blockers. Regularly organize project status so multi-session collaboration does not lose context.

3. Developer
Responsibility: You are the main developer. Implement code changes, bug fixes, refactors, and features based on Commander instructions. Before each change, understand the code structure. After each change, run necessary validation and report results to Secretary and Commander.

4. Tester
Responsibility: You are the tester and code reviewer. Review code quality, run tests, find bugs, coverage gaps, architectural risks, and regression risks. Report issues to Secretary and Commander by severity.

5. Reporter
Responsibility: You are the progress reporter. Periodically ask for or read status from other sessions and produce progress reports covering completed work, in-progress work, blockers, risks, and recommended next steps.

6. obs
Responsibility: You are the operations observer. Continuously check whether all sessions are running normally: Commander is coordinating, Secretary is recording, Developer is implementing, Tester is validating, and Reporter is synchronizing status. When a session drops off, drifts from its role, misses important context, leaves blockers unhandled, moves away from the project goal, or breaks the collaboration flow, identify the issue, prompt the relevant session to resume its responsibility, and give Commander and Secretary concrete recovery suggestions so the team returns to a normal operating track.

After creation, list each session's threadId, title, and responsibility, and pin these sessions if possible.
```

Short version:

```text
Please create a Codex multi-session development team for the current project: Commander, Secretary, Developer, Tester, Reporter, and obs. Each session should work in the current repository and separately own project direction, status coordination, implementation, quality review, progress reporting, thread health checks, and recovery when collaboration drifts off track. After creation, list the threadId and purpose for each session, and pin them.
```

## Suggested Reporting Format

Reporter can use this format when summarizing the team:

```md
# Project Status

## Completed
- ...

## In Progress
- ...

## Blocked
- ...

## Risks
- ...

## Next Steps
- ...
```

## When To Use This Workflow

Use CXWorkflow when:

- The project will last more than one session.
- The work touches multiple modules or files.
- You need continuous planning, coding, testing, and reporting.
- You want Codex to behave more like a development team than a single assistant.
- You are experimenting with AI-native software team structures.

For small one-file fixes or simple questions, a single Codex session is usually enough.
