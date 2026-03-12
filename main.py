from scripts.batch_run import batch_process_county
from scripts.data_process import export_verify_data
from utils.file_utils import get_dir_name, get_dirs
from config.config import DATA_DIR, EXPORT_CONFIG
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from logger import log

# 全局锁，用于保护 result_data_list 的写入
data_lock = threading.Lock()
max_workers = 5


def safe_process_county(county_dir, export_unit, parent_result_list):
    """
    处理并根据配置决定是否立即导出
    """
    try:
        county_name = get_dir_name(county_dir)
        # 每个线程维护自己的私有列表，处理当前区县
        current_county_data = []
        # if county_name != '210115 辽中区':
        #     return
        batch_process_county(county_dir, current_county_data)

        # 逻辑 A: 如果导出粒度是区县，直接在这里完成导出，不再写回主列表
        if export_unit == "county":
            print(f"[EXPORT] 正在导出区县: {county_name}")
            export_verify_data(county_dir, current_county_data)

        # 逻辑 B: 如果导出粒度是城市或省，则需要加锁合并到父级列表
        else:
            with data_lock:
                parent_result_list.extend(current_county_data)

    except Exception as e:
        log.error(f"[ERROR] 处理区县 {get_dir_name(county_dir)} 失败: {e}")


def main():
    export_unit = EXPORT_CONFIG.get("unit", "province")
    province_dirs = get_dirs(DATA_DIR)

    with ThreadPoolExecutor(
        max_workers=max_workers, thread_name_prefix="CountyWorker"
    ) as executor:
        for province_dir in province_dirs:
            province_name = get_dir_name(province_dir)
            log.info(f"\n>>> 开始处理省份: {province_name}")

            province_result_data = []
            city_dirs = get_dirs(province_dir)

            for city_dir in city_dirs:
                city_name = get_dir_name(city_dir)
                log.info(f"-> 城市: {city_name}")

                # 只有非区县模式，才需要这个城市级的共享列表
                city_result_data = [] if export_unit == "city" else province_result_data

                county_dirs = get_dirs(city_dir)

                # 提交任务：传入对应的父级列表和导出配置
                futures = [
                    executor.submit(
                        safe_process_county,
                        c_dir,
                        export_unit,
                        city_result_data,
                    )
                    for c_dir in county_dirs
                ]

                # 等待当前城市的所有线程完成
                for _ in as_completed(futures):
                    pass

                # 城市级导出逻辑
                if export_unit == "city":
                    log.info(f"[EXPORT] 正在汇总导出城市: {city_name}")
                    export_verify_data(city_dir, city_result_data)

            # 省级导出逻辑
            if export_unit == "province":
                log.info(f"[EXPORT] 正在汇总导出省份: {province_name}")
                export_verify_data(province_dir, province_result_data)


if __name__ == "__main__":
    main()
