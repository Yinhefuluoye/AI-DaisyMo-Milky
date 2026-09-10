<div align="center">
  <img src="./icon.png" alt="AI-DaisyMo Logo" width="128"/>
  <h1>AI 墨小菊 (AI-DaisyMo)</h1>
  <p>《三色绘恋》墨小菊 同人专属伴侣系统</p>
  <p>
    <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white" alt="Python 3.10+"/>
    <img src="https://img.shields.io/badge/Pygame-2.5+-4B8BBE?style=flat" alt="Pygame"/>
    <img src="https://img.shields.io/badge/Platform-Windows-0078D6?style=flat&logo=windows" alt="Platform"/>
    <img src="https://img.shields.io/badge/License-Non--Commercial-orange?style=flat" alt="Non-Commercial"/>
  </p>
</div>

---

## 📌 核心声明 (Notice & License)

1. **同人非商业声明**：本项目为《三色绘恋》（*Tricolour Lovestory*）同人非盈利开源项目，仅供技术交流与粉丝相伴使用，严禁用于任何商业营利或变相收费行为。
2. **知识产权归属**：项目中使用的立绘、背景、CG、BGM 音频等游戏视听资产版权归原制作方 **绘恋制作组 (HL-Galgame)** 所有。如有侵权，请联系维护者下架处理。
3. **安全与隐私保护**：API Key 仅保存在用户本机的 `assets/config.json` 中，绝不上报云端，工程已配置 `.gitignore` 严防敏感凭据与本地对话历史误提交。
4. **生成内容免责**：AI 墨小菊的对白由第三方大模型实时生成，内容受提示词与模型特性影响，不代表原版权方及本项目开发者立场。

---

## ✨ 核心特性

- 🎨 **原汁原味和纸风格 UI**：还原官方三层底框视效，配备 2x SSAA 超采样进入主键、平滑消融转场、打字机动效与回忆（Backlog）珍藏分栏。
- 🧠 **原案台词深度蒸馏**：依托 6,397 句官方剧本原案语料提炼心智机制，还原傲娇长姐防御、生活温存主义与真诚基准线。
- ⚡ **深度思考（Reasoning）智能切换**：自动检测模型是否具备思考推理能力（如 `mimo-v2.5`、`deepseek-reasoner` 等），提供开启/关闭/置灰禁用三态；关闭时显式降低延迟，实现 2 秒级极速对白响应。
- 🎙️ **自适应 TTS 语音合成**：内置双协议语音引擎，全面兼容 OpenAI 规范与小米 MiMo 拟真少女音色。
- 🌐 **多主流大模型预设**：一键切换 小米 MiMo、DeepSeek、Claude、OpenAI、Gemini、通义千问等主流服务商与自定义端点。

---

## 🚀 快速启动

### 方式一：Windows 一键启动（推荐）

1. 确保电脑已安装 [Python 3.10 或更高版本](https://www.python.org/downloads/)（**安装时务必勾选 "Add python.exe to PATH"**）。
2. 下载/克隆本仓库后，**双击根目录下的 `run.bat`**：
   - 脚本会自动检测环境、创建虚拟环境并高速安装必要依赖，随后自动启动游戏。

### 方式二：手动命令运行

```bash
# 1. 安装核心依赖
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 2. 启动游戏
python DaisyMo.py
```

### 首次配置指南
首次启动后，在主界面点击右下角 **「设置」**（或进入游戏后点击右下角 **「SYSTEM」**），填入所选服务商的 API Key 并点击 **「保存配置」** 即可畅快对话。下次启动自动读取配置，无需重复填写。

---

## 🎮 常用操作与快捷键

| 操作 / 快捷键 | 功能说明 |
| :--- | :--- |
| `1` | 随机切换墨小菊表情 |
| `2` | 随机切换墨小菊服装姿势 |
| `3` | 随机切换场景背景 |
| `SPACE` / 鼠标左键 | 推进剧情 / 快速显示全部对白 |
| `ESC` | 退出全屏 / 关闭弹窗 |
| 对话界面右下角按钮 | **AUTO** 自动播放 / **LOG** 查看历史与珍藏 / **SYS** 核心设置 |

---

## 👥 贡献与致谢

- **项目发起 / 维护**：[Rosysuki](https://github.com/Rosysuki), [Lulianovic](https://github.com/Lulianovic)
- **原作致敬**：感谢 **绘恋制作组** 创作的《三色绘恋》与生动鲜活的墨小菊。
- 欢迎提交 Issue 与 Pull Request 共同交流完善！
