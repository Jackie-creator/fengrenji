# Few-shot 示例与评测数据格式

本目录存放注入 prompt 的 few-shot 示例（建议 2–3 组，少而精）。评测集用同样的格式，但**放在仓库外或单独目录**，不要和 few-shot 示例混用。

## 目录格式（平台中立）

```
examples/                      # 或任意评测集目录
├── sample_01/
│   ├── front.jpg              # 任意数量照片，文件名不限
│   ├── inside.jpg
│   └── expected.json          # 人工标注的标准答案（AnalysisResult schema）
└── sample_02/
    └── ...
```

- 照片支持 jpg / png / webp / gif；
- `expected.json` 必须能通过 `app/vision/schemas.py` 的 Pydantic 校验；
- 没有 `expected.json` 的子目录会被跳过（可放置未完成的标注）。

## expected.json 示例

```json
{
  "category": "bifold_wallet",
  "confidence": 0.95,
  "estimated_dimensions_mm": {"width": 110, "height": 90, "depth": 15},
  "scale_reference_detected": true,
  "structure": {
    "card_slots_left": 3,
    "card_slots_right": 3,
    "has_bill_compartment": true,
    "has_zipper_pocket": false,
    "edge_finish": "burnished"
  },
  "notes_for_user": "标准二折短夹，左右各 3 个卡位，油边收边。",
  "closest_template": null
}
```

## 用途

1. **Few-shot**：本目录有样本时，`ClaudeVisionAnalyzer` 自动把它们作为示例对话注入 prompt（含 prompt caching，重复调用时示例图片按缓存价计费）。
2. **评测**：`python scripts/evaluate.py <评测集目录>` 输出品类准确率、卡位误差等指标——改 prompt 后跑一遍即知效果好坏。
3. **将来微调**：此格式与各平台视觉微调的训练数据（图片 + 指令 → JSON 回答 的 JSONL）一一对应，标注积累零浪费。
