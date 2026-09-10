<div align="center">
  <img src="./icon.png" alt="AI-DaisyMo Logo" width="128"/>
  <h1>AI 墨小菊 (AI-DaisyMo)</h1>
  <p>《三色绘恋》墨小菊 同人交互程序</p>
  <p>
    <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white" alt="Python 3.10+"/>
    <img src="https://img.shields.io/badge/Pygame-2.5+-4B8BBE?style=flat" alt="Pygame"/>
    <img src="https://img.shields.io/badge/OpenCV-4.8+-5C3EE8?style=flat&logo=opencv&logoColor=white" alt="OpenCV"/>
    <img src="https://img.shields.io/badge/Platform-Windows-0078D6?style=flat&logo=windows" alt="Platform"/>
    <img src="https://img.shields.io/badge/License-Non--Commercial-orange?style=flat" alt="Non-Commercial"/>
  </p>
</div>

本项目 Fork 自 [Rosysuki/AI-DaisyMo](https://github.com/Rosysuki/AI-DaisyMo)，基于原项目的概念原型对底层渲染管线、交互界面与模型接入层进行了全面重构与二次开发。

---

## 项目声明

1. **同人非商业用途**：本项目为《三色绘恋》（Tricolour Lovestory）同人非盈利项目，仅供技术交流与学习使用，严禁用于任何商业盈利或变相收费行为。
2. **知识产权归属**：项目中使用的立绘、背景、CG、音频等游戏视听资产版权归原制作方 **绘恋制作组 (HL-Galgame)** 所有。如有侵权，请联系维护者下架处理。
3. **数据与隐私安全**：API Key 仅保存在用户本地的 `assets/config.json`，不经过任何第三方服务器中转。项目已配置 `.gitignore` 隔离敏感配置与本地运行记录。
4. **生成内容免责**：交互对白由第三方大语言模型根据设定提示词实时生成，不代表原制作方及本项目开发者的观点与立场。

---

## 核心特性

- **界面视觉还原**：重构官方三层底框样式，支持 2x SSAA 抗锯齿超采样进入主键、消融转场与回忆（Backlog）珍藏分栏。
- **语料蒸馏心智设定**：基于 6,397 句官方剧本原案对话提炼角色提示词，规范语气节律与动作表情映射。
- **深度思考能力适配**：自动识别模型是否具备推理能力（如 mimo-v2.5、deepseek-reasoner 等），支持开启、关闭与置灰禁用三态；关闭时显式降低延迟，实现 2 秒级响应。
- **TTS 语音合成支持**：内置双协议适配器，兼容标准 OpenAI 协议与小米 MiMo 语音端点。
- **多模型服务商接入**：提供小米 MiMo、DeepSeek、Claude、OpenAI、Gemini、通义千问等服务商预设及自定义端点配置。

---

## 运行方式

### 方式一：下载 Release 运行包（推荐）

前往项目的 [Releases 页面](https://github.com/Yinhefuluoye/AI-DaisyMo-Milky/releases) 下载最新发布的绿色整合包，解压后直接运行可执行程序。

### 方式二：从源码运行（可选）

环境要求：Windows，[Python 3.10+](https://www.python.org/downloads/)（安装时勾选 "Add python.exe to PATH"）。

- **脚本启动**：双击运行根目录下的 `run.bat`（自动检测环境、创建虚拟环境并安装必要依赖）；
- **手动启动**：
  ```bash
  pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  python DaisyMo.py
  ```

---

## 首次配置

首次进入游戏后，在主界面点击「设置」（或在对话中点击右下角「SYSTEM」），选择服务商并填写对应的 API Key，点击「保存配置」即可生效。配置保存在本地，下次启动自动读取。

---

## 常用操作与快捷键

| 按键 / 操作 | 功能 |
| :--- | :--- |
| `1` | 切换立绘表情 |
| `2` | 切换服装动作 |
| `3` | 切换场景背景 |
| `SPACE` / 鼠标左键 | 推进对话 / 快速显示文本 |
| `ESC` | 退出全屏 / 关闭弹窗 |
| 界面按钮 | **AUTO** 自动播放 / **LOG** 回忆记录 / **SYS** 系统设置 |

---

## 当前版本状态 (v0.1)

目前底层代码已按标准协议接入多家模型与语音服务，实际测试覆盖情况如下：

### 1. 大模型 (LLM) 兼容性

| 服务商 | 模型示例 | 接入方式 | 实测状态 | 说明 |
| :--- | :--- | :--- | :--- | :--- |
| **小米 MiMo** | mimo-v2.5 | 官方兼容接口 | **已充分测试** | 支持深度思考开关，关闭思考后响应调优至 2 秒级 |
| **DeepSeek** | deepseek-chat | 官方兼容接口 | **基础验证** | 基础对话流程已调通 |
| **OpenAI** | gpt-4o / o1-mini | 官方接口 | **协议适配** | 已完成接口逻辑与参数适配，未全量实机验证 |
| **Claude** | claude-3-7-sonnet | Anthropic 协议 | **协议适配** | 已适配鉴权头与数据格式，未全量实机验证 |
| **通义千问 / 腾讯混元 / 百度文心** | qwen-plus / hunyuan / ernie | 兼容接口 | **未实机测试** | 仅根据官方开放平台规范配置默认端点与模型 |
| **自定义端点** | 自定义模型 | OpenAI 格式 | **支持** | 支持任意兼容 OpenAI 规范的本地模型或第三方中转端点 |

### 2. 语音合成 (TTS) 兼容性

| 服务 / 协议 | 适配说明 | 实测状态 |
| :--- | :--- | :--- |
| **小米 MiMo TTS** | 采用 chat/completions 音频扩展协议 | **已充分测试**（茉莉等音色实测正常） |
| **OpenAI 规范 TTS** | 标准 /v1/audio/speech 端点 | **协议适配**（已写好调用逻辑，未接入付费 Key 详测） |
| **本地服务 (如 GPT-SoVITS 等)** | 本地无需鉴权的 OpenAI 兼容接口 | **协议适配**（预留端点与音色字段，待社区反馈） |

> 注：如在未实测的服务商或自建端点上遇到接口报错，欢迎提交 [Issue](https://github.com/Yinhefuluoye/AI-DaisyMo-Milky/issues) 协助完善。

---

## 开发与致谢

- **重构与维护**：[Yinhefuluoye](https://github.com/Yinhefuluoye)
- **原型灵感**：感谢 [Rosysuki](https://github.com/Rosysuki) 提供的初始项目构想与原型
- **原作致敬**：感谢 **绘恋制作组** 创作的《三色绘恋》原作游戏
- 欢迎提交 Issue 与 Pull Request 共同交流完善。
