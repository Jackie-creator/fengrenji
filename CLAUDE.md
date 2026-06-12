# LeatherPattern AI — 项目记忆

皮具裁剪图纸生成器 MVP。上传皮具照片 → AI 识别结构参数（JSON）→ 参数化几何引擎生成毫米级 SVG/DXF 图纸。

## 不可违背的架构铁律

- **AI 只负责理解，几何引擎负责出图。** 模型输出止步于 Pydantic 校验的 JSON 参数（`app/vision/schemas.py`），图纸的每一个坐标都由确定性代码计算。绝不让 AI 生成坐标或 SVG。
- 模板驱动：3 个品类 = 3 个参数化模板类（CardHolder / BifoldWallet / ZipperPouch）。
- 所有几何计算必须有单元测试；关键尺寸要在测试注释里写手算过程。
- 无数据库，MVP 无状态。

## 进度（按 Milestone 验收制）

- ✅ M1 几何引擎 + CardHolder + SVG + CLI（已验收）
- ✅ M2 BifoldWallet + ZipperPouch + DXF（已验收）
- ✅ M3 视觉分析层（工程部分已代测通过；真实照片验收待用户本地完成）
- ⬜ M4 FastAPI 三端点（/analyze /generate /export）+ Vite+React+TS 前端
- ⬜ M5 打磨：PDF 1:1 分页打印、图片压缩(≤2000px)、错误处理、README 完善

## 已确认的领域规则（与产品负责人逐条确认过，勿自行更改）

- 缝份默认 3.5mm（3–5 可配）；"净尺寸"= 缝线到缝线，裁切 = 净 + 缝份。
- 皮厚补偿：包覆 d 层 → **每条缝合边**各加 d×t×π/2（宽度方向左右各一次，底边一次）。
- 二折折叠补偿 = **单侧**内部层数(内衬+卡位) × t × 3（系数可配 `BIFOLD_FOLD_COMPENSATION_FACTOR`）。
- 卡位：露出量默认 12mm（10–14）；顶层卡位片高 40mm；第 i 层高 = 40+(i-1)×露出量；主体净高 = 露出量×(n-1)+54+10（保证卡片不露头）。
- 折边：缝份之外再外扩 8mm，四角 45° 切角标记；缝份沿全周统一外扩（开口边也保留作修边量）。
- 钞票基准：欧元 77mm 高 + 5mm 余量（可配）；钞票仓 = 外壳与内衬之间，不单独出裁片。
- 拉链：槽长 = 标称 + 6mm，宽 4mm，两端半圆；支持开窗式（默认）与顶边夹缝式。
- 打孔：孔距默认 4mm（法斩 3.85），只标缝线起止圆点。
- 图纸：1mm = 1 SVG 单位，5mm 出血，10mm 网格，50mm 比例尺；DXF `$INSUNITS=4`，CUT/STITCH/MARK/TEXT 分层。
- 视觉模型：`claude-sonnet-4-6`；无参照物时尺寸必须返回 null，严禁编造。

## 路线图共识（来自竞品评审讨论）

- M5 追加：皮料参数档案（LeatherProfile presets）、材料用量/缝线长度估算、图纸参数指纹。
- M5 做 edge-segment 重构（"边"从矩形四边枚举升级为轮廓分段），为不规则形状铺路；schema 已预留 `outline_hint`。
- Post-MVP backlog：排料 nesting、转角落孔规则、透视校正（单应变换）+ CV 轮廓提取、数据驱动模板。
- 视觉层保持可插拔（`vision/base.py`），将来可换微调模型（如 Microsoft Foundry 上的视觉微调）；标注数据用 `app/vision/examples/README.md` 的平台中立格式积累。

## 工作约定

- 每个 Milestone 开始前先列实现计划要点，确认后写代码；完成后停下等验收。
- 领域规则有歧义时不要自行拍板，停下来问。
- 与用户沟通用中文，代码注释用英文。
- 验收手册见 `TESTING.md`。

## 常用命令

```bash
cd backend
pip install -e ".[dev]"
python -m pytest                                            # 全部测试
python -m app.cli card_holder --slots 3 --leather 1.2 -o out.svg
python -m app.cli bifold_wallet --format dxf -o out.dxf
python scripts/analyze_example.py 照片1.jpg 照片2.jpg        # 需 .env 中 ANTHROPIC_API_KEY
python scripts/evaluate.py <标注数据集目录>
```
