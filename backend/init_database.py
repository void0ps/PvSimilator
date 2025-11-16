#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
初始化数据库脚本
"""
import os
import sys
from pathlib import Path

# 确保在backend目录运行
backend_dir = Path(__file__).parent
os.chdir(backend_dir)

print("=" * 60)
print("PV Simulator - 数据库初始化")
print("=" * 60)
print(f"\n工作目录: {backend_dir}")

# 导入数据库模块
try:
    from app.core.database import Base, engine
    print("\n[1/2] 导入数据库模块成功")
except Exception as e:
    print(f"\n[错误] 导入失败: {e}")
    sys.exit(1)

# 创建数据库表
try:
    print("[2/2] 创建数据库表...")
    Base.metadata.create_all(bind=engine)
    print("\n✓ 数据库初始化成功！")
    
    # 检查数据库文件
    db_file = backend_dir / "pv_simulator.db"
    if db_file.exists():
        size = db_file.stat().st_size
        print(f"✓ 数据库文件: {db_file}")
        print(f"✓ 文件大小: {size} 字节")
    else:
        print(f"! 警告: 数据库文件未找到: {db_file}")
        
except Exception as e:
    print(f"\n[错误] 创建数据库失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("数据库已准备就绪，可以启动服务！")
print("=" * 60)



