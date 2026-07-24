# 从 10 条扩展到 1,000 / 10,000 条

## 基本原则

规模化目标不是“生成数量”，而是最大化最终可售的通过数量，并保留每条数据为何
被接受的证据。所有阶段用不可变 artifact 传递；队列只保存 digest 和 job id。
重试不改变 job id，同一输入不会重复付费或重复发布。

## 三个规模档位

| 规模 | 编排方式 | 人审策略 | Rollout 策略 | 建议产能目标 |
|---|---|---|---|---|
| 10 | 单机 DAG，逐题 review | 10/10 深审 | 每题至少 2 模型族 × 3–5 次 | 验证模板和失败分类 |
| 1,000 | 100–200 条/shard，队列 worker | 全审边界项 + 20% 随机抽检 | 门禁后分层抽样，候选发布集全跑 | 200–400 条 calibration-ready |
| 10,000 | 多队列、租约、优先级、成本预算 | 风险采样 + reviewer 一致性审计 | 先 cheap smoke，再对高价值候选全校准 | 2,000+ 条多样化候选池 |

这些是容量规划值，不是质量承诺；真实转化率应由前 100 条 pilot 更新。

## 分层漏斗

建议 10,000 条 Topic 输入的初始预算按以下漏斗规划：

| 阶段 | 示例保留率 | 10,000 输入后的数量 | 主要成本 |
|---|---:|---:|---|
| 来源/许可/去重 | 60% | 6,000 | 低，确定性 |
| Topic 工程性与多样性门禁 | 50% | 3,000 | 低 |
| 五步蓝图与公开 Contract | 70% | 2,100 | 中，LLM + 静态 gate |
| 代码、solution、verifier 合成 | 65% | 1,365 | 高，LLM |
| Oracle/Starter/Mutant 审计 | 65% | 887 | 高，容器 |
| rollout 难度与区分度校准 | 60% | 532 | 最高，Agent tokens |
| 人审/买方抽检 | 80% | 426 | 专家时间 |

因此若目标是交付 1,000 条，不能只准备 1,000 个 Topic；需要用 pilot 的实测
转化率反推候选池，通常应准备约 2–4 倍。禁止为了补数量放宽 P0 门禁。

## 队列与状态

每个 worker job 至少记录：

```json
{
  "job_id": "<operator>@<version>:<input-digest>:<config-digest>",
  "operator": "harbor.audit",
  "input_digests": ["..."],
  "attempt": 1,
  "lease_owner": "worker-17",
  "lease_expires_at": "...",
  "status": "queued|running|succeeded|retryable|rejected|dead-letter",
  "output_digests": [],
  "error_class": null,
  "cost": {"input_tokens": 0, "output_tokens": 0, "usd": 0}
}
```

- `retryable` 只用于 API 限流、机器中断、容器拉取失败；
- contract、测试、许可、作弊漏洞属于 `rejected`，不能盲目重试；
- 同一 job 最多重试固定次数，随后进入 dead-letter 人工归因；
- worker 通过短租约领取任务，失联后自动回队列；
- 输出先落不可变 artifact，再原子提交 job 成功状态。

## Shard 与并行

- Topic/蓝图：按 source/domain 分片，便于配额和去重；
- 代码合成：按任务独立并行；
- Harbor 审计：按镜像/依赖分组，提高镜像缓存命中；
- rollout：按模型服务和 token budget 分队列，防止一个供应商故障阻塞全局；
- 发布包：只消费审核通过的 digest，不扫描可变工作目录。

三台共享盘机器可让 artifact store 放在共享盘，但每个 Harbor job 的可写 workspace
应放在节点本地临时目录，完成后只上传证据 artifact。禁止多个 worker 共同写一个
任务目录。

## 质量 SLO

批次必须至少监控：

- provenance/license 完整率；
- Topic、blueprint、audit、rollout 各阶段接受率；
- Oracle、Starter、每 Step mutant 通过/拒绝率；
- 相同输入重复审计的一致率；
- public smoke 与 hidden checks 差值；
- pass@1、置信区间、Step 位置通过率；
- 地板率（所有模型均失败）和天花板率（所有模型均成功）；
- 每个接受任务的模型成本、Harbor 时间和人审时间；
- domain/source/语言/系统形态的分布与重复率；
- 脱敏、Manifest、自包含复验通过率。

建议发布硬门槛：

- Oracle 100%，Starter 严格整题 0；
- Step 1–5 定向 mutant 全拒绝，重复审计一致；
- public contract 全通过；
- verifier 与 Agent workspace 隔离；
- 至少两个独立模型族有重复 rollout；
- 难度落在目标区间且不存在未解释的接口地板；
- 人工 reviewer 签核来源、真实性、测试映射和买方可读性。

## 成本控制

按顺序执行：确定性门禁 → 低价模型蓝图 → 静态检查 → 代码合成 → Harbor →
便宜模型 smoke → 正式跨族 rollout。任何阶段失败都停止后续花费。

预算必须绑定：

- operator；
- source/domain；
- model family；
- task id；
- 输入/输出 tokens；
- 成功、拒绝或基础设施失败类别。

只有这样才能回答“每卖出一条高质量数据实际花多少钱”，并定位应该优化 Topic、
prompt、verifier 还是 rollout scaffold。

## 推荐实施顺序

1. 用当前算子 DAG 生产 20–30 个蓝图，人工确认 Topic 和 Contract 的接受标准；
2. 接入 `task.synthesize`、`verifier.build` 和 `harbor.audit` 三个 worker；
3. 完成 100 条 pilot，建立真实转化率、成本和失败分类；
4. 固化 operator/container/model 版本，扩到 1,000；
5. 达到稳定 SLO 后再扩到 10,000，并引入跨批语义去重和 reviewer 一致性抽检。
