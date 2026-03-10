#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
添加 backtrack_enabled 字段到 simulations 表
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "pv_simulator.db")

def migrate():
    print("Adding backtrack_enabled column to simulations table...")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 检查列是否已存在
    cursor.execute("PRAGMA table_info(simulations)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'backtrack_enabled' not in columns:
        cursor.execute("ALTER TABLE simulations ADD COLUMN backtrack_enabled BOOLEAN DEFAULT 1")
        conn.commit()
        print("  Column 'backtrack_enabled' added successfully!")
    else:
        print("  Column 'backtrack_enabled' already exists.")

    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
