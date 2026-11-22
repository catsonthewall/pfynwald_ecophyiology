# 将实验材料上传到 GitHub

## 放在仓库根目录

先选择你要使用的 GitHub 仓库及其公开或私有设置。将本文件夹的**内容**放到该仓库根目录，保留所有子目录；不要额外嵌套一层 `pfynwald-remote-sensing-lab/`。

上传完成后，仓库根目录应直接包含：

- `README.md`、`requirements.txt`、`config.json`。
- `run_all.py`、`verify_inputs.py`、`LICENSE_CODE.txt`。
- `scripts/`、`data/`、`outputs/` 和 `docs/`。
- `.gitignore` 和本说明。

材料包含多个子目录和二进制文件。使用 Git 或 GitHub Desktop 时，将这些内容复制到目标仓库的本地工作目录，检查待提交的文件，再提交并同步到你选定的仓库。如果已有同名文件，先比较内容，避免覆盖其他项目的工作。

`.gitignore` 仅排除本地虚拟环境、缓存、编辑器文件、系统文件和本地环境配置；**包内数据与参考输出需要一并上传**。

## 上传后的检查与复现

在仓库根目录打开终端，先执行不依赖第三方库的完整性检查：

```bash
python verify_inputs.py
```

使用 Python 3.12，按 `README.md` 创建虚拟环境并安装依赖，然后运行：

```bash
python run_all.py
```

查看 `outputs/figures/` 和 `outputs/tables/`。`run_all.py` 会重新生成输出；需要保留自己的修改时，请先备份工作目录。上传本身无需重新获取卫星数据。

## 说明和手册

- 实验入口：`docs/START_HERE.html`，下载后可在浏览器中直接打开。
- 中文手册 PDF：`docs/Pfynwald_Remote_Sensing_Manual_CN.pdf`。
- 中文手册 Word：`docs/Pfynwald_Remote_Sensing_Manual_CN.docx`。
- 遥感方法说明：`docs/SATELLITE_METHOD_NOTES_EN.md`。

## 保留来源和解释

代码许可见 `LICENSE_CODE.txt`；现场数据作者、DOI、CC BY 4.0 许可及日期筛选记录见 `data/field/README.md` 和 `data/field/manifest.json`。卫星来源见 `data/satellite/manifest.json`，WorldCover 和其他来源说明见方法文档。分享时保留这些说明和校验清单。

这是使用公开数据的学习与方法复现材料，不代表 EPFL 或 WSL 的官方认可或背书。严格 Landsat 筛选为空、现场时区未确认等已记录限制同样属于结果，应与数据和图表一起保留。
