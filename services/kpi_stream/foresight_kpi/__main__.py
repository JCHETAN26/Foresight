"""Run the KPI stream consumer: python -m foresight_kpi"""

from __future__ import annotations

import asyncio

from foresight_kpi.consumer import run

if __name__ == "__main__":
    asyncio.run(run())
