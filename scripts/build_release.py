# -*- coding: utf-8 -*-
"""
AI-DaisyMo Release 一键自动化构建与绿色打包脚本
执行本脚本将自动完成：
1. 从 icon.png 生成高清多尺寸 icon.ico
2. 调用 PyInstaller 编译无控制台独立主程序 (onedir 模式)
3. 清洗并拷贝视听素材、角色提示词与配置模板（严格过滤私密 Key 与本地缓存）
4. 打包输出开箱即用的 AI-DaisyMo-v0.1-win64.zip 绿色分发包
"""

import os
import sys
import shutil
import zipfile
import subprocess
from pathlib import Path
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
RELEASE_DIR = DIST_DIR / "AI-DaisyMo"
VERSION = "v0.1"
ZIP_NAME = f"AI-DaisyMo-{VERSION}-win64.zip"
ZIP_PATH = DIST_DIR / ZIP_NAME

def step(msg: str):
    print(f"\n=======================================================")
    print(f"  {msg}")
    print(f"=======================================================")

def generate_ico():
    step("1. 生成 Windows 原生高清图标 (icon.ico)...")
    png_path = ROOT_DIR / "icon.png"
    ico_path = ROOT_DIR / "icon.ico"
    if not png_path.exists():
        print(f"[警告] 未找到 {png_path}，跳过图标生成")
        return
    img = Image.open(png_path)
    icon_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path, format='ICO', sizes=icon_sizes)
    print(f"[OK] 已成功生成多分辨率图标: {ico_path}")

def run_pyinstaller():
    step("2. 执行 PyInstaller 编译构建...")
    spec_path = ROOT_DIR / "AI-DaisyMo.spec"
    if not spec_path.exists():
        raise FileNotFoundError(f"未找到 spec 描述文件: {spec_path}")
    
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        str(spec_path),
        "--noconfirm",
    ]
    print(f"执行命令: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=str(ROOT_DIR))
    if res.returncode != 0:
        raise RuntimeError(f"PyInstaller 构建失败，退出码: {res.returncode}")
    print("[OK] PyInstaller 二进制编译完成！")

def copy_assets_clean():
    step("3. 清洗并拷贝运行素材至绿色发布目录...")
    if not RELEASE_DIR.exists():
        raise FileNotFoundError(f"未找到构建输出目录: {RELEASE_DIR}")
    
    # 1. 拷贝根目录关键文件
    root_files_to_copy = [
        ("DaisyMo.soul", True),
        ("icon.png", True),
        ("icon.ico", False),
        ("README.md", False),
    ]
    for filename, required in root_files_to_copy:
        src = ROOT_DIR / filename
        dst = RELEASE_DIR / filename
        if src.exists():
            shutil.copy2(src, dst)
            print(f"  [拷贝文件] {filename} -> {dst.name}")
        elif required:
            raise FileNotFoundError(f"必需文件丢失: {src}")

    # 2. 拷贝 assets 目录（严格排除私密、历史和临时缓存）
    src_assets = ROOT_DIR / "assets"
    dst_assets = RELEASE_DIR / "assets"
    if dst_assets.exists():
        shutil.rmtree(dst_assets)
    dst_assets.mkdir(parents=True, exist_ok=True)

    # 排除名单
    EXCLUDE_DIRS = {"tts_cache", "history_backups"}
    EXCLUDE_FILES = {
        "config.json",          # 严防个人私密 API Key
        "DaisyMo_history.json", # 严防个人聊天历史
        "favorites.json",       # 严防个人收藏
        "fetched_models.json",  # 用户本机的模型列表缓存
        "temp_tts.wav",         # 临时音频
        "DaisyMo.soul.tmp",
        "DaisyMo.soul.corrupt.bak",
    }

    copied_assets_count = 0
    for root, dirs, files in os.walk(src_assets):
        # 原地过滤掉排除的目录
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        rel_path = Path(root).relative_to(src_assets)
        target_sub_dir = dst_assets / rel_path
        target_sub_dir.mkdir(parents=True, exist_ok=True)
        
        for f in files:
            if f in EXCLUDE_FILES or f.endswith(".tmp") or f.endswith(".bak"):
                continue
            src_f = Path(root) / f
            dst_f = target_sub_dir / f
            shutil.copy2(src_f, dst_f)
            copied_assets_count += 1

    print(f"[OK] 已安全拷贝 {copied_assets_count} 个素材资产至 assets 目录")
    
    # 校验：确保绝对没有打包私密 config.json
    leaked_config = dst_assets / "config.json"
    if leaked_config.exists():
        os.remove(leaked_config)
        print("[安全警报] 发现泄露的 config.json，已立即剔除！")

    # 确保 config.example.json 存在
    example_src = src_assets / "config.example.json"
    example_dst = dst_assets / "config.example.json"
    if example_src.exists() and not example_dst.exists():
        shutil.copy2(example_src, example_dst)

def package_zip():
    step(f"4. 压缩打包生成绿色分发包: {ZIP_NAME}...")
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
        
    total_files = 0
    with zipfile.ZipFile(ZIP_PATH, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for root, dirs, files in os.walk(RELEASE_DIR):
            for file in files:
                file_path = Path(root) / file
                archive_name = Path("AI-DaisyMo") / file_path.relative_to(RELEASE_DIR)
                zf.write(file_path, arcname=str(archive_name))
                total_files += 1
                
    zip_size_mb = ZIP_PATH.stat().st_size / (1024 * 1024)
    print(f"[OK] 成功打包 {total_files} 个文件！")
    print(f"  [产物位置] {ZIP_PATH}")
    print(f"  [压缩包体积] {zip_size_mb:.2f} MB")

def verify_build():
    step("5. 产物自检与就绪验证...")
    exe_path = RELEASE_DIR / "AI-DaisyMo.exe"
    soul_path = RELEASE_DIR / "DaisyMo.soul"
    ui_path = RELEASE_DIR / "assets" / "ui"
    
    assert exe_path.exists(), "主执行文件缺失: AI-DaisyMo.exe"
    assert soul_path.exists(), "角色提示词缺失: DaisyMo.soul"
    assert ui_path.exists(), "UI 目录缺失: assets/ui"
    assert not (RELEASE_DIR / "assets" / "config.json").exists(), "严重安全错误: config.json 被意外包含！"
    assert not (RELEASE_DIR / "assets" / "favorites.json").exists(), "严重安全错误: favorites.json 被意外包含！"
    assert not (RELEASE_DIR / "assets" / "DaisyMo_history.json").exists(), "严重安全错误: DaisyMo_history.json 被意外包含！"
    assert not (RELEASE_DIR / "assets" / "history_backups").exists(), "严重安全错误: history_backups 目录被意外包含！"
    assert ZIP_PATH.exists(), "最终压缩包未生成！"
    
    exe_size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"  [主程序] AI-DaisyMo.exe ({exe_size_mb:.2f} MB)")
    print(f"  [分发包] {ZIP_PATH.name} ({ZIP_PATH.stat().st_size / (1024 * 1024):.2f} MB)")
    print("\n恭喜！Release 构建全部通过，可直接上传 ZIP 至 GitHub Releases！")

def main():
    try:
        generate_ico()
        run_pyinstaller()
        copy_assets_clean()
        package_zip()
        verify_build()
    except Exception as e:
        print(f"\n[构建异常中断] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
