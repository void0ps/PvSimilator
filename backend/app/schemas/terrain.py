from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class TerrainBounds(BaseModel):
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    min_z: Optional[float] = None
    max_z: Optional[float] = None


class TerrainMetadata(BaseModel):
    source_file: str
    total_tables: int
    total_piles: int
    generated_at: datetime
    bounds: Optional[TerrainBounds] = None


class PilePoint(BaseModel):
    index: int
    x: float
    y: float
    lat: Optional[float] = None
    lon: Optional[float] = None
    z_top: Optional[float] = None
    z_ground: Optional[float] = None
    pile_reveal_m: Optional[float] = None
    table_slope_deg: Optional[float] = None
    slope_delta_deg: Optional[float] = None
    notes: Optional[str] = None


class TerrainTable(BaseModel):
    table_id: int
    zone_id: Optional[str] = None
    preset_type: Optional[str] = None
    table_direction: Optional[str] = None
    table_slope_deg: Optional[float] = None
    slope_delta_deg: Optional[float] = None
    notes: Optional[str] = None
    piles: List[PilePoint]


class TerrainLayoutResponse(BaseModel):
    metadata: TerrainMetadata
    tables: List[TerrainTable]


