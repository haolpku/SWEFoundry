# Operator Catalog

## 控制平面：v1 已实现

| 算子 | 输入 → 输出 | 职责 | 失败/拒绝条件 |
|---|---|---|---|
| `io.load-records@1.0` | JSON/JSONL → `source-records` | 加载离线候选来源；源文件内容进入缓存指纹 | 非对象列表 |
| `topic.find@1.0` | `source-records` → candidates + rejections | 检查 Topic 来源、许可、五项能力、状态/恢复等工程信号 | 来源/许可缺失、能力不足、分数不足 |
| `topic.rank@1.0` | candidates → `selected-topics` | 能力指纹去重、领域配额、Top-K | 候选被去重或超过领域配额 |
| `task.design-multistep@1.0` | selected topics → blueprints | 生成五步连续 Greenfield 任务蓝图 | 下游 gate 负责拒绝不完整设计 |
| `quality.blueprint-gate@1.0` | blueprints → accepted + report | 每步检查 instruction、公开 API、公开 case、hidden 类别、确定性 mutant | 任一强制项缺失或 mutant 含随机性 |
| `contract.compile@1.0` | accepted → public contracts | 固化 Agent 可见的类名、签名、行为 case 和最终全栈回归要求 | Step ID/API 重复 |
| `mutant.plan@1.0` | accepted → mutant plan | 每 Step 生成一个定向确定性错误，含重复审计次数 | 由 blueprint gate 保证完整性 |
| `quality.audit-plan@1.0` | accepted + contracts + mutants → audit plan | 规划 schema、Oracle、Starter、mutant、隔离、确定性审计 | 合同缺失或 mutant 未覆盖五步 |
| `rollout.plan@1.0` | accepted → rollout plan/shards | 生成幂等 job、模型族、尝试次数和分片 | 少于两个模型族 |
| `release.package-plan@1.0` | contracts + audit + rollouts → package plan | 定义交付目录、机器记录、Manifest 和发布阻断项 | 不提前宣称 release-ready |

## Worker 平面：下一阶段接入

这些节点需要模型服务、容器或 Harbor。它们仍应遵守相同的 artifact contract，
但不应在控制平面里直接保存 secret。

| 建议算子 | 输入 → 输出 | 执行方式 | 验收要点 |
|---|---|---|---|
| `source.collect.github` | search policy → source records | GitHub/API adapter | 固定 commit、许可、引用范围 |
| `knowledge.build` | selected topic → local knowledge pack | fetch + sanitize worker | 离线可用、无答案泄漏、文件哈希 |
| `task.synthesize` | blueprint + contract + knowledge → task source | LLM worker | 独立五步 instruction/solution/tests |
| `verifier.build` | contract + task source → verifier bundle | LLM + deterministic compiler | hidden 测试映射需求、严格主奖励 |
| `mutant.materialize` | mutant plan + source → mutant bundle | patch worker | 每个 mutant 只引入目标错误 |
| `harbor.audit` | task + verifier + mutants → audit evidence | Harbor worker | Oracle/Starter/Mutant/隔离/重复审计 |
| `agent.rollout` | rollout plan + audited task → trajectories | Harbor agent worker | 原始轨迹、成本、耗时、异常、reward |
| `difficulty.calibrate` | rollout evidence → calibration report | deterministic reducer | pass@1/CI、Step 位置、失败类别、地板/天花板 |
| `release.package` | approved artifacts → ZIP + Manifest | packaging worker | 自包含复验、脱敏、路径可移植 |

## Topic 算子的推荐拆法

规模化时不要让一个“找 Topic” prompt 同时做搜索、判断和选题。建议拆成：

1. `source.collect.*`：按来源采集，记录 URL、commit、license；
2. `source.normalize`：统一字段、去掉 HTML/重复段落；
3. `topic.extract`：从材料提取可教学的工程能力；
4. `topic.find`：按 provenance 和工程信号做硬门禁；
5. `topic.deduplicate`：语义指纹 + 代码仓库血缘去重；
6. `topic.rank`：领域配额、稀缺度、预估成本、风险排序；
7. `topic.human-review`：只审核高分边界候选。

这样可以单独替换搜索源或模型，不影响后面的任务生产。
