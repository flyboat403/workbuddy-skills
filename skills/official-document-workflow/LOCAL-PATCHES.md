# 本机本地改动记录

本目录是官方文档工作流技能 official-document-workflow（市场发布 v1.0.0，ownerId 542222）的本地副本，
在 2026-10-18 做过一次本地增强。**发布方更新、重装或覆盖安装会丢失这些改动**，届时按下面说明重做。

## 背景

把《AI生成公文初稿的四项校准》（抖音「公文摆渡」）范式化为起草前的立意框架"谋篇四定"：
定叙事 / 定主线 / 定边界 / 定语态。采用"前置为主、后置保留"双轨设计——前置指导起草与改写，
后置作为交付核验，两者共用同一知识源（drafting-positions.md），避免两处维护。

来源材料：`references/AI生成公文初稿的四项校准_旁白精校版.md`（2026-10-18 已随技能存档，原工作区副本已清理）

## 1. 新增 references/drafting-positions.md（谋篇四定，唯一权威版）

四条各含：决策问句、适用场景、典型错误、判据；文末附"落位"表（Mode A → `brief.json` 的
`positions` 字段；Mode B → `structure-analysis.md` 的分析透镜；交付前 → review-checklists 的
Positioning 核验块）。

## 2. SKILL.md 改动（4 处）

- "Required references" 增加一行：For pre-drafting positioning: `references/drafting-positions.md`。
- Mode A 流程：原第 3 步前插入"Resolve the four pre-drafting positions…"步骤（含 `positions` 字段与
  起草遵循要求），原步骤顺延，共 9 步。
- Mode B 流程：第 2 步结构分析改为以四条为分析透镜；第 3、5 步分别补"applying the resolved
  positions"与"verify the held positions"。
- "Quality gates"：在 Structure 之后新增第 5 条 **Positioning**，原 Tone / Format / File output
  顺延为 6 / 7 / 8。

## 3. references/review-checklists.md 改动（1 处）

- 在 "Content integrity" 与 "Language and tone" 之间新增 "## Positioning" 核验块（4 条，
  逐条引用 drafting-positions.md，不重复其规则）。

## 重做顺序

先按来源材料重建 `references/drafting-positions.md`，再依次修改 `SKILL.md` 与
`references/review-checklists.md`。
