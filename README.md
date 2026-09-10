<div align="center">
  <img src="./icon.png" alt="AI-DaisyMo Logo" width="128"/>
  <h1>AI 墨小菊 (AI-DaisyMo)</h1>
  <p>《三色绘恋》墨小菊 同人专属伴侣系统</p>
</div>

---

## 项目声明

1. **同人非商业声明**：本项目为《三色绘恋》（Tricolour Lovestory）同人非盈利开源项目，仅供技术交流与粉丝相伴使用，严禁用于任何商业盈利或变相收费行为。
2. **版权归属**：项目中使用的立绘、背景、CG、音频等游戏视听资产版权归原制作方 **绘恋制作组 (HL-Galgame)** 所有。如有侵权，请联系维护者下架处理。
3. **安全与隐私**：API Key 仅保存在用户本地的 `assets/config.json` 中，不经过任何第三方中转，工程已配置 `.gitignore` 避免敏感凭证与个人聊天记录被上传。
4. **免责声明**：对白内容由第三方大语言模型根据人设提示词实时生成，不代表原版权方及本项目开发者立场。

---

## 核心特性

- **和纸质感界面**：还原官方三层底框视觉，支持 2x SSAA 超采样进入主键、平滑消融转场与回忆（Backlog）珍藏分栏。
- **原案台词深度蒸馏**：基于 6,397 句官方剧本语料提炼心智机制，还原傲娇长姐防御、生活温存主义与真诚基准线。
- **深度思考能力开关**：自动识别模型是否支持 Reasoning/Thinking（如 mimo-v2.5、deepseek-reasoner 等），支持开启、关闭与置灰禁用三态；关闭时显式压低延迟，实现 2 秒级极速响应。
- **双协议 TTS 语音合成**：兼容标准 OpenAI 协议与小米 MiMo 拟真少女音色。
- **多模型服务商支持**：内置小米 MiMo、DeepSeek、Claude、OpenAI、Gemini、通义千问等主流服务商预设及自定义端点。

---

## 运行方式

### 方式一：下载 Release 整合包（普通用户推荐）

前往项目的 [Releases 页面](https://github.com/Rosysuki/AI-DaisyMo/releases) 下载最新的绿色运行包，解压后直接运行可执行文件即可。

### 方式二：从源码运行（开发者 / 可选方案）

若选择从源码运行，需先安装 [Python 3.10+](https://www.python.org/downloads/)（安装时勾选 "Add python.exe to PATH"）。

- **脚本一键启动**：双击运行根目录下的 `run.bat`，脚本会自动检测环境、创建虚拟环境并安装依赖后启动；
- **手动命令启动**：
  ```bash
  pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  python DaisyMo.py
  ```

---

## 首次配置

首次进入游戏后，在主界面点击右下角 **「设置」**（或进入游戏后点击右下角 **「SYSTEM」**），填入所选服务商的 API Key 并点击 **「保存配置」**。下次启动自动读取，无需重复输入。

---

## 常用操作与快捷键

| 操作 / 快捷键 | 说明 |
| :--- | :--- |
| `1` | 随机切换立绘表情 |
| `2` | 随机切换服装姿势 |
| `3` | 随机切换场景背景 |
| `SPACE` / 鼠标左键 | 推进剧情 / 快速显示全部对白 |
| `ESC` | 退出全屏 / 关闭弹窗 |
| 对话界面右下角按钮 | **AUTO** 自动播放 / **LOG** 历史与珍藏 / **SYS** 核心设置 |

---

## 贡献与致谢

- **项目维护**：[Rosysuki](https://github.com/Rosysuki), [Lulianovic](https://github.com/Lulianovic)
- **致谢**：感谢 **绘恋制作组** 创作的《三色绘恋》与生动的墨小菊。
- 欢迎提交 Issue 与 Pull Request。
