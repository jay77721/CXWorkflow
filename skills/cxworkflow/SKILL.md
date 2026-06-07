---
name: cxworkflow
description: Create, explain, or operate a multi-session Codex development team with Commander, Secretary, Developer, Tester, Reporter, and Observer roles. Use when the user asks for CXWorkflow, multi-session Codex teams, AI development teams, or one-click session setup prompts.
---

# CXWorkflow

CXWorkflow organizes Codex into a small development team made of specialized sessions. Use it when a project needs persistent planning, implementation, testing, reporting, and coordination across multiple Codex threads.

## Core Principle

CXWorkflow prioritizes deterministic coordination over maximum parallelism. Agents communicate through events, Secretary acts as the single source of truth, and Commander schedules work using a rate-limit-aware sequential handoff strategy.

## Event-Driven Operating Model

Prefer event-driven coordination over continuous polling:

- `TaskCreated`: Commander creates a task; Developer executes.
- `TaskFinished`: Developer finishes; Commander schedules Tester.
- `TestFailed`: Tester reports failure; Commander assigns Developer a fix.
- `Blocked`: any session reports a blocker; Commander decides and Secretary records.
- `MilestoneReached`: Commander or Secretary emits; Reporter summarizes.
- `RateLimitWarning`: any session reports pressure; Commander lowers concurrency and obs enters Watchdog mode.

Roles should not freely ping each other. Important state goes to Secretary first, then Commander schedules the next action.

## Single Source Of Truth

Secretary is the workflow database. All important events, task states, blockers, test results, decisions, and recovery actions should be written to Secretary. Any role that needs context should read Secretary first instead of asking other sessions directly.

## Load Levels

- Level 0: Commander only. Use for clarification, lightweight planning, or simple questions.
- Level 1: Commander + Developer. Default mode for small implementation or fixes.
- Level 2: Commander + Developer + Tester. Use when validation, regression checks, or review are needed.
- Level 3: Commander + Secretary + Developer + Tester + Reporter + obs. Use for long-running projects, multi-module work, or complex collaboration.

Start at Level 1 by default and increase only when complexity, risk, or duration justifies it.

## Rate Limit Safety And Circuit Breaker

Use minimum necessary concurrency to avoid API 429s:

- Commander is the only scheduling entry point.
- Developer and Tester use sequential handoff.
- Secretary, Reporter, and obs join only at stage boundaries, blockers, or abnormal events.
- Reporter reads Secretary first and avoids frequent polling.
- obs is a Watchdog: it sleeps during normal operation and wakes only on abnormal events.

Circuit breaker:

- 1 consecutive `429`: Commander lowers the load level and pauses non-essential sessions.
- 3 consecutive `429`s: stop non-critical roles such as Reporter and obs; keep only Commander and essential execution.
- 5 consecutive `429`s: Secretary saves state, Commander pauses the workflow, and the team waits for cooldown.

Recovery starts from Secretary's last known state, then Commander resumes from a lower load level.

## Core Roles

- `指挥` / Commander: owns project direction, task breakdown, priorities, coordination, and acceptance criteria.
- `秘书` / Secretary: owns project memory, decisions, task state, blockers, and cross-thread synchronization.
- `开发` / Developer: owns implementation, bug fixes, refactors, and verification.
- `测试` / Tester: owns QA, code review, test execution, regression risk, and quality reporting.
- `汇报` / Reporter: owns progress reports, team status snapshots, and next-step summaries.
- `obs` / Observer: owns thread health checks, role-drift detection, blocker detection, coordination-gap detection, and recovery suggestions that bring the team back on track.

## When To Use

Use CXWorkflow when:

- The user wants a Codex development team.
- The project is long-running or context-heavy.
- The task spans multiple modules, roles, or phases.
- The user asks to create sessions such as `指挥`, `秘书`, `开发`, `测试`, `汇报`, or `obs`.
- The user asks for a GitHub/README explanation of this workflow.

For small single-file fixes, a normal single Codex session is usually enough.

## One-Click Session Setup Prompt

When the user asks for a prompt to create the team, provide this:

```text
请基于当前项目一键创建 Codex 多线程开发团队，所有线程都使用当前仓库作为工作目录。

请创建并命名以下 session：

1. 指挥
职责：你是项目总指挥。读取整个项目和现有上下文，理解目标，拆分任务，制定开发路线，并向其他线程分配工作。你不直接做大量实现，优先负责决策、规划、协调和验收标准。

2. 秘书
职责：你是秘书长。负责记录项目决策、任务状态、各线程进展、待办事项和阻塞点。你需要定期整理项目状态，保证多线程协作不会丢上下文。

3. 开发
职责：你是主开发手。根据指挥线程的任务进行代码实现、bug 修复、重构和功能落地。每次修改前先理解代码结构，修改后运行必要验证，并把结果汇报给秘书和指挥。

4. 测试
职责：你是测试手和代码审查员。负责审查代码质量、运行测试、发现 bug、覆盖率缺口、架构风险和回归风险。请把问题按严重程度汇报给秘书和指挥。

5. 汇报
职责：你是汇报手。负责定期询问或读取其他线程的状态，生成项目进度报告，包括已完成、进行中、阻塞、风险、下一步建议。

6. obs
职责：你是运行观察员。你要持续检查所有线程是否正常运行，包括指挥是否在统筹、秘书是否在记录、开发是否在实现、测试是否在验证、汇报是否在同步状态。发现线程掉线、职责漂移、信息不同步、阻塞无人处理、任务偏离目标或协作流程失效时，你要指出问题，提醒对应线程恢复职责，并向指挥和秘书给出纠偏建议，帮助团队回到正常轨道。

创建完成后，请把每个 session 的 threadId、标题和职责列出来，并尽量 pin 这些线程。
```

Short version:

```text
请基于当前项目一键创建 Codex 多线程开发团队：指挥、秘书、开发、测试、汇报、obs。每个线程都在当前仓库工作，并分别承担项目总控、状态协调、代码实现、质量审查、进度汇总、线程运行检查和纠偏恢复职责。创建后列出 threadId 和用途，并 pin 这些线程。
```

## Operating Rules

When helping operate a CXWorkflow team:

1. Keep role boundaries clear.
2. Route implementation to Developer.
3. Route project memory and status tracking to Secretary.
4. Route validation and review to Tester.
5. Route summary requests to Reporter.
6. Route thread health checks, role-drift detection, and recovery suggestions to Observer.
7. Let Commander coordinate priorities and final decisions.

If thread-management tools are available and the user explicitly asks to create sessions, create the sessions directly. Otherwise provide the setup prompt.
