# 和 Mentor 讨论用：从问题到证据的 Research Skeleton

> **我们不是先列 Benchmark 有哪些组件，而是先定义现有工作没有回答的问题，再让每个 Benchmark 设计对应这个问题中的一个证据缺口。**

> 这是 preliminary map，不是完整 related-work 结论。下面只采用指定工作的可核查描述；下一步仍需 systematic literature review。

## 一眼看懂整条研究逻辑

```text
[Related work：不同研究线分别回答什么]
│
├─ A. Passive / static physical reasoning
│     给定图像、视频或问题 → 判断物理概念、因果、空间关系或结果
│     贡献：测“模型看到既定证据后是否理解物理”
│     未覆盖：行动后的反馈，以及 belief 随反馈怎样更新
│
├─ B. Physics puzzles / interactive physical problem solving
│     在物理环境中选择动作或实时干预
│     贡献：测任务成功、sample efficiency、planning、generalization
│     未覆盖：成功来自可复用物理 belief，还是当前 action search
│
├─ C. Interactive scientific discovery
│     主动 probe 模拟系统 → 恢复一般规律、方程或高保真 hypothesis
│     贡献：测 law discovery，并控制 prior、复杂度或记忆风险
│     未覆盖：对象级反馈怎样支持未见动作预测与新目标行动
│
└─ D. General agents learning from interaction feedback
      在 agent loop 中接收反馈 → 改善后续任务表现
      贡献：直接研究反馈内容与 task-performance adaptation
      未覆盖：物理 belief、未见动作预测和新目标行动的联合诊断
                         │
                         ▼
[Missing question：现有评测分不开的两种解释]
同一个 agent 在多次物理交互后表现变好，究竟是：
  K. 反馈驱动它更新了对象 / 环境 belief，形成可复用物理知识；还是
  S. 它只是重复、搜索或记住了当前目标下的有效动作？

现有研究分别测 physical understanding、final success / generalization、
law recovery 或 task-performance adaptation，但没有联合诊断：

physical feedback
  → updated object / environment belief
  → unseen-action outcome prediction
  → new-goal action
                         │
                         ▼
[Operational definition：什么才算“可复用知识”]
交互结束后冻结反馈；如果 agent 相比交互前：
  ① 更准确预测没有试过的动作结果，并且
  ② 面对新目标时首轮或少量试验表现更好，
才构成“反馈形成了可复用知识”的证据，而不只是在原目标上成功。
                         │
                         ▼
[Benchmark evidence：每个设计补哪段证据]
pre-probe ── 测初始 belief / prediction
    ↓
fixed trial budget + assigned feedback ── 控制可获得的信息
    ↓
feedback-conditioned actions ── 记录表现怎样随交互变化
    ↓
freeze feedback ── 切断继续搜索
    ↓
post-probes
  ├─ current-task improvement ── 是否更会完成原任务
  ├─ held-out action prediction ── 是否形成可外推的 outcome belief
  └─ new-goal transfer ── 已有知识能否支持新目标行动
                         │
                         ▼
[Possible conclusions：由观测模式决定，不预设结果]
  ├─ task ↑，prediction ↑，transfer ↑
  │    → 支持“反馈促成可复用知识”
  ├─ task ↑，prediction ≈，transfer ≈
  │    → 支持“成功主要来自当前目标下的搜索 / 重复”，反驳强知识解释
  ├─ prediction ↑，transfer ≈
  │    → belief 有更新，但尚不足以支持新目标行动
  ├─ richer feedback ≈ no feedback
  │    → 反驳“这些反馈在当前预算和 harness 下能驱动学习”
  └─ oracle state 明显优于 video
       → 支持“从感知反馈提取有效状态是瓶颈”，但不能单独证明推理机制正确
```

## 1. Related work：先说每条线研究什么、贡献什么

### A. Passive / static physical reasoning benchmarks

这一类工作问：模型在拿到既定的视觉或文本证据后，能否识别物理概念、推断因果与空间关系、预测稳定性或事件结果。[PhysBench](https://physbench.com/) 的公开页面把目标概括为评估 physical concepts、physics problems、spatial reasoning，以及更广义的物理与因果理解。它的贡献是把多种物理理解能力整理成评测；对我们而言，缺少的是受控的“行动—反馈—belief update”序列，因此不能直接测 feedback-driven belief update。

### B. Physics puzzles / interactive physical problem solving

[PHYRE](https://arxiv.org/abs/1908.05656) 用二维经典力学 puzzles 研究 physical reasoning，强调 sample-efficient solving 和跨 puzzle generalization。[I-PHYRE](https://arxiv.org/abs/2312.03009) 进一步要求 agent 在动态事件中进行 multi-step planning 和 in-situ intervention，并用不同 splits 检查学习与泛化。这条线的重要贡献是让物理理解接受行动结果和任务成功的检验；但只看 success 或 efficiency，仍可能无法判断改进来自可复用的物理 belief，还是对当前 action space 的有效搜索。

### C. Interactive scientific discovery

[PhysGym](https://arxiv.org/abs/2507.15550) 让 LLM agents 在交互式物理模拟中主动 probe、顺序收集数据并提出底层物理规律的 hypothesis，同时控制 prior knowledge，并评价 hypothesis accuracy 和 model fidelity。[NewtonBench](https://arxiv.org/abs/2510.07172) 将 scientific law discovery 放进复杂模拟系统的交互探索中，以 counterfactual law shifts 构造跨物理领域、抗记忆的任务。这条线的贡献是把 law discovery 从静态拟合推进到主动实验；我们的候选问题更窄：有限反馈是否更新了某个对象 / 环境的 belief，并从未见动作预测继续传递到新目标行动。

### D. General agents learning / adapting from interaction feedback

[LLF-Bench](https://arxiv.org/abs/2312.06853) 直接评估 agent 能否从行动后的自然语言反馈和指令中交互学习，并允许控制反馈携带 suggestion、explanation 或 instantaneous performance 等信息。这条线的贡献是把“反馈内容如何影响 agent loop 中的任务适应”变成可控问题。我们要补的诊断位于物理场景：反馈是否先更新 outcome belief，这种更新又是否支持未见动作预测和新目标行动。

**谨慎定位：**“反馈后的任务改进是否对应可复用物理知识”是一个尚未被上述评测联合诊断、值得系统核查的问题；现在不做 first claim。下一步需要扩展检索范围，并逐项核对是否已有工作同时测 pre/post belief、held-out action prediction 与 new-goal transfer。

## 2. 从相关工作推出的未解问题

> 当 general-purpose multimodal agent 在多次物理交互后表现提高时，我们如何判断它是利用反馈获得了可复用的对象 / 环境知识，而不只是搜索或重复当前目标下的动作？

关键不是再加一个 success benchmark，而是把“学习”拆成可观察的因果链：

```text
反馈里是否有信息
→ agent 的对象 / 环境 belief 是否更新
→ 更新后的 belief 能否预测未尝试动作
→ 这种预测能力能否支持新目标下的行动
```

如果只看最终成功，就无法定位链条在哪一段成立或断裂。

## 3. Benchmark 如何研究这个问题

### 评测对象

评测单位是 **general-purpose multimodal model + 固定的 harness / agent loop**，包括输入组织、memory、reasoning loop 与动作接口。比较时同时报告底座模型和 harness，因为可观察到的学习来自整个 agent system。

### Task / data

- 使用模块化 simulated physical environments；第一项原型是 **rebound-to-cup**。
- agent 选择 ball A / B / C、initial speed 和 launch angle；球的 elasticity、friction 等属性隐藏且系统变化。
- 用 hidden physical parameters、geometry 和 target locations 定义 task families；每个 family 生成多个 interaction episodes。
- 在 family 内外建立 held-out splits，避免只记住单个场景或动作组合。

### Interaction protocol

```text
pre-interaction probe
→ fixed trial budget 内根据指定反馈继续行动
→ freeze feedback
→ post-interaction probes
```

反馈条件是：**none、binary success / failure、terminal coordinate、video、oracle accurate state**。oracle state 是信息上界和诊断条件，不是默认输入。

### Post-probes 与证据缺口

- **Current-task improvement**：同一目标下是否随试验变好，对应“反馈是否改善行动”。
- **Held-out action outcome prediction**：预测未尝试 ball–speed–angle 的落点、反弹点或成功排序，对应“belief 是否可外推”。
- **New-goal transfer**：改变目标位置后测 first shot 与 small-budget 表现，对应“知识是否能支持新目标行动”。

## 4. Experimental design：怎样排除替代解释

### 公平比较

- 同一比较内固定 tasks、initial priors、action budget 和 harness，只改变 feedback channel。
- 横向比较多个 models / harnesses，纵向比较同一系统在不同反馈条件下的差异。
- 记录完整 learning curve，而不只报告最后一次是否成功。

### 指标

- 当前任务：success@budget、best miss distance、learning-curve AUC、trials to first success。
- 未见动作：outcome prediction error，以及候选动作的 ranking quality。
- 新目标迁移：first-shot error、small-budget success，以及相对 cold start 的 improvement。
- **Knowledge gain = post-probe score − pre-probe score**；误差型指标需统一变换方向，使正值始终表示改善。

### 结果模式与解释边界

| 观测模式 | 支持的解释 | 被削弱或证伪的解释 |
|---|---|---|
| 有反馈组 task、held-out prediction、transfer 都优于 no-feedback，且 knowledge gain 随反馈信息量上升 | 反馈驱动了可复用 belief acquisition | “提升只来自当前任务搜索” |
| task 明显提升，但 prediction 与 transfer 没有相对 pre-probe / no-feedback 改善 | 当前目标上的搜索、记忆或重复足以解释成功 | “任务成功本身证明学到了可复用知识” |
| prediction 改善，但 transfer 不改善 | agent 提取了部分 outcome structure，但没有把它有效用于新目标行动 | “belief improvement 足以自动带来迁移” |
| binary / coordinate / video 与 no-feedback 无差异 | 在给定预算和 harness 下，没有证据表明这些反馈被有效利用 | “提供反馈就会产生学习” |
| oracle state 改善而 video 不改善 | 信息提取可能是主要瓶颈 | 不能据此断言高层 reasoning 已充分解决 |
| pre/post、反馈条件间都无稳定差异 | 当前 benchmark、预算或系统没有检出目标效应 | 既不能支持知识获得，也不能直接证明 agent 永远不能学习 |

这些结论都必须基于预先定义的对照、置信区间和重复实验；它们目前是判读规则，不是发现。

## 5. Data design：让证据可解释

- **Task families**：由 hidden physical parameters、geometry、target locations 的组合定义；参数范围和组合规则要显式记录。
- **不是以训练为前提**：核心数据单元是 interaction episode，以及配套的 pre/post probe sets；模型可以原样评测，不要求在本 benchmark 上训练。
- **Unseen-action split**：probe 的 ball–speed–angle tuples 不得出现在交互历史中，并控制与已试动作的距离。
- **Target-transfer split**：保持已交互对象与环境规律，改变 target location；同时设置合理跨度，避免新目标过近或不可达。
- **Difficulty balance**：按 no-feedback baseline、oracle baseline 与几何可达性分层，避免全是过易或过难任务。
- **防泄漏**：随机化不具物理意义的颜色、编号和渲染细节；检查 ball ID、背景或文件顺序不能直接泄露 hidden properties。
- **Ground truth**：由 simulator 记录完整 trajectory、terminal outcome、contact / bounce state 和生成参数；对 agent 只开放对应反馈条件允许的信息。

## 6. 目前已确定 / 接下来要定

### 目前已确定

- 研究对象是 feedback → belief → prediction → transfer 的证据链，而不是只做任务成功榜单。
- 评测单位是 general-purpose multimodal model + harness / agent loop。
- 从 rebound-to-cup 开始，系统变化隐藏物性、几何与目标位置。
- 使用 pre-probe → fixed-budget interaction → freeze → post-probe 协议。
- 主反馈条件和三类 post-probes 已确定。
- 核心分析并列比较 task improvement 与 knowledge gain。

### 接下来要定

- simulator / rendering、接触与反弹 ground truth 的具体实现。
- trial budgets、连续或离散 action space，以及 action discretization。
- models、harnesses、memory / reasoning 配置与报告规范。
- 重复次数、统计检验、置信区间、多重比较和 effect size。
- task-family 参数范围、split 规则、difficulty calibration 与 benchmark validation。
- 是否以及何时加入 projectile、bounce、rolling 等 broader modules。
- systematic / exhaustive related-work review，以及最终 novelty boundary。
- shuffled feedback 暂缓，后续再决定是否作为因果诊断条件。

## 汇报时的一句话收束

我们要建立一套对照证据，判断 agent 在物理交互中变好时，究竟是从反馈中更新了可复用 belief，还是只找到了当前任务的动作。

## 四篇核心相关工作与我们的切入点

[PHYRE](https://arxiv.org/abs/1908.05656) 研究的核心问题是：agent 能否在二维物理谜题中以较少试验找到解，并把解题能力泛化到新的任务。它提供可反复尝试的 simulator，让方法在行动、观察结果、继续尝试的过程中求解，再以任务成功和 sample efficiency 等结果衡量跨任务泛化。论文的主要经验结论是，当时评测的现代学习方法在高效解题上仍明显不足，与人类的 sample-efficient performance 还有较大差距。PHYRE 并非不研究学习；更准确的区别是，它的主要 outcome metrics 不能直接区分性能提升究竟来自反馈驱动的可复用物理知识，还是来自对当前动作空间的搜索。我们的 benchmark 在这之上加入交互前后 probe、未见动作结果预测和新目标迁移，用额外证据判断“解出来了”是否伴随可复用 knowledge gain。

[I-PHYRE](https://arxiv.org/abs/2312.03009) 进一步追问：面对持续变化的物理事件，agent 能否在正确时机进行 in-situ intervention，同时完成 multi-step planning，并在不同任务划分上泛化。它把干预时机和动作序列纳入动态任务，通过四类 game splits、不同 planning strategies，以及 supervised / reinforcement learning baselines 检查求解与 zero-shot generalization。论文报告这些方法与人类表现之间仍有显著差距，说明动态时序、连续决策和泛化的组合仍然困难。I-PHYRE 已经严肃评估交互中的学习与泛化；我们补充的不是另一种 success 指标，而是一个更细的 within-episode 诊断：行动反馈是否形成了显式、可复用的对象 / 环境模型，并使 agent 能预测未尝试动作的结果。换言之，我们把“会解和会泛化”继续拆成 belief update、unseen-action prediction 与 new-goal transfer 三段证据。

[PhysGym](https://arxiv.org/abs/2507.15550) 与我们的设定最接近之一。它问的是：LLM agent 在不同 prior-knowledge levels 和环境复杂度下，能否通过主动实验发现底层物理规律。为此，PhysGym 让 agent 在受约束的交互式模拟中主动 probe、顺序收集数据并提出关于隐藏规律或方程的 hypothesis，再以 hypothesis accuracy 和 model fidelity 评价发现质量。其基线实验表明，这套评测能够区分模型在不同 prior 和 task complexity 下的能力，模型表现会随这些条件而变化。我们与它都研究 finite interactive physics 和 knowledge acquisition，但目标知识不同：PhysGym 的终点是一般 law / equation recovery；我们的终点是对象级或 instance-specific knowledge 能否支持未见动作结果预测与 goal-conditioned action。方法上，我们还显式控制 none、binary、terminal coordinate、video、oracle state 的 feedback-modality ladder，并把 current-task success 与独立测得的 knowledge gain 并列，从而检查任务变好是否真的意味着获得了可复用知识。

[NewtonBench](https://arxiv.org/abs/2510.07172) 问的是：LLM agents 能否通过交互实验发现可泛化的科学定律，同时兼顾科学相关性、规模化和抗记忆性。它包含 12 个 physics domains 中的 324 个 law-discovery tasks，通过 metaphysical / counterfactual law shifts 对经典定律作系统改写，并要求 agent 主动 probe 复杂模拟系统、恢复隐藏原则。论文的主要经验结论是，frontier models 已表现出一定但脆弱的 discovery capability：能力随系统复杂度和 observational noise 增大而明显下降；工具辅助还可能使较强模型过早从 exploration 转向 exploitation，从而满足于次优 hypothesis。NewtonBench 的评价终点是 hidden-law discovery 及其 generalization；我们的切入点则是更日常的行动后果能否成为可复用物理知识。我们在受控反馈通道下明确分开 current-task success、held-out action prediction 和 new-goal transfer，因此既能发现“成功但没有可复用知识”，也能定位 video 等反馈在哪个环节没有被转化为有效 belief。

综合来看，PHYRE 与 I-PHYRE 主要问 agent 能否求解并泛化 interactive physics tasks，PhysGym 与 NewtonBench 主要问 agent 能否通过主动实验恢复隐藏的一般规律；我们的 benchmark 问的是，general-purpose multimodal agent 能否把自身行动造成的反馈转化为可复用物理知识。关键证据不止是当前任务成功，而是交互后在 unseen-action prediction 和 new-goal action 上也出现相对 pre-probe 的增益。这一定位目前只是基于四个核心 comparator 的 preliminary positioning；仍需 systematic literature review 来检验边界，因此不提出“first”主张。

## 这个评测集具体长什么样

先把整个评测想成同一个隐藏世界从头走到尾。下面用 **W-017** 做 running example。所有物性、坐标、速度、角度和动作结果都是 **illustrative draft；simulator validation required**：它们现在用于把实验逻辑讲具体，最终范围和真实轨迹必须由 simulator 校准后确定。

W-017 是一个二维 ground-bounce-to-cup 场景。球从约 (0 m, 1 m) 出发，原始杯口中心暂放在 x=6 m，可选速度为 4–10 m/s，角度为 20–60 degrees，重力默认采用标准值，除非后续把 gravity 也纳入变化因素。评测器在生成 world 时知道三个球的隐藏属性：

| Agent 可见标签 | 仅供读者 / evaluator 理解的材料称呼 | restitution e | friction mu | mass |
|---|---|---:|---:|---:|
| Ball A | wood-like | 0.45 | 0.35 | 0.10 kg |
| Ball B | rubber-like | 0.85 | 0.20 | 0.10 kg |
| Ball C | foam-like | 0.20 | 0.65 | 0.06 kg |

“wood-like / rubber-like / foam-like” 只是给读者和 evaluator 的解释性名字，绝不会显示给 agent；数值同样不会进入 prompt。Agent 只看到 A/B/C 和每个 world 随机化后的颜色。最终物性范围还要通过 simulator calibration，确保任务既可解，又能让不同材料产生可分辨但不过分显眼的结果。这样设计，是为了迫使 agent 从自己的行动后果中推断物性，而不能靠标签或颜色猜答案。

正式交互前先做 pre-probe。比如系统问：“如果在 W-017 中执行 (B, 7.5 m/s, 32°)，第一次反弹大概发生在哪里，最终落点相对 x=6 m 的杯子是偏前还是偏后？”这个 tuple 从未实际执行。另有 2–4 个类似问题，并临时给出一个新目标让 agent 直接选 first action。所有 pre-probe 答案提交完之前，系统都不返回 ground truth 或模拟画面。原因是，如果答一道就揭晓一次结果，pre-probe 会变成免费的 interaction trials，后面的 knowledge gain 就不再干净。

随后杯子回到 x=6 m，两名假想 agent 各自获得 10 次尝试。10 只是便于讨论的默认值，正式预算记作 B，仍是 TBD。每个 action 都是 (ball_id, speed, angle)。第一次，两者都可能试 (B, 8 m/s, 35°)；在叙事占位中，B 发生强反弹并 overshoot 原杯位。第二次若试相近参数的 A，A 的反弹较弱，可能落在杯前；若试 C，C 因低 restitution、高 friction 而损失更多能量，可能更明显地 shortfall。第三次再把 B 降到约 6–7 m/s，它可能接近杯口或得分。这里的“overshoot / shortfall / 接近杯口”只是预期现象的 narrative placeholders，我们不声称这些参数对应的精确轨迹已经通过物理验证；最终 bounce 和 landing coordinates 一律由 simulator 生成并校准。

同一段反馈可能被两种 agent 完全不同地使用。Agent 1 把每个三元组记成“失败”或“成功”，继续在动作空间搜索，最后记住某个 6–7 m/s 的 B 动作能打进 x=6 m 的杯子。Agent 2 则把 B 的强反弹、A 的较弱反弹和 C 的明显能量损失联系起来，形成一个可更新的工作 belief：B 相对高 restitution、低 friction，因此同角度下需要比直觉更低的速度。两者最后都可能 success@10=1，但这个结果本身是弱且含混的证据，因为搜索、记忆和物性推断都能导致成功。

每次试验后，simulator 只返回该 episode 指定的一种 feedback channel：none、binary success/failure、terminal coordinate、video 或 oracle state。为了做 paired comparison，各 feedback condition 使用完全相同的 W-017、初始 observation、10 次预算和 harness，唯一变化是 agent 能收到的信息。评测器在后台保存每轮 action、完整 trajectory、bounce/contact points、terminal landing、success、实际发出的 feedback，以及接口允许时的 rationale 和 memory state。完整 trace 用来计算曲线和核对行为；但 agent 只能看到所属条件允许的部分，rationale 也只作为辅助证据，不能因为一段解释听起来合理就认定它真的学会了。

第 10 次后立即 freeze：不再给任何反馈，也不允许针对 probe 重试。Post prediction 可以问另一个未执行过的 tuple，例如 (B, 6.4 m/s, 28°) 在 W-017 中会怎样反弹、最终落在哪里，并要求它和 A、C 的相近动作排序。测试同时覆盖 interpolation 和合理范围内的 extrapolation，且与 interaction trace 严格不重合。若 Agent 2 的预测相对 pre-probe 明显接近 simulator ground truth，而 Agent 1 只会复述成功动作，这比当前任务成功提供了更强的 behavioral evidence：它表明 agent 的行为与学到一个可用于未见动作的 forward model 相一致，但仍不是对内部机制的直接证明。

接着保持同一张材料表、同一几何和同一组隐藏属性，只把杯子从 x=6 m 移到约 x=4.5 m。系统先测一次完全无反馈的 first shot，再给一个极小固定预算，例如 2 次；这个数值也只是待校准的示例。Agent 1 记住的“B 在 6–7 m/s 可打进原杯位”现在很可能失效，因为目标位置已经改变。Agent 2 若真的利用“B 高弹、低摩擦”的 belief，就可以据此为更近的杯位重新选择速度和角度，而不是照抄旧动作。First-shot transfer 因而提供第三层证据：它检查学到的表示是否不仅能预测，还能用于 goal-conditioned action。

整条 evidence hierarchy 可以直接沿 W-017 来解释：

1. **Current success 是弱且含混的证据**：两种 agent 都可能靠不同过程得分。
2. **Accurate unseen-action prediction 是更强的 behavioral evidence**：它要求信息超出已试 action，符合 learned forward model 的行为表现。
3. **First-shot transfer 是表示可用于目标行动的证据**：旧成功动作失效后仍能选出合理新动作，说明信息不只停留在复述层面。
4. **Prediction gain 与 transfer gain 同时出现是中心证据**：两者收敛比任何单项都更有说服力，但仍不直接证明 agent 内部采用了哪一种学习机制。

计分也对应这四层。**Task Improvement** 由 10 次 interaction 中的 success / distance curve 得到，例如 Agent 2 是否更早降低 miss distance。**Prediction Knowledge Gain** 是 post prediction score 减去 pre prediction score；若原指标是 error，先统一方向，让正值代表改善。**Transfer Knowledge Gain** 比较 moved-cup 的 first-shot / tiny-budget performance 与 pre baseline 或匹配 cold start。评测器同时报告原始分、增量和不确定性，而不是压成一句“学会了”。

主图采用二维诊断：x 轴是 task improvement，y 轴是 reusable-knowledge gain，并分别展示 prediction 与 transfer。四个区域提供的是可证伪的行为解释：

- **task 上升、knowledge 持平**：与 action search 或局部记忆一致。
- **task 上升、knowledge 上升**：为 feedback-driven reusable learning 提供更强 behavioral evidence。
- **task 持平、knowledge 上升**：可能学到了 dynamics，但 planning / action selection 没有转成当前任务收益。
- **两者都持平**：在当前 world、预算和 agent system 下，没有观察到反馈被有效使用。

W-017 在数据组织中属于一个 **World Family**：family 规定 hidden-property ranges、geometry 和 target locations；一次具体参数采样与 seed 形成 **World Instance**；同一 instance 配上 feedback mode、预算和 agent system 形成 **Interaction Episode**；episode 再挂接 **Probe Items**。层级就是 **World Family → World Instance → Interaction Episode → Probe Items**。Train / validation / test 按 hidden-property combinations 和 geometry 划分，而不是随机拆 frame；同一 ball ID 在不同 world 中不能固定对应一种材料。每个 split 还要平衡 easy / medium / hard，检查 action feasibility 和目标可达性，并确保 held-out actions 与 interaction trace 不相交、probe 期间不泄露 outcome。

最小可行版本可以先按 **3 种 ball-property regimes × 3 种 geometries × 4 个 target positions × multiple seeds** 生成，并让所有 feedback conditions 在相同 world 上 paired evaluation。这仍是 draft。3×3×4=36 只是参数组合数，乘 seeds 后才是 unique world instances；每个 world 再乘 feedback modes、agent systems 和重复运行，才得到 evaluation episodes。确切规模要等物性范围、budget、seed 数和统计方案确定后再定。

### 附：W-017 紧凑记录示意

~~~json
{
  "world_id": "W-017",
  "hidden_physics": {
    "A": {"reader_name": "wood-like", "e": 0.45, "mu": 0.35, "mass_kg": 0.10},
    "B": {"reader_name": "rubber-like", "e": 0.85, "mu": 0.20, "mass_kg": 0.10},
    "C": {"reader_name": "foam-like", "e": 0.20, "mu": 0.65, "mass_kg": 0.06}
  },
  "geometry": {"type": "2d_ground_bounce", "launch_m": [0, 1], "cup_x_m": 6.0, "gravity": "standard"},
  "action_space": {"speed_mps": [4, 10], "angle_deg": [20, 60]},
  "budget": 10,
  "feedback_mode": "video",
  "pre_probe": [{"action": ["B", 7.5, 32], "feedback_revealed": false}],
  "interaction_trace": [
    {"action": ["B", 8.0, 35], "placeholder_result": "strong_bounce_overshoot"},
    {"action": ["B", 6.5, 32], "placeholder_result": "approaches_or_scores"}
  ],
  "post_prediction_probe": [{"action": ["B", 6.4, 28], "feedback_revealed": false}],
  "transfer_probe": {"cup_x_m": 4.5, "first_shot": true, "tiny_budget": 2},
  "ground_truth": "evaluator_only; generated_and_calibrated_by_simulator"
}
~~~

表中的材料称呼、隐藏物性、完整轨迹和 ground truth 只对 reader / evaluator 可见；所有参数与 placeholder results 都是 illustrative draft，正式使用前必须经过 simulator validation。

我们故意在测试时把题目换掉，让 agent 不能照抄刚才成功的动作；如果它仍然表现得更好，才说明它从反馈里学到了可以复用的东西。
