# session-temp-cleanup 通用版 · 安装与使用

## 安装

把 `session-temp-cleanup/` 整个文件夹放进你的 Agent 技能目录：

- WorkBuddy / CodeBuddy 系：`<用户目录>/.workbuddy/skills/`
- 其他 Agent：放各自约定的 skills 目录

## 首次使用：先校准环境（重要）

```bash
python -u scripts/probe_env.py
```

按输出结论确定工作流并填入 `LOCAL-NOTES.md`：

- 工作区删除**进入回收站** → **两步法**（清理后必须 purge 才能真正释放空间）
- 工作区删除**未进回收站** → 单步法（删除即真释放；purge 可保留作保险）

## 日常清理（示例）

```bash
python -u scripts/cleanup.py --dry-run "<目标目录>"            # ① 盘点
python -u scripts/cleanup.py           "<目标目录>"            # ② 删除
python -u scripts/purge_recycle.py --execute "<目标目录>"      # ③ 若为两步法：真释放
python -u scripts/purge_recycle.py            "<目标目录>"     #    复扫核验（应 0 条）
```

## 其余工具

- `fast_del_tree.py` —— 可选加速件：ctypes 原生删除目录树/单文件（速度快）。
- `scan_venvs.py` —— 只读盘点虚拟环境（venv / conda），不做任何删除。

## 说明

- 脚本仅依赖 **Python 标准库**，面向 **Windows**。
- 删除行为因环境（甚至因路径）而异——`probe_env.py` 会实测你的机器，别照搬他人（或旧文档）的结论。
