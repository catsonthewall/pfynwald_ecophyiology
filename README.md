# Pfynwald 遥感实验复现包

本练习使用真实公开的 Sentinel-2、Landsat、ESA WorldCover 和 Pfynwald 现场数据，练习反射率换算、光谱指数、地表温度产品、质量筛选、时间与空间匹配及结果解释。包含已经运行的参考输出；安装依赖后，可以离线重新生成。

本仓库仅用于基于公开数据的学习与方法复现，不代表 EPFL 或 WSL 的官方认可或背书。

**先打开 `docs/START_HERE.html`。** 浏览器可直接打开这份说明，无需启动服务器。完整实验流程、主要结果和局限见说明及随附实验手册。

## 最快的复现步骤

将 ZIP 完整解压。以下命令在包含本文件、`run_all.py` 和 `requirements.txt` 的文件夹中执行。建议使用 **Python 3.12** 和独立虚拟环境。

macOS 或 Linux：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python verify_inputs.py
python run_all.py
```

Windows PowerShell：

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe verify_inputs.py
.venv\Scripts\python.exe run_all.py
```

安装依赖通常需要网络。安装完成后，上述校验和分析使用包内数据，不需要登录数据平台、API 密钥或重新下载卫星影像。`verify_inputs.py` 仅使用 Python 标准库，因此也可以在安装科学计算依赖之前执行。

`run_all.py` 会重新生成 `outputs/` 下的分析文件。若要保留自己的修改或原有结果，请先复制整个解压文件夹，再运行。

## 应该看到什么

1. `verify_inputs.py` 检查卫星资产清单及现场子集清单中的文件大小和 SHA-256。任何缺失或不一致都会返回非零退出码。清单保存的完整 EnviDat 原始 ZIP 哈希属于历史来源记录；这些原始 ZIP 未打包，程序不会将其误报为本次验证通过的文件。
2. `run_all.py` 处理卫星反射率与质量标记，计算 NDVI、NDMI、NDRE 和 Landsat 地表温度，生成描述性统计。
3. 程序处理现场质量标记、单位和十分钟聚合，输出三种未确认时区假设下的过境匹配敏感性。
4. 查看 `outputs/figures/` 中的图、`outputs/tables/` 中的卫星统计、`outputs/field/` 中的现场表和审计记录。GeoTIFF 输出可以在 QGIS 中打开。

## 目录说明

| 路径 | 内容 |
|---|---|
| `config.json` | 本次练习声明的范围和筛选阈值 |
| `data/satellite/` | 卫星裁剪数据、来源元数据和资产校验清单 |
| `data/field/` | 2024 年 7 月 15–21 日现场子集、原始单位和说明 |
| `scripts/` | 实际处理和制图代码 |
| `outputs/` | 已执行的参考输出及重新运行的输出 |
| `docs/START_HERE.html` | 实验入口和解释说明 |
| `verify_inputs.py` | 无第三方依赖的输入完整性检查 |
| `run_all.py` | 离线运行整套处理 |

## 必须保留的结果解释

- **严格 Landsat 结果为空是本次真实结果。** 包内八景影像在预设 2 K 产品温度不确定性筛选下均没有保留的分析像元。不要把空值补成零温度，也不要为了得到漂亮曲线而悄悄放宽阈值。文件名含 `baseQA_CONTEXT` 的内容是明确分开的补充教学背景结果，并未通过严格不确定性筛选。
- **2024 年 7 月 21 日 Landsat 核心范围被云污染。** 它无法和这一周现场数据构成合格的热红外验证对。7 月 19 日 Sentinel-2 可提供光学背景，但 Sentinel-2 没有热红外波段，不能拿它直接验证树冠温度。
- **现场时区尚未确认。** 保留 `source_time_naive`，对 UTC、固定 UTC+1、UTC+2 三种假设做敏感性比较。这个检查不会证明哪种时区正确。十分钟现场聚合区间的标签含义也需要确认。
- **500 米圆形范围是景观分析缓冲区，不是实验样地边界。** 包内没有精确树冠轮廓、热辐射计视场或处理地块边界。Landsat 的 30 米产品网格不意味着具有独立的 30 米原生热红外信息。
- **光谱指数不是直接的生理测量。** NDMI、NDRE 不能直接换算为叶水势、气孔导度或树木健康评分。现场可选生理文件实际只有叶水势，单位 bar 转 MPa 乘 0.1，并保留原始负号。
- **重复观测不是独立样本。** 15 个传感器和许多分钟记录，不能把一个卫星日期扩展成数百个独立卫星训练样本。空气参考来自一个上方气象站或条件分组的冠层内聚合值，并非每棵树独立配对的空气温度。

本包用于可复现的方法练习和面试展示。报告时可说明自己完成了哪些质量控制与尺度匹配检查；不应将它表述为已经识别出干旱因果效应、建立森林脆弱性模型或完成正式卫星温度验证。

## 来源和引用

现场子集原始作者、DOI、CC-BY 4.0 许可及筛选方式保存在 `data/field/README.md` 与 `data/field/manifest.json`。卫星资源来源保存在 `data/satellite/manifest.json`，方法来源见实验说明。使用或分享结果时，保留这些来源与日期筛选说明。
