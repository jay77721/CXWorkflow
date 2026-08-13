# CXWorkflow — 给 Codex 用的仓库

This repository is a Codex plugin + workflow kit built **for Codex itself**. When
you (Codex) work here, treat this file as your operating manual: bootstrap the
skill if needed, then follow the protocol in daily development.

## 首次使用：自主安装（每台机器一次）

The `cxworkflow` skill is **not** auto-loaded from this repo — it must be
installed into `~/.codex/skills/` (or as a plugin) once per machine. If it is not
installed yet, install it yourself:

```bash
bash scripts/bootstrap.sh        # macOS / Linux
# 跨平台等价：python3 scripts/bootstrap.py
```

How to know it is already installed:

- `~/.codex/skills/cxworkflow/SKILL.md` exists, **or**
- the `cxworkflow` plugin is listed in `~/.agents/plugins/marketplace.json`.

`bootstrap` copies `skills/cxworkflow` into `~/.codex/skills/` (idempotent) and,
with `--with-plugin`, also syncs the local plugin via
`scripts/update_local_plugin.py`. After bootstrapping, tell the user to open a
new Codex thread so the skill is loaded.

## 日常开发：遵守并主动使用

- 用户要求"创建 / 解释 / 运行多线程开发团队"时：先读
  `skills/cxworkflow/SKILL.md` 并按其协议执行；用
  `python3 scripts/cxwf.py prompt --level N` 生成建队 Prompt，**不要自己编**。
- 任何需要跨会话持久化的状态（任务、事件、决策、简报）：写入 `.cxworkflow/`
  状态存储（`cxwf.py init / task / event / decision / brief / check`），不要
  只依赖单个会话的记忆。
- 任务状态机：`Planned -> Assigned -> Implementing -> ReadyForTest -> Testing
  -> Fixing -> Accepted -> Reported`，用 `cxwf.py task set` 推进，禁止跳步；
  状态转移合法性由 `cxwf.py check` 校验。
- 非指挥会话写给秘书的消息必须包含 8 字段：`Event、Source、Task、Status、
  Severity、Evidence、Suggested Next、Needs Commander`。
- 修改本仓库前先验证：`python3 -m unittest discover -s tests` 和
  `python3 scripts/check_plugin.py .`。不要删除或改写 SKILL.md / README 中
  的协议字段（黄金测试会拦截）。

## 仓库地图

| 路径 | 用途 |
| --- | --- |
| `skills/cxworkflow/SKILL.md` | 工作流协议：角色、事件、状态机、收敛模式、建队 Prompt |
| `scripts/cxwf.py` | 状态 CLI：文件化事实源 + `check` 校验 + 分级 Prompt |
| `scripts/bootstrap.py` | 自主安装 skill（本文件说明的引导入口） |
| `scripts/update_local_plugin.py` | 本地插件安装/更新（cachebuster 只写副本） |
| `scripts/check_plugin.py` | 自包含插件/skill 校验（CI 同款） |
| `scripts/release.py` | keep-a-changelog 版本发布 |
| `tests/` | 状态机单测 + CLI 集成测试 + Prompt/AGENTS 黄金测试 |
