# CXWorkflow

CXWorkflow is a multi-session Codex development workflow. It turns one AI coding assistant into a small, persistent development team by giving each Codex thread a clear role, memory boundary, and collaboration responsibility.

Instead of asking one session to plan, code, test, remember every decision, and report progress at the same time, CXWorkflow splits the work across specialized sessions:

- Commander owns direction.
- Secretary owns memory and coordination.
- Developer owns implementation.
- Tester owns quality.
- Reporter owns status visibility.
- Observer owns system-level risk review.

This structure is designed for long-running projects, multi-module features, complex refactors, AI-assisted product development, and any repo where a single chat thread becomes too crowded to manage safely.

## Team Roles

| Session | Role | Responsibility |
| --- | --- | --- |
| `Commander` / `指挥` | Project lead | Understands the whole project, breaks down work, assigns tasks, defines priorities, and makes final direction calls. |
| `Secretary` / `秘书` | PMO and project memory | Records decisions, tracks task status, keeps cross-thread context synchronized, and prevents project memory loss. |
| `Developer` / `开发` | Main engineer | Implements features, fixes bugs, refactors code, verifies changes, and reports results back to Commander and Secretary. |
| `Tester` / `测试` | QA and reviewer | Reviews code quality, runs tests, finds bugs, checks regression risk, and reports issues by severity. |
| `Reporter` / `汇报` | Progress reporter | Collects project status from other sessions and produces concise progress reports. |
| `Observer` / `obs` | External observer | Reviews the whole workflow, checks whether the team structure is complete, and identifies missing roles, process gaps, or strategic risks. |

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
   Observer checks the whole system from a higher level and points out missing coverage, process weaknesses, or architectural concerns.

## Why Use Multi-Session Codex

A single AI coding thread is convenient, but it often becomes overloaded during larger projects. It may lose track of previous decisions, mix planning with implementation, or under-invest in testing and reporting.

CXWorkflow gives each session a stable job:

- Planning is separated from coding.
- Project memory is separated from execution.
- Testing is separated from implementation.
- Reporting is separated from decision-making.
- Strategic review is separated from day-to-day progress.

The result is a more compatible, reusable AI development team structure that can be applied to many kinds of software projects.

## Recommended Session Setup Prompt

Use this prompt in Codex to create the full team in one step:

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
职责：你是观察员。你从全局观察这个 AI 开发团队是否完整，检查项目是否存在遗漏模块、流程断点、角色缺失、战略偏差或质量风险，并提出改进建议。

创建完成后，请把每个 session 的 threadId、标题和职责列出来，并尽量 pin 这些线程。
```

Short version:

```text
请基于当前项目一键创建 Codex 多线程开发团队：指挥、秘书、开发、测试、汇报、obs。每个线程都在当前仓库工作，并分别承担项目总控、状态协调、代码实现、质量审查、进度汇总、全局观察职责。创建后列出 threadId 和用途，并 pin 这些线程。
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
