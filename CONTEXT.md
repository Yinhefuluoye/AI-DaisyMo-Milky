# CONTEXT.md — AI-DaisyMo 领域词汇表

这个文件只放**术语**：每个词在本项目里到底指什么、它在代码里落在哪儿。
架构决策不写在这里，术语变了才改这里。

---

## 角色

**墨小菊** — AI 角色本身。代码里没有这个类名，她表现为 `DaisyMo` 的人格文件
（`DaisyMo.soul` / `assets/DaisyMo.soul`）加上回复 JSON 里的 `face` / `body` / `where` / `text` 四个字段。

**邱诚** — 玩家。他的输入落在聊天记录里 `role == "user"` 的那些条目。

---

## 会话

**聊天记录** — 这段回忆的**持久内容**，就是那份 `[{role, content}, ...]` 列表。
落盘在 `assets/DaisyMo_history.json`。

> 曾用名：代码里的 `DaisyMo.memory`。这个名字容易被读成"模型记忆"，其实它只是聊天记录。
> 正在抽出的 `Conversation`（见下）就是它的所有者。

**一条记录** — 聊天记录里的一个元素，形如 `{"role": "user"|"assistant", "content": str}`。
`assistant` 的 `content` 是一段 JSON 字符串，`user` 的是纯文本。

**轮** — 墨小菊回复一次算一轮。用于分支存档卡片的「N 轮对话」和自动快照的最低门槛。

---

## 画面（不是会话）

这三样由「最后一条回复」算出来，载入分支后会重算。它们**不属于聊天记录**。

**当前台词** — 屏幕上正在显示的那一句，是聊天记录最后一条的副本。代码里是 `DaisyMo.text`。

**立绘队列** — 当前这一帧要画的人物图层（脸 + 身体两张 Surface）。代码里是 `DaisyMo.photos`。

**画面位置** — 立绘的视口偏移。代码里是 `DaisyMo.offset`。

---

## 回忆界面与存档

**回忆界面** — 全屏的信纸风格界面，三个分栏：历史 / 珍藏 / 分支存档。代码里是 `Screen.history_menu`。

**分支存档** — 用户手动命名保存的一条时间线，文件在 `assets/history_backups/`。可以载入回去，等于从那一刻重新分叉。

**自动快照** — 系统自己生成的存档，两种触发时机：清空记录前、切换分支前。
策略：同名只保留一条（原地覆盖），且只有开场白时不生成。

**软删除** — 删除分支存档时不真的抹掉，而是移进 `assets/history_backups/.trash/`，可以手工找回。

---

## 架构术语（本项目专用）

**Conversation** — 即将抽出的 module，唯一拥有「聊天记录」的所有者。
门上有四个动作：`messages()` / `append(role, content)` / `replace_with(messages)` / `clear()`。
落盘在它之外（走 `daisymo_history_manager`），它不是适配器，只管内存。

**场景状态** — 上面「画面」那三样的统称。**故意不归 `Conversation` 管**：
它由回复算出来、供渲染用，和「聊过什么」是两个变更理由。等拆屏时再单独归位。

**UiState** — 即将抽出的「跨屏共享、随运行变化」的界面状态的所有者。
当前散落在 `Screen` 实例上的标量字段，共约 250 处引用（`self.mode` / `self.is_thinking` /
`self.voice_channel` / `self.toast_*` / `self.typewriter_*` / `self.fade_*` 等 28 个）。
抽出后 `Screen` 只持有一个 `self.ui` 命名空间，四个屏幕方法经 `self.ui.xxx` 访问。
**不属于 UiState**：字体与 `pygame.image.load` 出的 Surface（素材缓存）、`screen`/`mixer`/`chat_queue`/
`conversation`/`daisymo`/`player_box`（句柄与控件对象，不是标量状态）。
