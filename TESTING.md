# 手把手验收测试指南

覆盖 Milestone 1–3 的全部验收点。预计耗时：环境准备 5 分钟，M1/M2 验收 10 分钟，M3 真图验收 10 分钟。

---

## 第 0 步：环境准备（一次性）

需要 Python 3.11 或更高（`python3 --version` 确认）。

```bash
git clone <仓库地址> fengrenji
cd fengrenji
git checkout claude/nifty-hamilton-vk50g3

cd backend
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

✅ **通过标准**：安装无报错。

---

## 第 1 步：跑单元测试（1 分钟）

```bash
cd backend
python -m pytest
```

✅ **通过标准**：最后一行显示 `88 passed`，没有 failed/error。

---

## 第 2 步：验收 M1 — 卡包图纸

### 2.1 生成默认图纸

```bash
python -m app.cli card_holder --slots 3 --leather 1.2 -o card_holder.svg
```

用浏览器打开 `card_holder.svg`（双击或拖入 Chrome）。

✅ **逐项核对**：
- [ ] 共 4 个裁片：主体片（标注 ×2）+ 卡位片 1/2/3
- [ ] 主体片标注「裁切 105.41×100.65 mm」（与手算一致，手算过程见 `tests/test_card_holder.py` 文件头注释）
- [ ] 卡位片 1 标注「裁切 94.1×47 mm」
- [ ] 实线 = 裁切线；蓝色虚线 = 缝线（左/下/右三边，顶边开口无缝线）；缝线两端有蓝色打孔圆点；绿色箭头 = 纤维方向
- [ ] 背景有浅灰 10mm 网格；左下角有 50mm 比例尺

### 2.2 打印比例验证（验收标准里的关键项）

浏览器打开 SVG → 打印（缩放选 100%/实际大小）→ 用尺量比例尺线段。

✅ **通过标准**：比例尺实测 50mm（±0.5mm 内算打印机误差）。

### 2.3 折边模式

```bash
python -m app.cli card_holder --edge folded -o card_holder_folded.svg
```

✅ **通过标准**：每个裁片比油边版每边大 8mm，四角出现橙色 45° 切角标记。

---

## 第 3 步：验收 M2 — 短夹、零钱包、DXF

### 3.1 二折短夹

```bash
python -m app.cli bifold_wallet -o bifold.svg
```

✅ **核对**：9 个裁片；外壳标注「裁切 218.22×102.54 mm」；外壳中部有两条灰色点划折线（间距 14.4mm 折叠区）；内衬注明「靠书脊一侧的竖边不缝合」。

不对称参数测试：`python -m app.cli bifold_wallet --slots-left 3 --slots-right 1 -o bifold_31.svg`，外壳应变窄（净长 ≈ 203.68mm）。

### 3.2 拉链零钱包

```bash
python -m app.cli zipper_pouch -o pouch.svg
python -m app.cli zipper_pouch --style top_seam -o pouch_seam.svg
```

✅ **核对**：开窗版前片上部有 106×4mm 两端半圆长窗 + 窗外一圈缝线；夹缝版无开窗、顶边中段有拉链标记线。

### 3.3 DXF（LibreCAD 验收）

```bash
python -m app.cli card_holder --format dxf -o card_holder.dxf
```

LibreCAD 打开后：
- [ ] 菜单 Edit → Current Drawing Preferences → Units 显示 Millimeter
- [ ] 图层面板有 CUT / STITCH / MARK / TEXT 四层，可分别开关
- [ ] 用测量工具（Tools → Info → Distance）量主体片宽：≈105.41mm

---

## 第 4 步：验收 M3 — 视觉分析（需要 API key 和真实照片）

### 4.1 配置 key

```bash
cd backend
cp ../.env.example .env
# 编辑 .env，填入 ANTHROPIC_API_KEY=sk-ant-你的key
```

### 4.2 准备照片

拿一个真实卡包/短夹/拉链零钱包，拍 3–4 张：外观正面、打开后的内部、侧面；**其中一张在旁边放一张银行卡**（测尺寸估算）。手机照片直接用即可（jpg/png）。

### 4.3 运行分析

```bash
python scripts/analyze_example.py 正面.jpg 内部.jpg 侧面带卡.jpg
```

✅ **逐项核对输出 JSON**：
- [ ] `category` 与实物相符，`confidence` 合理（清晰照片应 >0.7）
- [ ] `card_slots_left/right` 数量与实物一致或接近
- [ ] 放了银行卡的那组：`scale_reference_detected: true` 且 `estimated_dimensions_mm` 有数值、误差在 ±10% 内
- [ ] **不放参照物再跑一次**：尺寸字段必须全为 `null`（验证"不许编造尺寸"）
- [ ] `notes_for_user` 是通顺中文，且诚实说明不确定处
- [ ] 整个流程 30 秒内返回

### 4.4 边界测试（建议）

拍一个不支持的品类（如长夹、钥匙包、随便一个包）：

✅ **通过标准**：`category: "unsupported"`，`closest_template` 给出最接近的模板，notes 用中文说明暂不支持。

### 4.5 评测脚本（可选，建议积累后常态化）

```bash
mkdir -p ~/lp_eval/sample_01
# 放入照片 + 按 app/vision/examples/README.md 格式写 expected.json
python scripts/evaluate.py ~/lp_eval
```

✅ **通过标准**：输出每组 ✓/✗ 明细和汇总（品类准确率、卡位平均误差等）。

---

## 常见问题排查

| 现象 | 原因与处理 |
|---|---|
| `ANTHROPIC_API_KEY is not set` | `.env` 没放在 `backend/` 目录下，或 key 名拼错 |
| `authentication_error` (401) | key 无效/已吊销，去 Anthropic Console 重新生成 |
| `ModuleNotFoundError: app` | 没在 `backend/` 目录下运行命令 |
| `pip install` 装 shapely 失败 | 升级 pip：`pip install -U pip`，或确认 Python ≥3.11 |
| SVG 中文标注显示为方框 | 系统缺中文字体，不影响几何精度；浏览器一般正常 |
| DXF 文字层乱码 | TEXT 层是英文标注，正常；切割前可直接关闭该层 |
| 分析超时 | 照片过大（M5 会做自动压缩），先手动压到 2000px 以内 |
