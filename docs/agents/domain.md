# Domain Docs

工程技能在探索代码库时，如何消费本仓库的领域文档。

## 探索前，先读这些

- **`CONTEXT.md`**（项目根目录），或者
- **`CONTEXT-MAP.md`**（如果存在的话）——它指向每个上下文各自的 `CONTEXT.md`。阅读与当前主题相关的每一份。
- **`docs/adr/`** — 读与你要工作的领域相关的 ADR。在多上下文仓库中，还需检查 `src/<context>/docs/adr/` 中的上下文级决策。

如果以上文件都不存在，**静默继续**。不要提示它们缺失，也不要主动建议创建。生产者技能（`/grill-with-docs`）会在术语或决策真正确定时懒加载创建它们。

## 文件结构

单一上下文仓库（大多数仓库）：

```
/
├── CONTEXT.md
├── docs/adr/
│   ├── 0001-event-sourced-orders.md
│   └── 0002-postgres-for-write-model.md
└── src/
```

多上下文仓库（根目录存在 `CONTEXT-MAP.md`）：

```
/
├── CONTEXT-MAP.md
├── docs/adr/                          ← 系统级决策
└── src/
    ├── ordering/
    │   ├── CONTEXT.md
    │   └── docs/adr/                  ← 上下文级决策
    └── billing/
        ├── CONTEXT.md
        └── docs/adr/
```

## 使用术语表的词汇

当你的输出中命名一个领域概念（在 Issue 标题、重构提案、假设、测试名称中），使用 `CONTEXT.md` 中定义的术语。不要偏离到术语表明确避开的同义词。

如果你需要的概念不在术语表中，这是一个信号——要么你在发明项目不使用的语言（重新考虑），要么确实存在缺口（记下来给 `/grill-with-docs`）。

## 标记 ADR 冲突

如果你的输出与现有 ADR 相矛盾，明确标注而不是静默覆盖：

> _与 ADR-0007（事件溯源订单）矛盾——但值得重新讨论，因为……_
