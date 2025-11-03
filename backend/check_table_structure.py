#!/usr/bin/env python3
"""检查数据库表结构"""

from sqlalchemy import create_engine, text
from app.core.config import settings

def check_pv_modules_table():
    """检查PV Modules表结构"""
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # 检查表是否存在
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='pv_modules'"))
        if result.fetchone() is None:
            print("PV Modules表不存在")
            return
        
        # 检查表结构
        result = conn.execute(text("PRAGMA table_info(pv_modules)"))
        print("PV Modules表结构:")
        columns = []
        for row in result:
            columns.append(row[1])
            print(f"  {row[1]} ({row[2]})")
        
        # 检查是否缺少height字段
        if 'height' not in columns:
            print("\n缺少height字段，需要添加...")
            # 添加height字段
            try:
                conn.execute(text("ALTER TABLE pv_modules ADD COLUMN height FLOAT"))
                conn.commit()
                print("成功添加height字段")
            except Exception as e:
                print(f"添加height字段失败: {e}")

if __name__ == "__main__":
    check_pv_modules_table()