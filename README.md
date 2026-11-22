# ai-attrib

> 用 git 提交历史，回答一个 2026 年每个工程团队都在问、但几乎没人敢量化的问题：
> **AI 到底改了多少代码，改得比人更好还是更糟？**

一行命令，只读本地仓库，不上传任何数据，输出一份可以直接贴在周报/晋升材料/技术分享里的对比报告。

```bash
ai-attrib report /path/to/repo --baseline 2024-01-01..2024-12-31 --signals
```

示例输出（伪数据，仅示意格式）：

```
declared AI involvement: 137 commits (23.4% of all)
AI-declared: files/commit p90 = 4, touches tests 31.2%, rework within 14d 9.1%
Human-declared: files/commit p90 = 3, touches tests 22.8%, rework within 14d 14.6%
```

---

## 为什么做这个

关于 AI 编程的说法有两类，都缺少证据：

- 「AI 让效率提升 10 倍」——通常拿不出可比的口径；
- 「AI 写的代码质量差」——通常只是感觉。

这个工具不测「效率」，也不测「质量」。它只做一件可复现的事：**把仓库里的提交按「是否声明 AI 参与」分成两组，在同一时间窗口内用同一套指标做对照**。所有数字都能被任何人用同一条命令重新算出来——这是它唯一的价值主张。

## 它衡量什么

| 维度 | 指标 | 想说明的问题 |
|---|---|---|
| 改动规模 | 每提交文件数 / 行数的中位数与 p90 | AI 是一次改一大片，还是小步快跑 |
| 影响半径 | 每提交涉及模块数、跨 >3 模块占比 | AI 是否倾向于跨层改动，埋下耦合 |
| 工程习惯 | 动测试占比、纯文档占比、fix 提交占比 | AI 提交是否绕过测试 |
| 返工成本 | 14 天内同文件二次 fix 率 | 改动是否稳定 |
| 代码气味 | 新增行里的 `console.log`、空 catch、`as any`、`@ts-ignore`、TODO 等 | 是否存在「先跑通再说」的痕迹 |

每个指标都能在 `--format json` 里拿到原始值，便于接看板或做二次统计。

## AI 提交怎么识别

**靠声明，不靠猜测。** 默认匹配这些提交信息里的 trailer 或标记：

```
Co-authored-by: Claude <noreply@anthropic.com>
Co-authored-by: Copilot <noreply@github.com>
Generated-by: Cursor
[ai-assisted]
🤖
```

常见工具（Claude Code / Copilot / Cursor / Codex / Aider / Devin / Qoder / Windsurf / Cline / Continue）默认都在名单里。团队有自己的约定时：

```bash
ai-attrib report . --ai-pattern '^Assisted-by:\s*our-bot'
```

这是刻意的取舍：**声明的比例是下界，不是估计**。偷偷用 AI 的提交会被算进人类组——报告会因此低估 AI 占比，但不会编造。想缩小误差，只有一条路：让团队养成写 trailer 的习惯。

## 安装与使用

只依赖 Python 3.9+ 和 `git`，没有第三方包。

```bash
git clone https://github.com/ma1833577561/ai-attrib.git
cd ai-attrib

# 方式 A：安装成命令（需要 pip >= 21.3；旧 pip 先 python -m pip install -U pip）
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

# 方式 B：完全不安装，直接用
PYTHONPATH=src python3 -m ai_attrib demo

# 1) 先看效果：内置合成仓库，不需要任何真实数据
ai-attrib demo

# 2) 再看自己的仓库
ai-attrib report /path/to/repo --since 2024-01-01 --until 2024-12-31 --signals

# 3) 想看「引入 AI 前后」的变化，给一个等长基线窗口
ai-attrib report /path/to/repo \
  --baseline 2024-01-01..2024-12-31 \
  --since 2025-01-01 --until 2025-12-31

# 4) 出 JSON 接你自己的看板
ai-attrib report /path/to/repo --format json -o report.json
```

`examples/demo-report.md` 是一份完整样例输出（55 个合成提交），可以先看格式再决定要不要跑。
复现它：`ai-attrib demo -o examples/demo-report.md`（固定随机种子，每台机器结果一致）。

## 输出结构

```
src/ai_attrib/
├── gitio.py        只读地调用 git：日志解析、numstat、-p 新增行
├── attribution.py  AI 声明识别（正则表 + 自定义扩展）
├── metrics.py      指标计算：分位数、模块划分、返工率、代码气味
├── render.py       markdown / json 渲染
├── demo.py         合成仓库，用于自测与演示
└── cli.py          report / demo 两个子命令
```

设计上刻意保持「一层薄壳」：所有逻辑都能被单独 import 做单元测试，CLI 只负责参数与输出。不引入 pandas，不引入 web 框架，不缓存中间结果——目标是十年后还能 `pip install` 就跑。

## 设计取舍

- **只用 `git`，不接 API。** 不碰 GitHub/GitLab token，不读 PR 评论，不联网。代价是拿不到 review 轮次、CI 结果这类信号；收益是任何内网仓库、任何离线环境都能跑，且没有数据外泄风险。
- **按提交分，不按行分。** 逐行追溯 AI  authorship 需要 blame 全仓库，慢且在有 rebase/squash 的仓库里不可靠。按提交分组是粗糙但稳定的口径。
- **报告里不放「结论」，只放对照。** 工具不替你下「AI 更好/更差」的判断，因为同一组数字在两种业务下可以有完全相反的解读。它只保证数字可比。
- **小样本必须警告。** 少于 50 个提交、或单组少于 20 个提交时，报告会自己标注「仅供方向参考」，避免被当成统计结论引用。

## 已知局限

1. 只统计**声明了** AI 参与的提交，是下界。
2. 返工率用「14 天内同文件再次 fix」近似，无法区分「修复回归」和「迭代优化」。
3. 模块划分按路径前 N 段，单仓库多包（monorepo）时建议调 `--module-depth 3`。
4. 不处理 merge 提交（默认排除），大团队 squash 流程下会少算。

## 性能

在一个上万提交（已排除 merge）的真实仓库上：`report` 用时**几十秒**；
加 `--signals`（逐行扫新增代码）在**分钟级**。全程只是本地 `git` 调用，无网络、无缓存文件。

## 开发

```bash
python3 -m unittest discover -s tests -v
```

无 pytest 依赖，纯标准库。CI 在 Python 3.9 / 3.11 / 3.12 三个版本上跑同一套用例。

## 数据与隐私

工具只读本地 git 历史，不联网、不落盘中间结果、不输出作者身份。

本仓库本身也经过脱敏：所有代码为公开发布重写，示例报告由合成提交生成。规则与自检清单见
[docs/DESENSITIZE.md](docs/DESENSITIZE.md)，机械校验脚本：

```bash
./scripts/scan-sensitive.sh     # 发布前必跑：组织名/工单号/企业邮箱/密钥/绝对路径
./scripts/configure.sh --user your-github-handle --email you@example.com --name "Your Name"
```

`configure.sh` 会一次性替换本文档与 `pyproject.toml` 里的账号占位符（fork 后换成你自己的），并把 git 身份写成本仓库局部配置。
完整发布步骤见 [docs/PUBLISH.md](docs/PUBLISH.md)。

## License

MIT，见 [LICENSE](LICENSE)。
