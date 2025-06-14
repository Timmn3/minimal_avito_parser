import os
import platform
import subprocess
from loguru import logger


def kill_chrome_processes():
    """
    Убивает все процессы chrome и chromedriver.
    Поддерживает Windows и Linux/Unix.
    """
    try:
        os_name = platform.system()

        def get_win_pids(process_name):
            cmd = f'tasklist | findstr /I "{process_name}"'
            try:
                result = subprocess.check_output(
                    cmd,
                    stderr=subprocess.DEVNULL,
                    shell=True,
                    encoding='utf-8',
                    errors='ignore'
                )
                pids = []
                for line in result.splitlines():
                    parts = line.split()
                    if len(parts) >= 2 and parts[1].isdigit():
                        pids.append(parts[1])
                return pids
            except subprocess.CalledProcessError:
                return []

        if os_name == "Windows":
            return
            chrome_pids = get_win_pids("chrome.exe")
            driver_pids = get_win_pids("chromedriver.exe")

            all_pids = set(chrome_pids + driver_pids)

            if all_pids:
                logger.info(f"Найдены зависшие процессы Chrome/Chromedriver: {all_pids}")
                for pid in all_pids:
                    os.system(f"taskkill /F /PID {pid}")
                logger.info(f"Завершены {len(all_pids)} зависших процессов Chrome/Chromedriver")
            else:
                logger.info("Нет зависших процессов Chrome/Chromedriver")

        else:
            # Линукс логика
            chrome_pids = os.popen("pgrep -f chrome").read().splitlines()
            driver_pids = os.popen("pgrep -f chromedriver").read().splitlines()

            all_pids = set(chrome_pids + driver_pids)

            if all_pids:
                logger.info(f"Найдены зависшие процессы Chrome/Chromedriver: {all_pids}")
                for pid in all_pids:
                    os.system(f"kill -9 {pid}")
                logger.info(f"Завершены {len(all_pids)} зависших процессов Chrome/Chromedriver")
            else:
                logger.info("Нет зависших процессов Chrome/Chromedriver")

    except Exception as e:
        logger.error(f"Ошибка при убивании процессов: {e}")