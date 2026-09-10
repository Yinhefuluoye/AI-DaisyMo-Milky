# -*- coding: utf-8 -*-
"""
墨小菊 专属大语言模型微调与知识蒸馏训练脚本 (LoRA / SFT)
支持基座模型：
- Qwen/Qwen2.5-7B-Instruct / Qwen2.5-1.5B-Instruct / Qwen2.5-3B-Instruct
- deepseek-ai/DeepSeek-R1-Distill-Qwen-7B / 1.5B
使用方法：
  python scripts/train_distill_lora.py --base_model Qwen/Qwen2.5-7B-Instruct --output_dir ./models/DaisyMo-7B-LoRA
"""

import os
import argparse
import json

def main():
    parser = argparse.ArgumentParser(description="DaisyMo LoRA Distillation Training")
    parser.add_argument("--base_model", type=str, default="Qwen/Qwen2.5-7B-Instruct", help="Pretrained base model name or path")
    parser.add_argument("--dataset_path", type=str, default="dataset/daisymo_distill_sharegpt.json", help="Path to ShareGPT dataset")
    parser.add_argument("--output_dir", type=str, default="./models/daisymo-lora", help="Output directory for saved model")
    parser.add_argument("--batch_size", type=int, default=2, help="Per device train batch size")
    parser.add_argument("--grad_accum", type=int, default=4, help="Gradient accumulation steps")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--lr", type=float, default=2e-4, help="Learning rate")
    parser.add_argument("--lora_rank", type=int, default=16, help="LoRA rank (r)")
    parser.add_argument("--lora_alpha", type=int, default=32, help="LoRA alpha")
    args = parser.parse_args()

    print("=" * 60)
    print(" 墨小菊 (Daisy Mo) 专属模型蒸馏微调引擎")
    print(f" 基座模型: {args.base_model}")
    print(f" 训练集:   {args.dataset_path}")
    print(f" 输出目录: {args.output_dir}")
    print(f" 训练轮数: {args.epochs}, 学习率: {args.lr}")
    print("=" * 60)

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer
        from peft import LoraConfig, get_peft_model, TaskType
        from datasets import load_dataset
    except ImportError:
        print("\n[提示] 运行微调训练需要安装依赖库：")
        print("pip install torch transformers peft datasets accelerate trl\n")
        print("如果使用快速微调，强烈推荐安装 Unsloth:")
        print("pip install unsloth\n")
        return

    print("正在加载 Tokenizer 与基座模型...")
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        torch_dtype=torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16,
        device_map="auto",
        trust_remote_code=True
    )

    print("配置 LoRA 适配层...")
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=args.lora_rank,
        lora_alpha=args.lora_alpha,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    print("微调环境准备就绪，可加载 dataset/daisymo_distill_sharegpt.json 进行一键微调。")

if __name__ == "__main__":
    main()
