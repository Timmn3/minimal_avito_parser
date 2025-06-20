import psutil
import asyncio
from loguru import logger

def log_total_memory(prefix: str = ""):
    mem = psutil.virtual_memory()
    total = int(mem.total / 1024**2)
    used = int(mem.used / 1024**2)
    logger.success(f"[{prefix}] Общая память: {total} MB, Занято: {used} MB")

async def monitor_system_memory(prefix: str = ""):
    while True:
        mem = psutil.virtual_memory()
        used = int(mem.used / 1024**2)
        logger.success(f"[{prefix}] Занято памяти: {used} MB ")
        await asyncio.sleep(10)
