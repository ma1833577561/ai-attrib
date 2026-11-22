# 发布清单（Publish checklist）

仓库已经整理好，并且已在本地 `~/projects/ai-attrib` 完成 `git init` + 首次提交；**还没有推到 GitHub**。等你确认后从第 2 步开始。

## 0. 确认本地内容

```bash
cd ~/projects/ai-attrib       # 已从交接包复制出来的工作副本
python3 -m unittest discover -s tests -v   # 应为 32 passed
./scripts/scan-sensitive.sh                # 应为 clean
```

## 1. 身份确认（首次提交已完成）

首次提交已用个人身份完成。换机器或重来一遍时：

```bash
cd ~/projects/ai-attrib
git config user.name  "你的名字"
git config user.email "你的个人邮箱"          # 千万不要是公司邮箱
git log --format='%an <%ae>' | sort -u        # 应该只有你一个
git add -A && git commit -m "feat: ai-attrib 0.1.0 - measure declared AI involvement in git history"
```

## 2. 建远程仓库并推送

没有 `gh` CLI 时，在 GitHub 网页 New repository：名字 `ai-attrib`，**public**，不要勾选初始化 README/License/gitignore（本地已有）。

```bash
git remote add origin git@github.com:ma1833577561/ai-attrib.git
git push -u origin main
```

有 `gh` 时一条命令：

```bash
gh repo create ai-attrib --public --source=. --remote=origin --push
```

## 3. 仓库元数据（招聘方 3 秒内看到的东西）

**Description（一句话）：**

> Read-only git analytics that compares AI-declared commits against human ones: change radius, test coverage habits, rework rate, code smells.

**Topics（复制粘贴）：**

```
git python developer-tools ai coding-agents metrics code-quality static-analysis cli
```

## 4. README 徽章（推送后 CI 跑过一次再加）

```markdown
[![ci](https://github.com/ma1833577561/ai-attrib/actions/workflows/ci.yml/badge.svg)](https://github.com/ma1833577561/ai-attrib/actions/workflows/ci.yml)
![python](https://img.shields.io/badge/python-3.9%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)
```

放在 README 第一行标题下面。

## 5. 置顶（Pinned）

只置顶这一个就够。第二个位置留给「能跑通的 Demo 项目」，第三个位置留给「一个 merged PR 的开源贡献」。
**不要**为了填满 6 个位置放练习仓库。

## 6. 发布后 30 分钟内自查

- [ ] 主页打开，仓库描述 + Topics 正确
- [ ] CI 徽章是绿色（不是 `no status`）
- [ ] 在无 Python 环境的机器/容器里 `pip install -e . && ai-attrib demo` 能跑通
- [ ] `git log --format='%an <%ae>'` 全是个人邮箱
