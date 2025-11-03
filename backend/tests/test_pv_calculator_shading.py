from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from app.services.pv_calculator import PVCalculator


def build_example_calculator():
    return PVCalculator(latitude=0.0, longitude=0.0, altitude=0.0, timezone='UTC')


def test_calculate_pv_power_with_dynamic_shading():
    calculator = build_example_calculator()

    times = pd.date_range('2024-01-01', periods=3, freq='H', tz='UTC')
    irradiance = pd.DataFrame({
        'poa_global': [800, 600, 400],
        'poa_direct': [600, 400, 200],
        'poa_diffuse': [200, 200, 200],
    }, index=times)

    module_params = {'pdc0': 400, 'gamma_pdc': -0.004}
    inverter_params = {'Paco': 5000, 'Pdco': 5200, 'Vdco': 400, 'Pso': 100, 'C0': -2e-6, 'C1': -2e-4, 'C2': -0.005, 'C3': 0.01}
    temperature_ambient = pd.Series([25, 25, 25], index=times)

    shading_series = pd.Series([1.0, 0.8, 0.5], index=times)

    power = calculator.calculate_pv_power(
        irradiance=irradiance,
        module_params=module_params,
        inverter_params=inverter_params,
        temperature_ambient=temperature_ambient,
        shading_factor=0.0,
        shading_factors=shading_series,
        soiling_loss=0.0,
        degradation_rate=0.0,
    )

    assert 'shading_multiplier' in power.columns
    assert math.isclose(power['shading_multiplier'].iloc[1], 0.8, rel_tol=1e-3)
    assert math.isclose(power['irradiance_global'].iloc[2], 400 * 0.5, rel_tol=1e-3)


def test_calculate_pv_power_with_constant_shading():
    calculator = build_example_calculator()

    times = pd.date_range('2024-01-01', periods=2, freq='H', tz='UTC')
    irradiance = pd.DataFrame({
        'poa_global': [1000, 1000],
        'poa_direct': [800, 800],
        'poa_diffuse': [200, 200],
    }, index=times)

    module_params = {'pdc0': 400, 'gamma_pdc': -0.004}
    inverter_params = {'Paco': 5000, 'Pdco': 5200, 'Vdco': 400, 'Pso': 100, 'C0': -2e-6, 'C1': -2e-4, 'C2': -0.005, 'C3': 0.01}
    temperature_ambient = pd.Series([25, 25], index=times)

    power = calculator.calculate_pv_power(
        irradiance=irradiance,
        module_params=module_params,
        inverter_params=inverter_params,
        temperature_ambient=temperature_ambient,
        shading_factor=0.3,
        shading_factors=None,
        soiling_loss=0.0,
        degradation_rate=0.0,
    )

    assert math.isclose(power['shading_multiplier'].iloc[0], 0.7, rel_tol=1e-3)
    assert math.isclose(power['irradiance_global'].iloc[1], 1000 * 0.7, rel_tol=1e-3)


