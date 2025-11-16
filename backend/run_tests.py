#!/usr/bin/env python
"""
测试运行脚本
支持运行所有测试或特定测试模块，生成覆盖率报告
"""
import sys
import subprocess
from pathlib import Path


def run_all_tests():
    """运行所有测试并生成覆盖率报告"""
    print("🧪 运行所有测试...")
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--cov=app",
        "--cov-report=html",
        "--cov-report=term"
    ]
    return subprocess.run(cmd)


def run_specific_test(test_file):
    """运行特定测试文件"""
    print(f"🧪 运行测试: {test_file}")
    cmd = [
        sys.executable, "-m", "pytest",
        f"tests/{test_file}",
        "-v",
        "--cov=app",
        "--cov-report=term"
    ]
    return subprocess.run(cmd)


def run_quick_tests():
    """快速运行测试（不生成覆盖率报告）"""
    print("🧪 快速测试（无覆盖率）...")
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "-x"  # 遇到第一个失败就停止
    ]
    return subprocess.run(cmd)


def show_coverage_report():
    """显示覆盖率报告"""
    print("📊 打开覆盖率报告...")
    report_path = Path("htmlcov/index.html")
    if report_path.exists():
        import webbrowser
        webbrowser.open(report_path.absolute().as_uri())
    else:
        print("❌ 覆盖率报告不存在，请先运行测试生成报告")


def main():
    """主函数"""
    if len(sys.argv) == 1:
        # 无参数，运行所有测试
        result = run_all_tests()
        sys.exit(result.returncode)
    
    command = sys.argv[1]
    
    if command == "quick":
        result = run_quick_tests()
        sys.exit(result.returncode)
    
    elif command == "coverage":
        show_coverage_report()
    
    elif command.endswith(".py"):
        result = run_specific_test(command)
        sys.exit(result.returncode)
    
    else:
        print("用法：")
        print("  python run_tests.py              # 运行所有测试")
        print("  python run_tests.py quick        # 快速测试（无覆盖率）")
        print("  python run_tests.py test_xxx.py  # 运行特定测试")
        print("  python run_tests.py coverage     # 打开覆盖率报告")
        sys.exit(1)


if __name__ == "__main__":
    main()

