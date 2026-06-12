# LeatherPattern AI

皮具裁剪图纸生成器：上传皮具成品照片，AI 识别品类与结构参数，参数化几何引擎生成毫米级精度的 2D 裁剪图纸（SVG / DXF）。

## 架构

```
照片 ──> Claude API 视觉分析 ──> 结构化 JSON（品类 + 结构参数）
                                      │
用户参数（皮厚/尺寸/收边）──────────────┤
                                      ▼
                          参数化几何引擎（纯代码，确定性）
                          templates: CardHolder / BifoldWallet / ZipperPouch
                                      │
                                      ▼
                            SVG（预览） / DXF（切割） / PDF（打印）
```

**核心原则：AI 只负责理解，几何引擎负责出图。** Claude 的输出永远是结构化 JSON 参数，图纸的每一个坐标都由确定性几何代码计算，保证毫米级精度与可复现性。

## 当前进度

- ✅ **Milestone 1**：几何引擎核心（`geometry/core.py`）+ `CardHolder` 模板 + SVG 导出 + CLI + 单元测试
- ⬜ Milestone 2：`BifoldWallet` / `ZipperPouch` 模板 + DXF 导出
- ⬜ Milestone 3：Claude 视觉分析层
- ⬜ Milestone 4：FastAPI 端点 + React 前端
- ⬜ Milestone 5：PDF 打印导出与打磨

## 本地启动

```bash
cd backend
pip install -e ".[dev]"     # Python 3.11+

# 生成 3 卡位卡包图纸（1.2mm 皮厚）
python -m app.cli card_holder --slots 3 --leather 1.2 -o card_holder.svg

# 其他参数
python -m app.cli card_holder --slots 2 --leather 1.0 --seam 4 --stagger 14 \
    --pitch 3.85 --edge folded -o out.svg

# 运行测试
python -m pytest
```

生成的 SVG 以 1mm = 1 SVG 单位绘制，含 10mm 网格背景与 50mm 比例尺；打印后请用尺校验比例尺长度。

## 领域规则（几何引擎实现）

所有规则的常量定义在 `backend/app/geometry/core.py`：

| 规则 | 默认值 | 说明 |
|---|---|---|
| 缝份 | 3.5mm（3–5 可配） | 裁片轮廓 = 净尺寸（缝线尺寸）+ 缝份；缝线以虚线标出 |
| 皮厚补偿 | 每包覆一层 `t×π/2` / 每条缝合边 | 外层裁片包覆内层叠层时按弯折弧长加宽；宽度方向左右两条缝合边各计一次，底边一次 |
| 折边余量 | 8mm | 折边收边时每条边在缝份之外再外扩 8mm，四角画 45° 切角标记；油边不外扩 |
| 卡位阶梯 | 露出 12mm（10–14 可配） | 卡位片宽 = 85.6 + 2×缝份 + 1.5 活动余量；顶层卡位片高 40mm，第 i 层高 = 40 + (i-1)×露出量 |
| 打孔标记 | 孔距 4mm（法斩 3.85） | 沿缝线标出打孔参考线起止圆点 |
| 拉链口 | 标称长 + 6mm，槽宽 4mm | 两端半圆收口（M2 实现） |
| 二折折叠区 | 总叠层厚度 × 3（经验系数，可配） | 外壳长 = 2×内衬宽 + 折叠区补偿（M2 实现） |

卡包结构模型：前后主体片相同尺寸，内部 1–3 个卡位片底边对齐叠放，靠腔体侧最短、逐层升高；主体净高 = 露出量×(n-1) + 卡高 54 + 顶部留边 10，保证卡片不露出主体。

## 项目结构

```
backend/
├── app/
│   ├── main.py                  # FastAPI 入口（M4）
│   ├── cli.py                   # 命令行出图
│   ├── geometry/core.py         # 通用几何：偏移、皮厚补偿、折边切角、打孔线
│   ├── geometry/templates/      # card_holder.py（M2 补充另外两个模板）
│   └── export/svg_export.py     # SVG 导出（网格 + 比例尺 + 标注）
└── tests/                       # pytest，含手算对照注释
```

环境变量见 `.env.example`（M3 起需要 `ANTHROPIC_API_KEY`）。
