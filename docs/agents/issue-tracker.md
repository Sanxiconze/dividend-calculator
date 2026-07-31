# Issue tracker: GitHub

Issues 和 PRD 存放在 GitHub Issues（`Sanxiconze/dividend-calculator`），通过 `gh` CLI 执行所有操作。

## 常用命令

- **创建 Issue**：`gh issue create --title "..." --body "..."`。多行正文使用 heredoc。
- **查看 Issue**：`gh issue view <number> --comments`，通过 `jq` 过滤评论并获取标签。
- **列出 Issue**：`gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'`，可配合 `--label` 和 `--state` 过滤。
- **评论 Issue**：`gh issue comment <number> --body "..."`
- **添加/移除标签**：`gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **关闭 Issue**：`gh issue close <number> --comment "..."`

仓库信息从 `git remote -v` 自动推断 — `gh` 在 clone 目录内执行时会自动识别。

## 当技能说"发布到事务跟踪器"

创建 GitHub Issue。

## 当技能说"获取相关工单"

执行 `gh issue view <number> --comments`。
