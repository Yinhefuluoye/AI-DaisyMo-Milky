# -*- coding: utf-8 -*-
"""
DaisyMo AI 与语音协议引擎 (Deep AI & Speech Protocol Engine)
100% 纯 Python 深度模块，与 Pygame 及 GUI 渲染完全解耦。
统一封装：
1. 8 大主流大模型服务商最新接入点与预设矩阵
2. 多厂商深度思考 (Reasoning / Thinking) 特征探测与超参清洗
3. 差异化网络请求分流适配 (DeepSeek, OpenAI, Claude 原生 /messages, Qwen SSE 流式聚合, MiMO, 混元, 千帆)
4. 多轮对话上下文脱敏净化（杜绝私有 reasoning_content 回传）
5. 自适应双协议语音 TTS 合成 (OpenAI /v1/audio/speech 与小米 MiMo /v1/chat/completions)
6. 连通性测试与远程模型/音色动态拉取
"""

import json
import re
from base64 import b64decode
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

# 8 大真实服务商预设（基于当前主流生产环境与各厂商官方最新开发者文档）
AI_PROVIDERS: Dict[str, Dict[str, Any]] = {
    "deepseek": {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "default_model": "deepseek-v4-pro",
        "models": [
            "deepseek-v4-pro",
            "deepseek-v4-flash",
            "deepseek-v4-flash-vision-exp"
        ],
        "doc_url": "https://platform.deepseek.com/"
    },
    "openai": {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-5.5",
        "models": [
            "gpt-5.5",
            "gpt-5",
            "gpt-5-mini",
            "o3",
            "o4-mini"
        ],
        "doc_url": "https://platform.openai.com/"
    },
    "claude": {
        "name": "Claude",
        "base_url": "https://api.anthropic.com/v1",
        "default_model": "claude-fable-5-1",
        "models": [
            "claude-fable-5-1",
            "claude-opus-4-7",
            "claude-opus-4-5",
            "claude-sonnet-4-5"
        ],
        "doc_url": "https://console.anthropic.com/"
    },
    "gemini": {
        "name": "Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "default_model": "gemini-3.8-flash",
        "models": [
            "gemini-3.8-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash",
            "gemini-3",
            "gemini-2.5-pro",
            "gemini-2.5-flash"
        ],
        "doc_url": "https://aistudio.google.com/"
    },
    "qwen": {
        "name": "通义千问",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen3.8-max",
        "models": [
            "qwen3.8-max",
            "qwen3.8-flash",
            "qwen3.7-plus",
            "qwen3.7-max",
            "qwen3.6-plus"
        ],
        "doc_url": "https://bailian.console.aliyun.com/cn-beijing#/home"
    },
    "mimo": {
        "name": "小米 MiMO",
        "base_url": "https://api.xiaomimimo.com/v1",
        "default_model": "mimo-v2.5-pro",
        "models": [
            "mimo-v2.5-pro",
            "mimo-v2.5",
            "mimo-v2-pro",
            "mimo-v2-flash"
        ],
        "doc_url": "https://xiaomimimo.com/"
    },
    "hunyuan": {
        "name": "腾讯混元",
        "base_url": "https://api.hunyuan.cloud.tencent.com/v1",
        "default_model": "hy3",
        "models": [
            "hy3",
            "hunyuan-turbos",
            "hunyuan-t1"
        ],
        "doc_url": "https://cloud.tencent.com/product/hunyuan"
    },
    "ernie": {
        "name": "文心一言",
        "base_url": "https://qianfan.baidubce.com/v2",
        "default_model": "ernie-5.1",
        "models": [
            "ernie-5.1",
            "ernie-5.0",
            "ernie-4.5-turbo",
            "ernie-x1-turbo"
        ],
        "doc_url": "https://console.bce.baidu.com/qianfan/"
    },
    "custom": {
        "name": "自定义",
        "base_url": "http://localhost:11434/v1",
        "default_model": "custom-model",
        "models": [
            "custom-model"
        ],
        "doc_url": ""
    }
}


@dataclass
class AIConfig:
    """大模型与语音 TTS 全局配置实体"""
    provider: str = "deepseek"
    base_url: str = "https://api.deepseek.com"
    model_name: str = "deepseek-v4-pro"
    api_key: str = ""
    enable_thinking: bool = True
    tts_base_url: str = ""
    tts_model: str = ""
    tts_api_key: str = ""
    tts_voice: str = ""


@dataclass
class TTSConfig:
    """语音 TTS 配置实体"""
    base_url: str = "http://localhost:9880"
    model_name: str = "tts-1"
    api_key: str = ""
    voice_name: str = "alloy"
    timeout: int = 20


@dataclass
class ChatResult:
    """大模型响应结果实体 (包含思考链与结束原因)"""
    content: str = ""
    reasoning_content: str = ""
    finish_reason: str = ""
    raw_response: str = ""
    usage: Dict[str, Any] = field(default_factory=dict)
    total_tokens: int = 0
    is_success: bool = False
    error_message: str = ""


# 正则过滤 Unicode Emoji 与特殊符号（避免 Pygame 渲染中文字体时出现方块乱码）
EMOJI_PATTERN = re.compile(
    r"["
    r"\U00010000-\U0010ffff"
    r"\u2600-\u27bf"
    r"\ufe00-\ufe0f"
    r"\u200d"
    r"\u2300-\u23ff"
    r"\u2b50-\u2b55"
    r"\u203c\u2049\u2122\u2139\u2194-\u2199\u21a9-\u21aa"
    r"\u25aa-\u25ab\u25b6\u25c0\u25fb-\u25fe"
    r"\u3030\u303d\u3297\u3299"
    r"]+",
    flags=re.UNICODE
)


def remove_emojis(text: str) -> str:
    """过滤 Unicode Emoji 符号与控制字符，杜绝方块乱码 (单例正则高频复用)"""
    if not text:
        return ""
    return EMOJI_PATTERN.sub('', text)


def get_provider_protocol(provider: str, base_url: str = "") -> str:
    """归一化服务商协议标识，收敛协议分支判定"""
    p = (provider or "").strip().lower()
    u = (base_url or "").strip().lower()
    if "deepseek" in p or "deepseek" in u:
        return "deepseek"
    if "claude" in p or "anthropic" in u:
        return "claude"
    if "gemini" in p or "generativelanguage.googleapis.com" in u:
        return "gemini"
    if "qwen" in p or "dashscope" in u or "aliyun" in u:
        return "qwen"
    if "mimo" in p or "xiaomimimo" in u:
        return "mimo"
    if "hunyuan" in p or "tencent" in u:
        return "hunyuan"
    if "ernie" in p or "qianfan" in u or "baidu" in u:
        return "ernie"
    if "openai" in p or "openai" in u:
        return "openai"
    return "openai"


def check_thinking_support(
    provider: str,
    base_url: str,
    model: str,
    api_key: str = "",
    probe: bool = False
) -> bool:
    """检测当前大模型是否具备并支持深度思考 (Reasoning / Thinking) 能力"""
    m = (model or "").strip().lower()
    if not m:
        return False

    proto = get_provider_protocol(provider, base_url)

    # 1. 小米 MiMO: mimo-v2-flash 明确不支持思考，其余 v2.5 / v2-pro 支持
    if proto == "mimo":
        if "mimo-v2-flash" in m:
            return False
        if any(k in m for k in ("mimo-v2.5", "mimo-v2-pro", "mimo-v2-omni")):
            return True

    # 2. DeepSeek: V4 与 reasoner 支持思考，deepseek-chat 明确不支持
    elif proto == "deepseek":
        if "deepseek-v4" in m or "v4" in m or "reasoner" in m:
            return True
        if "deepseek-chat" in m:
            return False

    # 3. OpenAI: GPT-5+ 系列与 o1/o3/o4 系列支持思考
    elif proto == "openai":
        if any(k in m for k in ("gpt-5", "o3", "o4", "o1")):
            return True
        if any(k in m for k in ("gpt-4o", "gpt-4", "gpt-3.5")):
            return False

    # 4. Anthropic Claude: Fable-5, Opus-4.7, Claude-3.7 等支持思考
    elif proto == "claude":
        if any(k in m for k in ("fable", "opus-4-7", "opus-4-5", "sonnet-4-5", "claude-3-7")):
            return True
        if "claude-3-5" in m:
            return False

    # 5. Google Gemini: Gemini 2.5 / 3 系列支持思考
    elif proto == "gemini":
        if any(k in m for k in ("gemini-3", "gemini-2.5", "thinking")):
            return True

    # 6. 通义千问: Qwen3 全系混合架构支持思考
    elif proto == "qwen":
        if any(k in m for k in ("qwen3", "qwq")):
            return True

    # 7. 腾讯混元: turbos 自适应与 t1 慢思考，以及默认 hy3
    elif proto == "hunyuan":
        if any(k in m for k in ("turbos", "t1", "hy3")):
            return True

    # 8. 百度千帆: ERNIE-5, ERNIE-4.5, ERNIE-X1
    elif proto == "ernie":
        if any(k in m for k in ("x1", "5.1", "5.0", "4.5", "thinking")):
            return True

    # 9. 通用关键词特征匹配
    reasoning_keywords = ("reasoner", "thinking", "r1", "qwq", "o1", "o3", "o4", "turbos", "t1", "x1", "fable", "v4")
    if any(kw in m for kw in reasoning_keywords):
        return True
    standard_models = ("gpt-4o", "gpt-4", "gpt-3.5", "claude-3-5", "deepseek-chat")
    if any(kw in m for kw in standard_models):
        return False

    # 10. 自定义或未知模型：仅在显式请求 probe=True 时发起 1 token 同步探测
    if probe and base_url and api_key:
        try:
            url = base_url.strip().rstrip('/')
            if not url.endswith('/chat/completions') and not url.endswith('/messages'):
                url += '/chat/completions'
            headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}
            if "api.anthropic.com" in url:
                headers = {"x-api-key": api_key.strip(), "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
                probe_body = {
                    "model": model.strip(),
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "hi"}]
                }
            else:
                probe_body = {
                    "model": model.strip(),
                    "messages": [{"role": "user", "content": "hi"}],
                    "max_tokens": 1
                }
            r = requests.post(url, headers=headers, json=probe_body, timeout=5)
            if r.status_code == 200:
                resp_txt = r.text.lower()
                return any(k in resp_txt for k in ("reasoning", "thinking", "reasoning_content"))
        except Exception:
            pass

    return False


def build_chat_request(
    messages: List[Dict[str, str]],
    system_prompt: str,
    config: AIConfig,
    scenario_context: str = ""
) -> Tuple[str, Dict[str, str], Dict[str, Any], bool, bool]:
    """
    针对 8 大厂商精确分流组装 HTTP 请求地址、Header 与 Body
    支持动态注入剧情客观事实约束 (scenario_context)
    返回: (url, headers, body, use_stream, is_anthropic_native)
    """
    url = config.base_url.strip().rstrip('/')
    is_anthropic_native = ("api.anthropic.com" in url)

    if is_anthropic_native:
        if not url.endswith('/messages'):
            url += '/messages'
        headers = {
            "Content-Type": "application/json",
            "x-api-key": config.api_key.strip(),
            "anthropic-version": "2023-06-01"
        }
    else:
        if not url.endswith('/chat/completions'):
            url += '/chat/completions'
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_key.strip()}"
        }

    # 组装系统提示词：若包含检索到的客观剧情事实，挂载至末尾作为权威依据，杜绝脑补
    full_system_prompt = system_prompt or ""
    if scenario_context and scenario_context.strip():
        if full_system_prompt.strip():
            full_system_prompt = full_system_prompt.strip() + "\n\n" + scenario_context.strip()
        else:
            full_system_prompt = scenario_context.strip()

    # 组装请求消息列表：系统提示词置顶
    req_messages: List[Dict[str, str]] = []
    if full_system_prompt and not is_anthropic_native:
        req_messages.append({"role": "system", "content": full_system_prompt})

    # 上下文窗口滑动（保留最近 16 条）
    # 历史消息严格只保留 role 与 content 文本，绝不夹带 reasoning_content，防止多轮 400 报错
    recent_mem = messages[-16:] if len(messages) > 16 else messages
    for m in recent_mem:
        if m.get("role") in ("user", "assistant") and m.get("content"):
            req_messages.append({"role": m["role"], "content": m["content"]})

    model_name = config.model_name.strip()
    provider = (config.provider or "").strip().lower()
    enable_thinking = config.enable_thinking

    body: Dict[str, Any] = {
        "model": model_name,
        "messages": req_messages
    }

    use_stream = False

    if provider == "deepseek" or "deepseek" in url:
        # DeepSeek 规范：通过 extra_body.thinking 与 reasoning_effort 控制
        body["extra_body"] = {"thinking": {"type": "enabled" if enable_thinking else "disabled"}}
        if enable_thinking:
            body["reasoning_effort"] = "high"

    elif provider == "openai" or "openai.com" in url:
        # OpenAI 规范：使用 reasoning_effort 控制；GPT-5 系列温度仅支持 1.0；推理模型使用 max_completion_tokens
        if any(k in model_name.lower() for k in ("o3", "o4", "o1")):
            body["reasoning_effort"] = "high" if enable_thinking else "medium"
            body["max_completion_tokens"] = 4096
            body.pop("temperature", None)
        else:
            body["reasoning_effort"] = "high" if enable_thinking else "none"
            body["temperature"] = 1.0
            body["max_completion_tokens"] = 4096

    elif provider == "claude" or is_anthropic_native:
        # Anthropic 规范：原生端点提取顶层 system 字段
        if is_anthropic_native:
            body["system"] = full_system_prompt
            body["messages"] = [m for m in req_messages if m.get("role") != "system"]
        body["max_tokens"] = 8192
        if enable_thinking and "opus-4-7" not in model_name.lower():
            body["thinking"] = {"type": "enabled", "budget_tokens": 4096}
            body["temperature"] = 1.0
        else:
            body.pop("thinking", None)

    elif provider == "qwen" or "dashscope" in url:
        # 阿里百炼规范：思考模式仅支持流式 (stream: true)
        if enable_thinking:
            body["extra_body"] = {"enable_thinking": True, "thinking_budget": 4096}
            body["stream"] = True
            use_stream = True
        else:
            body["extra_body"] = {"enable_thinking": False}

    elif provider == "mimo" or "xiaomimimo" in url:
        # 小米 MiMO 规范：外层传 thinking 对象，max_completion_tokens
        body["thinking"] = {"type": "enabled" if enable_thinking else "disabled"}
        body["max_completion_tokens"] = 4096
        body.pop("temperature", None)

    elif provider == "ernie" or "qianfan" in url:
        # 百度千帆规范：4.5 系列传 extra_body.metadata.enable_thinking
        if "4.5" in model_name:
            body["extra_body"] = {"metadata": {"enable_thinking": bool(enable_thinking)}}

    return url, headers, body, use_stream, is_anthropic_native


def chat_completion(
    messages: List[Dict[str, str]],
    system_prompt: str,
    config: AIConfig,
    timeout: int = 60,
    on_stream_chunk: Optional[Callable[[str], None]] = None,
    scenario_context: str = ""
) -> ChatResult:
    """
    高深度对话补全接口：负责全自动组装、网络分流、流式聚合与格式脱敏
    支持注入剧情客观事实约束 (scenario_context)
    """
    result = ChatResult()
    try:
        url, headers, body, use_stream, is_anthropic = build_chat_request(
            messages,
            system_prompt,
            config,
            scenario_context=scenario_context
        )

        if use_stream:
            response = requests.post(url, headers=headers, json=body, timeout=timeout, stream=True)
            if response.status_code != 200:
                result.is_success = False
                result.error_message = f"HTTP {response.status_code}: {response.text[:120]}"
                return result

            collected_content: List[str] = []
            for line in response.iter_lines():
                if not line:
                    continue
                line_str = line.decode('utf-8') if isinstance(line, bytes) else line
                if line_str.startswith("data: "):
                    data_part = line_str[6:].strip()
                    if data_part == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_part)
                        choices = chunk.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            delta_text = delta.get("content", "")
                            if delta_text:
                                collected_content.append(delta_text)
                                if on_stream_chunk:
                                    on_stream_chunk(delta_text)
                    except Exception:
                        pass

            raw_txt = "".join(collected_content)
            result.content = remove_emojis(raw_txt.replace('```json', '').replace('```', '').strip())
            result.is_success = True
            return result

        else:
            response = requests.post(url, headers=headers, json=body, timeout=timeout)
            if response.status_code != 200:
                result.is_success = False
                result.error_message = f"HTTP {response.status_code}: {response.text[:120]}"
                return result

            response_json: Dict[str, Any] = response.json()
            result.raw_response = response.text
            if is_anthropic:
                blocks = response_json.get("content", [])
                respond = "".join(b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type") == "text")
                reasoning = "".join(b.get("thinking", "") for b in blocks if isinstance(b, dict) and b.get("type") == "thinking")
                result.reasoning_content = reasoning
                result.finish_reason = response_json.get("stop_reason", "")
                result.usage = response_json.get("usage", {})
                result.total_tokens = result.usage.get("output_tokens", 0) + result.usage.get("input_tokens", 0)
            else:
                choices = response_json.get("choices", [])
                if choices:
                    first_choice = choices[0]
                    msg = first_choice.get("message", {})
                    respond = msg.get("content", "") or ""
                    reasoning = msg.get("reasoning_content") or msg.get("reasoning") or msg.get("thinking") or ""
                    result.reasoning_content = reasoning
                    result.finish_reason = first_choice.get("finish_reason", "")
                else:
                    respond = ""
                result.usage = response_json.get("usage", {})
                result.total_tokens = result.usage.get("total_tokens", 0)

            result.content = remove_emojis(respond.replace('```json', '').replace('```', '').strip())
            result.is_success = True
            return result

    except Exception as ex:
        result.is_success = False
        result.error_message = str(ex)
        return result


# 导出规范顶层快捷别名
chat = chat_completion


def test_llm_connection(base_url: str, api_key: str, model: str, timeout: int = 12) -> Tuple[bool, str]:
    """连通性测试：支持 OpenAI 兼容格式与 Anthropic 原生 /messages 格式"""
    try:
        u = base_url.strip().rstrip('/')
        if "api.anthropic.com" in u:
            if not u.endswith('/messages'):
                u += '/messages'
            headers = {
                "x-api-key": api_key.strip(),
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            }
            body = {
                "model": model.strip(),
                "max_tokens": 5,
                "messages": [{"role": "user", "content": "hi"}]
            }
        else:
            if not u.endswith('/chat/completions'):
                u += '/chat/completions'
            headers = {
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type": "application/json"
            }
            body = {
                "model": model.strip(),
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 5
            }

        r = requests.post(u, headers=headers, json=body, timeout=timeout)
        if r.status_code == 200:
            return True, "连接成功"
        else:
            return False, f"失败: HTTP {r.status_code}"
    except Exception as ex:
        err_str = str(ex)
        if "Connection" in err_str:
            err_str = "连接失败"
        return False, f"错误: {err_str[:18]}"


def fetch_models(base_url: str, api_key: str, provider: str = "", timeout: int = 12) -> Tuple[bool, List[str], str]:
    """拉取远程端点可用大模型列表"""
    try:
        u = base_url.strip().rstrip('/')
        if u.endswith('/chat/completions'):
            u = u[:-len('/chat/completions')]
        if not u.endswith('/models'):
            u += '/models'

        headers = {
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json"
        }
        if "api.anthropic.com" in u:
            headers["x-api-key"] = api_key.strip()
            headers["anthropic-version"] = "2023-06-01"

        r = requests.get(u, headers=headers, timeout=timeout)
        if r.status_code == 200:
            resp_data = r.json()
            raw_list = resp_data.get("data", [])
            fetched: List[str] = []
            if isinstance(raw_list, list):
                for itm in raw_list:
                    if isinstance(itm, dict) and "id" in itm:
                        fetched.append(str(itm["id"]))
                    elif isinstance(itm, str):
                        fetched.append(itm)
            elif "models" in resp_data:
                for itm in resp_data["models"]:
                    if isinstance(itm, dict) and "name" in itm:
                        fetched.append(str(itm["name"]).replace("models/", ""))
                    elif isinstance(itm, str):
                        fetched.append(itm)

            if fetched:
                return True, fetched, f"成功获取 {len(fetched)} 个模型"
            else:
                return True, [], "成功但模型列表为空"
        else:
            return False, [], f"失败: HTTP {r.status_code}"
    except Exception as ex:
        err_msg = str(ex)
        if "Connection" in err_msg:
            err_msg = "连接失败"
        return False, [], f"错误: {err_msg[:16]}"


def fetch_tts_voices(tts_base_url: str, tts_api_key: str, tts_model: str = "", timeout: int = 5) -> Tuple[bool, List[str], str]:
    """拉取 TTS 服务端支持的音色清单"""
    try:
        u = tts_base_url.strip().rstrip('/')
        k = tts_api_key.strip()
        if k.startswith("tp-") and "api.xiaomimimo.com" in u:
            u = u.replace("api.xiaomimimo.com", "token-plan-cn.xiaomimimo.com")

        is_mimo = ("mimo" in tts_model.lower()) or ("xiaomimimo" in u.lower())
        preset_voices = [
            "冰糖", "茉莉", "苏打", "白桦", "Mia", "Chloe"
        ] if is_mimo else [
            "alloy", "echo", "fable", "onyx", "nova", "shimmer", "xiaoxiao", "yunxi"
        ]

        v_url = u
        if v_url.endswith('/audio/speech'):
            v_url = v_url[:-len('/audio/speech')]
        if v_url.endswith('/chat/completions'):
            v_url = v_url[:-len('/chat/completions')]
        v_url = v_url.rstrip('/') + "/audio/voices"

        headers = {"Authorization": f"Bearer {k}", "Content-Type": "application/json"}
        if is_mimo:
            headers["api-key"] = k

        fetched: List[str] = []
        try:
            r = requests.get(v_url, headers=headers, timeout=timeout)
            if r.status_code == 200:
                v_data = r.json()
                raw_v = v_data.get("voices", v_data.get("data", []))
                if isinstance(raw_v, list):
                    for item in raw_v:
                        if isinstance(item, dict) and "voice_id" in item:
                            fetched.append(str(item["voice_id"]))
                        elif isinstance(item, dict) and "name" in item:
                            fetched.append(str(item["name"]))
                        elif isinstance(item, str):
                            fetched.append(item)
        except Exception:
            pass

        combined: List[str] = []
        for v_item in fetched + preset_voices:
            if v_item and v_item not in combined:
                combined.append(v_item)

        if combined:
            return True, combined, f"成功获取 {len(combined)} 个TTS音色"
        else:
            return False, [], "未能获取音色"
    except Exception as ex:
        err_msg = str(ex)
        if "Connection" in err_msg:
            err_msg = "连接失败"
        return False, [], f"错误: {err_msg[:16]}"


def synthesize_tts_to_file(
    base_url: str = "",
    model_name: str = "",
    api_key: str = "",
    voice_name: str = "",
    text: str = "",
    output_path: str = "",
    timeout: int = 20,
    config: Optional[Any] = None
) -> Tuple[bool, str]:
    """
    双协议自适应 TTS 合成：兼容标准 OpenAI /v1/audio/speech 与小米 MiMo /v1/chat/completions
    支持直接传入 TTSConfig / AIConfig 对象，或传入独立参数。
    """
    if config is not None:
        clean_url = getattr(config, "tts_base_url", getattr(config, "base_url", "")).strip().rstrip('/')
        clean_model = getattr(config, "tts_model", getattr(config, "model_name", "")).strip()
        clean_api_key = getattr(config, "tts_api_key", getattr(config, "api_key", "")).strip()
        clean_voice = getattr(config, "tts_voice", getattr(config, "voice_name", "")).strip()
        timeout = getattr(config, "timeout", timeout)
    else:
        clean_url = base_url.strip().rstrip('/')
        clean_model = model_name.strip()
        clean_api_key = api_key.strip()
        clean_voice = voice_name.strip()

    is_mimo = ("mimo" in clean_model.lower()) or ("xiaomimimo.com" in clean_url.lower()) or clean_url.lower().endswith("/chat/completions")

    if is_mimo:
        if clean_api_key.startswith("tp-") and "api.xiaomimimo.com" in clean_url:
            clean_url = clean_url.replace("api.xiaomimimo.com", "token-plan-cn.xiaomimimo.com")

        if clean_url.endswith('/audio/speech'):
            clean_url = clean_url[:-len('/audio/speech')]
        if not clean_url.endswith('/chat/completions'):
            clean_url += '/chat/completions'

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {clean_api_key}",
            "api-key": clean_api_key
        }

        voice_val = clean_voice if clean_voice else "冰糖"
        body = {
            "model": clean_model or "mimo-v2.5-tts",
            "messages": [
                {
                    "role": "user",
                    "content": "用傲娇、轻快、略带娇蛮可爱的少女音色"
                },
                {
                    "role": "assistant",
                    "content": text
                }
            ],
            "audio": {
                "format": "wav",
                "voice": voice_val
            }
        }

        try:
            r = requests.post(clean_url, headers=headers, json=body, timeout=timeout)
            if r.status_code == 200:
                resp_data = r.json()
                audio_b64 = ""
                choices = resp_data.get("choices", [])
                if choices and isinstance(choices, list):
                    msg = choices[0].get("message", {})
                    audio_info = msg.get("audio", {})
                    if isinstance(audio_info, dict):
                        audio_b64 = audio_info.get("data", "")

                if audio_b64:
                    raw_bytes = b64decode(audio_b64)
                    with open(output_path, "wb") as f:
                        f.write(raw_bytes)
                    return True, "发音测试成功"
                else:
                    return False, "TTS未返回音频数据"
            else:
                err_msg = f"HTTP {r.status_code}"
                try:
                    err_json = r.json()
                    if "error" in err_json:
                        e_info = err_json["error"]
                        if isinstance(e_info, dict) and "message" in e_info:
                            err_msg = e_info["message"][:20]
                        elif isinstance(e_info, str):
                            err_msg = e_info[:20]
                except Exception:
                    pass
                return False, f"TTS失败: {err_msg}"
        except Exception as ex:
            err_str = str(ex)
            if "Connection" in err_str:
                return False, "TTS错误: 连接失败"
            return False, f"TTS错误: {err_str[:16]}"
    else:
        # 标准 OpenAI / 本地语音服务协议
        if not clean_url.endswith('/audio/speech'):
            clean_url += '/audio/speech'

        headers = {"Content-Type": "application/json"}
        if clean_api_key:
            headers["Authorization"] = f"Bearer {clean_api_key}"

        voice_val = clean_voice if clean_voice else "alloy"
        body = {
            "model": clean_model or "tts-1",
            "input": text,
            "voice": voice_val
        }

        try:
            r = requests.post(clean_url, headers=headers, json=body, timeout=timeout)
            if r.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(r.content)
                return True, "发音测试成功"
            else:
                return False, f"TTS失败: HTTP {r.status_code}"
        except Exception as ex:
            err_str = str(ex)
            if "Connection" in err_str:
                return False, "TTS错误: 连接失败"
            return False, f"TTS错误: {err_str[:16]}"
