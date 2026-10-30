# CVPR 2027 研究设计共识记录

> 状态：Work in progress（WIP）  
> 用途：记录当前已经达成的研究设计共识，约束后续原型、实验和论文叙事。  
> 证据状态：尚无实验结果；本文中的 RQ、假设和贡献表述均为待检验设计，不是实证结论。  
> 最近更新：2026-09-08

## 1. 研究定位

- 目标 venue：CVPR 2027。
- 主题：multimodal foundation-model agents、visual/physical feedback 与 diagnostic evaluation。
- 核心对象：通用多模态 agent 在有限交互中，能否从自身行动造成的物理反馈中获得可复用知识。
- 当前方案不使用 video generation model；保留 physics simulator 中的 agent loop。

### 中心研究问题

> 通用多模态 agent 能否把自己行动后的物理反馈转化为可复用知识，而不是只在当前任务上成功？

**English positioning**

> Can general-purpose multimodal agents transform physical feedback from their own actions into reusable knowledge that extends beyond success on the current task?

### 问题缺口

只看最终任务是否成功，会把搜索、偶然命中和真正学习混在一起。一个 agent 可能通过多次尝试找到当前目标的可行动作，却没有形成能够预测未见动作结果、或迁移到新目标的物理知识。本项目要诊断的是：交互是否产生了可复用的 physical knowledge，而不只是提高当前任务的成功率。

## 2. 研究边界与系统单位

### 与 robotics 问题的边界

本研究不以 low-level control、motion planning、embodiment 或 sim-to-real 为主要问题。模拟器是可执行的信息源和工具；agent 只做高层选择，并通过结果更新其 memory/reasoning state。

> We study physical feedback as an executable information source for foundation-model agents, rather than physical interaction as a robot control problem.

### 被评估的单位

评估单位是完整的 **model + agent harness + memory + reasoning loop**，不是脱离执行框架的 base model。模型、上下文组织、记忆表示、工具接口和反馈处理共同决定 agent 的行为，因此后续报告必须说明具体配置，避免把系统级结果全部归因于模型本身。

## 3. 已决定的研究设计

### 3.1 首个原型：rebound-to-cup

agent 的目标是让球经过运动和反弹后进入 cup。每次试验由 agent 选择：

- initial speed；
- launch angle；
- ball A/B/C。

三种球在外观或标识上可区分，但其 elasticity 和 friction 对 agent 隐藏。agent 必须在固定交互预算内，通过试验反馈推断这些 object-specific physical properties，并将所得知识用于后续预测和转移。

### 3.2 模块化 benchmark suite

已接受模块化设计：projectile、bounce 和 rolling 模块共享同一评测协议。rebound-to-cup 是第一个实现和验证的模块，不预先承诺最终 suite 的范围。

共享协议要求：

1. 环境包含可通过交互推断的隐藏物理属性；
2. agent 采取高层参数化动作；
3. 每个条件使用固定 interaction budget；
4. 交互前后使用可比较的 probe；
5. 交互结束后冻结反馈，再测试 held-out prediction 和 new-goal transfer。

### 3.3 受控反馈阶梯

保持任务、交互预算、geometry 和 initial information 不变，只改变 observation channel：

1. **No feedback**：不给出动作结果；
2. **Binary success/failure**：只返回是否成功；
3. **Terminal coordinate**：返回终止位置；
4. **Video**：返回试验过程的视频观察；
5. **Oracle accurate state**：返回准确的结构化状态。

这组条件构成信息可用性和信息提取难度的诊断阶梯。它不是简单的“信息量越多越好”排序：video 可能包含相关信息，但 agent 未必能可靠地感知、抽取并写入可用记忆；oracle state 则降低了这一负担。

**不纳入当前主设计：** shuffled feedback。它保留为后续可能的因果对照，尚未决定是否实现。

### 3.4 固定预算协议

完整流程如下：

```text
pre-interaction probe
        ↓
fixed-budget interaction under the assigned feedback condition
        ↓
freeze feedback and interaction-derived updates
        ↓
held-out action prediction + new-target transfer
```

- **Pre-interaction probe**：在任何试验反馈前测量 agent 的初始知识和预测能力。
- **Fixed-budget interaction**：agent 在指定 feedback modality 下完成相同数量的试验。
- **Freeze feedback**：交互阶段结束后不再提供新反馈，防止测试阶段继续学习。
- **Post-interaction evaluation**：在未见动作组合上做预测，并在相同球属性、移动 cup 的条件下测试 transfer。

## 4. Research Questions

### RQ1：等预算下，反馈是否改善当前任务表现？

在相同 interaction budget 下，不同 feedback modality 是否改善 rebound-to-cup 的学习曲线和预算内成功率？

### RQ2：当前任务上的改善是否对应可复用知识？

交互后，agent 是否能更准确地预测 held-out action outcomes，并把所学迁移到 moved-cup goal？当前任务 improvement 与 knowledge gain 是否一致？

### RQ3：不同反馈模态揭示了哪些瓶颈？

当 video 和 structured state 描述同一物理过程时，性能差异来自信息缺失，还是来自 perception、information extraction、memory encoding 或 reasoning bottleneck？

## 5. 待检验假设

以下均为 hypotheses，不是当前发现。

- **H1 — within-task learning：** valid feedback 相比 no feedback 会改善当前任务的 learning curve。
- **H2 — success/knowledge dissociation：** 当前任务表现的改善可能与 held-out prediction 和 transfer 的改善分离；预计会观察到 task improvement 大于 knowledge gain 的情形。
- **H3 — modality bottleneck：** structured accurate state 可能优于 video，即使 video 包含完成推断所需的相关信息。这一差异将指向 perception 或 information extraction bottleneck，而不是环境缺少证据。

## 6. 评测指标

### 6.1 当前任务表现

- **success@budget**：固定预算结束时是否成功，或预算内成功率；具体聚合定义待定。
- **best miss distance per trial**：截至每次 trial 的最小 miss distance，用于绘制学习过程。
- **learning-curve AUC**：整个预算内表现曲线的面积。
- **trials-to-first-success**：首次成功所需试验数；未成功样本需要预先规定 censoring/penalty。

### 6.2 Held-out action prediction

测试未见的 ball-speed-angle tuples，要求 agent 预测：

- landing point；
- bounce point；
- success probability。

评分包括 normalized error 和 ranking accuracy。held-out tuples 必须与交互轨迹严格隔离，防止直接复述已观察结果。

### 6.3 New-goal transfer

保持球的隐藏属性不变，移动 cup，评估：

- first-shot error；
- small-budget success；
- improvement over cold start。

该测试关注 agent 能否复用关于球和动力学的知识，而不是记住原 cup 位置对应的动作。

### 6.4 Knowledge gain

对每个 post-interaction probe，定义：

```text
knowledge gain = post-interaction score − pre-interaction score
```

若某指标是 error（越低越好），报告时应统一方向，例如使用 `pre-error − post-error`，保证正值始终表示改善。最终公式和归一化方式需在实验设计中固定。

### 6.5 中心诊断

核心分析不是单独比较 success，而是比较：

```text
current-task improvement  ↔  knowledge gain
```

建议在 agent × feedback condition × seed 层面同时报告两者，并分析四种典型结果：

| 当前任务改善 | Knowledge gain | 解释 |
|---|---|---|
| 高 | 高 | 当前成功伴随可复用知识形成 |
| 高 | 低 | 搜索、记忆具体动作或偶然命中可能主导 |
| 低 | 高 | 学到了物理规律，但当前 goal optimization 未充分利用 |
| 低 | 低 | 反馈未被有效使用，或预算不足 |

## 7. Protocol、metrics 与 benchmark validation 的区分

- **Protocol** 回答“如何测试”：pre-probe、固定预算交互、冻结反馈、post-probe 和 transfer 的顺序及控制变量。
- **Metrics** 回答“如何给 agent 打分”：success@budget、miss distance、AUC、prediction error、ranking accuracy、transfer score 和 knowledge gain。
- **Benchmark validation** 回答“这些分数是否可信”：评测可靠性、对 strong/weak systems 的区分能力、是否存在 shortcut/leakage、human sanity check，以及能否区分 luck 与 knowledge。

后续 benchmark validation 至少需要覆盖：

1. **Reliability**：多 seed 稳定性、metric variance、模拟器确定性或噪声来源；
2. **Discrimination**：强弱 agent/harness、不同反馈条件和简单 heuristic 是否可区分；
3. **No shortcuts/leakage**：ball identity、渲染、文件名、反馈文本和 held-out split 不泄露隐藏属性或答案；
4. **Human sanity**：人类是否能在同等信息和预算下理解任务并表现出合理 learning/transfer；
5. **Luck versus knowledge**：成功动作是否伴随 held-out prediction 或 moved-goal transfer 的提升。

## 8. 初步 related-work map

以下仅是当前工作清单，不构成 exhaustive review，也不支持 “first” claim。链接和题名已按公开记录做初步核对；后续仍需阅读全文并逐项验证与本项目的准确关系。

### Interactive physics / scientific discovery

- [NewtonBench: Benchmarking Generalizable Scientific Law Discovery in LLM Agents](https://arxiv.org/abs/2510.07172)：LLM agents 通过交互探索模拟系统并发现可泛化科学规律；与本项目在 interactive discovery 上接近，需要重点比较任务单位、反馈控制和 generalization probes。
- [PhysGym: Benchmarking LLMs in Interactive Physics Discovery with Controlled Priors](https://arxiv.org/abs/2507.15550)：控制 prior knowledge，评估 LLM 在交互式物理环境中的 scientific reasoning；本项目需说明受控 feedback modality 与受控 prior 的差异。
- [PHYRE: A New Benchmark for Physical Reasoning](https://arxiv.org/abs/1908.05656)：二维物理谜题、sample-efficient interaction 和跨任务 generalization 的重要基准。
- [I-PHYRE: Interactive Physical Reasoning](https://arxiv.org/abs/2312.03009)：关注动态事件中的 multi-step planning 和 in-situ intervention；本项目不以实时干预和运动规划为主。

### Static/multimodal physical understanding

- [PhysBench: Benchmarking and Enhancing Vision-Language Models for Physical World Understanding](https://openreview.net/pdf?id=Q6a9W6kzv5)：面向 VLM 的多模态物理世界理解评测。需进一步核对其静态/视频任务与本项目主动交互、反馈后知识增益的边界。

### Learning from action-conditioned visual experience

- [Unsupervised Learning for Physical Interaction through Video Prediction](https://arxiv.org/abs/1605.07157)：通过 action-conditioned video prediction 学习物体运动。该方向说明从视觉交互中学习动力学并非新问题；本项目已经移除 video generation model，重点转向 general-purpose agent 的反馈利用诊断。

### Embodied property discovery and situated induction

- [Embodied Reasoning for Discovering Object Properties via Manipulation](https://imitrob.ciirc.cvut.cz/EQA/papers/EQA2.pdf)：通过机器人操作发现 weight、stiffness 等物体属性，并涉及 reasoning、planning 与执行。它是 hidden object properties through interaction 的直接邻近工作，也凸显本项目需要明确避开 low-level robotics claim。
- [Mars: Situated Inductive Reasoning in an Open-World Environment](https://openreview.net/forum?id=3qoQ6AolAz)：agent 在 counter-commonsense 环境中通过交互归纳规则并用于决策；与 reusable situated knowledge 的问题高度相关。

### Agent evaluation unit

- [Harness-Bench: Measuring Harness Effects across Models in Realistic Agent Workflows](https://arxiv.org/abs/2605.27922)：强调 model-harness pairing 会改变 agent 表现，为本项目把 model + harness/memory/reasoning loop 作为评估单位提供方法论参照。

### 安全的贡献表述

从 physical feedback 中学习这一宽泛方向并不新。当前可能有辨识度的是以下组合，而不是任一单点：

> general multimodal agent + finite interaction + object-specific hidden physical properties + controlled feedback modalities + explicit separation of current-task success from held-out prediction and transfer

在完成 exhaustive novelty review 前，不使用 “the first benchmark” 或等价表述。更稳妥的英文定位是：

> We introduce a diagnostic evaluation protocol that separates task success from reusable physical knowledge in general-purpose multimodal agents.

> By controlling the feedback channel under a fixed interaction budget, the protocol tests whether an agent's apparent improvement transfers to held-out action prediction and new goals.

这两句是 preliminary positioning，仍需根据完整文献检索、原型可行性和实验结果修改。

## 9. 尚未决定的问题（Open / TBD）

以下事项不属于当前共识，不应写成既定方案：

- 最终范围：除 rebound-to-cup 外，projectile、bounce、rolling 各实现多少任务和变体；
- simulator 与 rendering stack；
- interaction budget 的具体数值，以及 action space 采用连续、离散还是混合设计；
- model baselines、agent harness、memory format 和 reasoning loop；
- 统计方案：seed 数、置信区间、显著性或效应量、层级聚合方式；
- benchmark validation 的具体 strong/weak controls、human protocol 和 leakage tests；
- shuffled feedback 是否加入正式实验；
- exhaustive novelty review 与最终 related-work taxonomy；
- 最终 method、实现细节和工程结构。

## 10. 近期工作顺序

1. 写出 rebound-to-cup 的最小环境规格：状态、动作、隐藏参数、终止条件和可观测量。
2. 固定 pre/post probe 与 held-out split，先确保“知识”可被独立测量，再实现 agent loop。
3. 明确五档 feedback 的内容和等预算原则，检查各档是否意外泄露不同的额外信息。
4. 设计一个 heuristic、一个弱 agent 和一个较强 agent/harness，用于 benchmark discrimination sanity check。
5. 做 exhaustive related-work review，重点比较 NewtonBench、PhysGym、PHYRE/I-PHYRE、Mars 与 embodied property discovery。
6. 原型通过后再决定 suite 范围、统计方案和是否加入 shuffled feedback。

