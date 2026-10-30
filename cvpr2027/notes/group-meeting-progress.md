# CVPR 2027 项目组会进展简报（3–5 分钟）

> Work in progress：目前完成问题定义与初步评测设计收敛，尚无实验结果；related work 仍需系统检索。

## 给 Mentor 的研究叙事

> **我们不是先列 Benchmark 有哪些组件，而是先定义现有工作没有回答的问题，再让每个 Benchmark 设计对应这个问题中的一个证据缺口。**

### 1. 相关工作分别研究什么、贡献什么

- **Passive / static physical reasoning**（如 [PhysBench](https://physbench.com/)）：测模型能否从给定视觉或文本证据判断物理概念、因果、空间关系和结果；贡献是系统评测既定证据上的物理理解，但不包含行动后反馈与 belief update。
- **Physics puzzles / interactive physical problem solving**（[PHYRE](https://arxiv.org/abs/1908.05656)、[I-PHYRE](https://arxiv.org/abs/2312.03009)）：测任务成功、sample efficiency、planning 和 generalization；贡献是让物理推理接受交互行动和任务结果的检验，但 success 可能同时来自物理知识或 action search。
- **Interactive scientific discovery**（[PhysGym](https://arxiv.org/abs/2507.15550)、[NewtonBench](https://arxiv.org/abs/2510.07172)）：通过主动 probe 发现一般规律、方程或 hypothesis，并研究 prior、复杂度与 law recovery；贡献是把规律发现放进交互实验过程。
- **General agents learning from feedback**（[LLF-Bench](https://arxiv.org/abs/2312.06853)）：测 agent 在 loop 中能否利用交互反馈提高后续任务表现；贡献是把反馈内容和 task-performance adaptation 变成可控变量。

这是 preliminary map，不是完整综述；下一步要做 systematic literature review。当前不做 first claim。

### 2. 这些工作共同留下什么未解问题

当 agent 在多次物理交互后表现提高，现有评测通常不能区分：它是从反馈中获得了可复用的对象 / 环境知识，还是只通过搜索、重复或记忆找到了当前目标的有效动作。

我们要联合诊断此前分散的证据链：

```text
physical feedback
→ updated object / environment belief
→ unseen-action outcome prediction
→ new-goal action
```

因此，我们谨慎地把贡献定位为一个 **under-examined diagnostic question**：任务表现变好，是否真的对应 feedback-driven reusable physical knowledge？

### 3. Benchmark 怎样逐段补证据

- **评测单位**：general-purpose multimodal model + 固定 harness / agent loop，包括 memory、reasoning 与动作接口。
- **Task / data**：模块化 simulated physical environments，从 rebound-to-cup 开始；系统变化 hidden object properties、geometry 和 target locations，并建立 task families、interaction episodes 与 held-out splits。
- **协议**：pre-interaction probe → fixed trial budget 内按反馈行动 → freeze feedback → post-probes。
- **反馈条件**：none、binary success / failure、terminal coordinate、video、oracle accurate state。
- **Post-probes**：current-task improvement、held-out action outcome prediction、new-goal transfer。

### 4. 实验怎样区分两种解释

同一比较内固定 tasks、priors、action budget 和 harness，只改变 feedback channel；同时比较不同 models / harnesses 和反馈条件。当前任务看 learning curve、success@budget、miss distance；知识证据看 held-out prediction error / ranking、transfer first-shot error 和 small-budget performance。

核心分析是把 **task improvement** 与 **knowledge gain = post-probe score − pre-probe score** 并列：

- task、prediction、transfer 一起提高，才支持“反馈形成了可复用知识”。
- task 提高但 prediction、transfer 不变，支持“当前成功主要来自搜索 / 重复”，并反驳“成功本身等于知识”。
- prediction 提高但 transfer 不变，说明 belief 可能更新了，但尚未转化为新目标行动。
- richer feedback 与 no-feedback 无差异，会削弱“这些反馈在当前预算和 harness 下能驱动学习”的解释。
- oracle state 优于 video，支持信息提取可能是瓶颈，但不能单独证明高层 reasoning 已解决。

这些都是预先定义的判读规则，不是实验发现。

## Data design 要点

- 用 hidden physical parameters、geometry、target locations 定义 task families。
- 训练不是前提；构造 interaction episodes、pre/post probe sets、unseen-action splits 和 target-transfer splits。
- 平衡 difficulty，随机化非物理标识，排除 visual / identifier leakage。
- simulator 提供 outcome、trajectory 与 physical state ground truth；各反馈组只看到条件允许的信息。

## 已确定 / TBD

**已确定：** 核心问题、评测单位、rebound-to-cup 原型、pre/interact/freeze/post 协议、反馈阶梯、三类 post-probes，以及 task improvement 对 knowledge gain 的核心比较。

**TBD：** simulator/rendering、budgets/action discretization、models/harnesses、statistics、benchmark validation、broader modules、systematic related work；shuffled feedback 暂缓。
