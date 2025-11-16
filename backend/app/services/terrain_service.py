from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


logger = logging.getLogger(__name__)


@dataclass
class TerrainBounds:
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    min_z: Optional[float]
    max_z: Optional[float]


class TerrainService:
    """负责解析企业提供的地形/桩位 Excel 数据，并提供结构化结果。
    
    增强功能：
    - 缓存刷新锁：防止并发刷新
    - 异常重试：自动重试失败的文件读取
    - 无数据回退：提供默认空数据结构
    """

    def __init__(self, file_path: Optional[str | Path] = None) -> None:
        if file_path is None:
            # 优先使用环境变量指定的工作空间根目录（Docker环境）
            # 否则使用默认的项目根目录（物理机环境）
            if os.getenv("WORKSPACE_ROOT"):
                project_root = Path(os.getenv("WORKSPACE_ROOT"))
            else:
                project_root = Path(__file__).resolve().parents[3]
            file_path = project_root / "带坡度地形数据.xlsx"
        self.file_path = Path(file_path)
        self._cache_version = 0
        self._refresh_lock = threading.Lock()  # 缓存刷新锁
        self._max_retries = 3  # 最大重试次数
        self._retry_delay = 1.0  # 重试延迟（秒）

    @property
    def exists(self) -> bool:
        return self.file_path.exists()

    def load_layout(self, refresh: bool = False) -> Dict[str, Any]:
        """返回结构化地形+桩位数据。
        
        Args:
            refresh: 是否强制刷新缓存
            
        Returns:
            结构化的地形数据字典
            
        Raises:
            FileNotFoundError: 地形数据文件不存在时
            RuntimeError: 多次重试后仍无法加载数据时
        """
        if not self.exists:
            logger.warning(f"未找到地形数据文件: {self.file_path}，返回空数据结构")
            return self._get_empty_layout()

        if refresh:
            # 使用锁防止并发刷新
            with self._refresh_lock:
                logger.info(f"刷新地形数据缓存（版本：{self._cache_version} -> {self._cache_version + 1}）")
                self._cache_version += 1

        # 带重试机制加载数据
        last_exception = None
        for attempt in range(self._max_retries):
            try:
                return self._load_layout_cached(self._cache_version)
            except Exception as exc:
                last_exception = exc
                if attempt < self._max_retries - 1:
                    logger.warning(f"加载地形数据失败（尝试 {attempt + 1}/{self._max_retries}）: {exc}")
                    time.sleep(self._retry_delay * (attempt + 1))  # 指数退避
                else:
                    logger.error(f"加载地形数据失败，已达最大重试次数: {exc}")
        
        # 所有重试失败，返回空数据结构作为回退
        logger.error(f"无法加载地形数据，返回空数据结构。最后异常: {last_exception}")
        return self._get_empty_layout()

    def get_table(self, table_id: int, refresh: bool = False) -> Optional[Dict[str, Any]]:
        """获取指定 table 的桩位信息。"""

        data = self.load_layout(refresh=refresh)
        for table in data.get("tables", []):
            if table.get("table_id") == table_id:
                return table
        return None

    @lru_cache(maxsize=4)
    def _load_layout_cached(self, _version: int) -> Dict[str, Any]:
        logger.info("加载地形数据: %s", self.file_path)
        df = self._read_excel()

        if df.empty:
            raise ValueError("地形数据表为空，无法构建布局信息")

        tables: List[Dict[str, Any]] = []

        for table_id, group in df.groupby("table_id"):
            group_sorted = group.sort_values("pile_index")

            table_info: Dict[str, Any] = {
                "table_id": int(table_id),
                "zone_id": self._first_valid(group_sorted, "zone_id"),
                "preset_type": self._first_valid(group_sorted, "preset_type"),
                "table_direction": self._first_valid(group_sorted, "table_direction"),
                "table_slope_deg": self._first_valid_numeric(group_sorted, "table_slope_deg"),
                "slope_delta_deg": self._first_valid_numeric(group_sorted, "slope_delta_deg"),
                "notes": self._collect_notes(group_sorted),
                "piles": [],
            }

            for row in group_sorted.itertuples():
                table_info["piles"].append({
                    "index": int(row.pile_index),
                    "x": float(row.coord_x),
                    "y": float(row.coord_y),
                    "lat": self._to_float(row.latitude),
                    "lon": self._to_float(row.longitude),
                    "z_top": self._to_float(row.z_top),
                    "z_ground": self._to_float(row.z_ground),
                    "pile_reveal_m": self._to_float(row.pile_reveal_m),
                    "table_slope_deg": self._to_float(row.table_slope_deg),
                    "slope_delta_deg": self._to_float(row.slope_delta_deg),
                    "notes": row.notes if isinstance(row.notes, str) else None,
                })

            tables.append(table_info)

        bounds = self._calculate_bounds(df)

        metadata = {
            "source_file": self.file_path.name,
            "total_tables": len(tables),
            "total_piles": int(len(df)),
            "generated_at": datetime.now(timezone.utc),
            "bounds": bounds.__dict__ if bounds else None,
        }

        return {"metadata": metadata, "tables": tables}

    def _read_excel(self) -> pd.DataFrame:
        try:
            df = pd.read_excel(self.file_path, header=1, engine="openpyxl")
        except FileNotFoundError:
            raise
        except Exception as exc:
            logger.exception("读取地形 Excel 失败: %s", exc)
            raise RuntimeError(f"读取地形 Excel 失败: {exc}") from exc

        if df.empty:
            return df

        columns = list(df.columns)
        rename_map = self._build_rename_map(columns)
        df = df.rename(columns=rename_map)

        # 去掉内嵌标题行
        df = df[df["table_id"].astype(str).str.lower() != "table"]

        numeric_cols = [
            "table_id",
            "pile_index",
            "coord_x",
            "coord_y",
            "latitude",
            "longitude",
            "z_top",
            "z_ground",
            "pile_reveal_m",
            "table_slope_deg",
            "slope_delta_deg",
        ]

        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna(subset=["table_id", "pile_index", "coord_x", "coord_y"])

        df["table_id"] = df["table_id"].astype(int)
        df["pile_index"] = df["pile_index"].astype(int)

        df = df.assign(notes=df.apply(self._row_notes, axis=1))

        return df

    def _build_rename_map(self, columns: List[Any]) -> Dict[str, str]:
        base_names = [
            "table_id",
            "zone_id",
            "preset_type",
            "pile_index",
            "coord_x",
            "coord_y",
            "latitude",
            "longitude",
            "z_top",
            "z_ground",
            "pile_reveal_m",
            "table_slope_deg",
            "slope_delta_deg",
            "table_direction",
            "table_fault",
            "label",
            "fill_notes",
            "pile_adjustment",
            "z_top_new",
            "pile_reveal_new",
            "extra_1",
            "extra_2",
            "extra_3",
            "extra_4",
        ]

        rename_map: Dict[str, str] = {}
        for idx, column in enumerate(columns):
            if idx < len(base_names):
                rename_map[column] = base_names[idx]
            else:
                rename_map[column] = f"extra_{idx}"
        return rename_map

    def _row_notes(self, row: pd.Series) -> Optional[str]:
        fields = ["label", "table_fault", "fill_notes", "pile_adjustment"]
        notes = []
        for field in fields:
            value = row.get(field)
            if isinstance(value, str) and value.strip():
                notes.append(value.strip())
        return "; ".join(notes) if notes else None

    def _collect_notes(self, group: pd.DataFrame) -> Optional[str]:
        values = group["notes"].dropna().unique()
        return "; ".join(values.tolist()) if len(values) > 0 else None

    def _first_valid(self, df: pd.DataFrame, column: str) -> Optional[str]:
        series = df[column].dropna()
        if series.empty:
            return None
        value = series.iloc[0]
        return str(value) if not pd.api.types.is_numeric_dtype(series) else value

    def _first_valid_numeric(self, df: pd.DataFrame, column: str) -> Optional[float]:
        series = pd.to_numeric(df[column], errors="coerce").dropna()
        return float(series.iloc[0]) if not series.empty else None

    def _calculate_bounds(self, df: pd.DataFrame) -> Optional[TerrainBounds]:
        if df.empty:
            return None

        min_x = float(df["coord_x"].min())
        max_x = float(df["coord_x"].max())
        min_y = float(df["coord_y"].min())
        max_y = float(df["coord_y"].max())
        z_values = pd.concat([df["z_top"], df["z_ground"]], axis=0).dropna()
        min_z = float(z_values.min()) if not z_values.empty else None
        max_z = float(z_values.max()) if not z_values.empty else None

        return TerrainBounds(min_x, max_x, min_y, max_y, min_z, max_z)

    def _to_float(self, value: Any) -> Optional[float]:
        try:
            return float(value) if pd.notna(value) else None
        except (TypeError, ValueError):
            return None

    def _get_empty_layout(self) -> Dict[str, Any]:
        """返回空的地形数据结构作为回退。
        
        用于文件不存在或加载失败时，避免系统崩溃。
        """
        metadata = {
            "source_file": str(self.file_path.name) if self.file_path else "N/A",
            "total_tables": 0,
            "total_piles": 0,
            "generated_at": datetime.now(timezone.utc),
            "bounds": None,
            "error": "数据文件不存在或无法加载"
        }
        
        return {"metadata": metadata, "tables": []}


terrain_service = TerrainService()












