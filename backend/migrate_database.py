#!/usr/bin/env python3
"""
迁移数据库：将 backend/pv_simulator.db 的数据合并到 backend/data/pv_simulator.db
"""

import sys
import os
from pathlib import Path
import sqlite3
import shutil
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def migrate_database():
    """迁移数据库数据"""
    
    backend_dir = Path(__file__).parent
    old_db = backend_dir / "pv_simulator.db"
    new_db = backend_dir / "data" / "pv_simulator.db"
    
    # 确保 data 目录存在
    new_db.parent.mkdir(exist_ok=True)
    
    print("=" * 60)
    print("数据库迁移工具")
    print("=" * 60)
    print(f"\n旧数据库: {old_db}")
    print(f"新数据库: {new_db}")
    
    # 检查旧数据库是否存在
    if not old_db.exists():
        print("\n✓ 旧数据库不存在，无需迁移")
        return
    
    # 检查新数据库是否存在
    if not new_db.exists():
        print(f"\n新数据库不存在，直接复制旧数据库...")
        shutil.copy2(old_db, new_db)
        print(f"✓ 数据库已复制到: {new_db}")
        return
    
    # 两个数据库都存在，需要合并数据
    print("\n两个数据库都存在，开始合并数据...")
    
    # 备份新数据库
    backup_path = new_db.parent / f"pv_simulator.db.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(new_db, backup_path)
    print(f"✓ 已备份新数据库到: {backup_path}")
    
    try:
        # 连接两个数据库
        old_conn = sqlite3.connect(old_db)
        new_conn = sqlite3.connect(new_db)
        
        # 获取旧数据库的所有表
        old_cursor = old_conn.cursor()
        old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in old_cursor.fetchall() if not row[0].startswith('sqlite_')]
        
        print(f"\n找到 {len(tables)} 个表: {', '.join(tables)}")
        
        # 合并每个表的数据
        new_cursor = new_conn.cursor()
        total_migrated = 0
        
        for table in tables:
            try:
                # 获取旧表中的所有数据
                old_cursor.execute(f"SELECT * FROM {table}")
                rows = old_cursor.fetchall()
                
                if not rows:
                    print(f"  - {table}: 无数据，跳过")
                    continue
                
                # 获取列名
                old_cursor.execute(f"PRAGMA table_info({table})")
                columns = [col[1] for col in old_cursor.fetchall()]
                col_names = ', '.join(columns)
                placeholders = ', '.join(['?' for _ in columns])
                
                # 检查新表中是否已有数据
                new_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                existing_count = new_cursor.fetchone()[0]
                
                # 插入数据（使用 INSERT OR IGNORE 避免重复）
                insert_sql = f"INSERT OR IGNORE INTO {table} ({col_names}) VALUES ({placeholders})"
                new_cursor.executemany(insert_sql, rows)
                
                migrated_count = new_cursor.rowcount
                total_migrated += migrated_count
                print(f"  - {table}: 迁移 {migrated_count} 条记录 (旧: {len(rows)}, 新: {existing_count})")
                
            except Exception as e:
                print(f"  - {table}: 迁移失败 - {e}")
                continue
        
        # 提交更改
        new_conn.commit()
        print(f"\n✓ 迁移完成！共迁移 {total_migrated} 条记录")
        
        # 关闭连接
        old_conn.close()
        new_conn.close()
        
        # 询问是否删除旧数据库
        print(f"\n是否删除旧数据库 {old_db}? (y/n): ", end='')
        # 在脚本中自动选择保留旧数据库作为备份
        print("n (保留作为备份)")
        
    except Exception as e:
        print(f"\n✗ 迁移失败: {e}")
        # 恢复备份
        if backup_path.exists():
            shutil.copy2(backup_path, new_db)
            print(f"已恢复备份数据库")
        raise

if __name__ == "__main__":
    migrate_database()

