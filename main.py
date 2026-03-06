from scripts.batch_run import batch_process_county
from scripts.data_process import export_verify_data
from utils.file_utils import get_dir_name, get_dirs
from config.config import DATA_DIR, EXPORT_CONFIG


def main():
    # 遍历省、市、区/县目录，并提取名称
    province_dirs = get_dirs(DATA_DIR)
    result_excel_data = []

    for province_dir in province_dirs:
        # 提取省份名称
        province_name = get_dir_name(province_dir)
        # 以省为单位创建校验excel

        city_dirs = get_dirs(province_dir)
        for city_dir in city_dirs:
            # 提取城市名称
            city_name = get_dir_name(city_dir)
            county_dirs = get_dirs(city_dir)
            for county_dir in county_dirs:
                # 提取区县名称
                county_name = get_dir_name(county_dir)

                # 格式化打印省市区名称
                print(
                    f"省份：{province_name} | 城市：{city_name} | 区县：{county_name}"
                )

                # 初始化结果数据列表（用于生成Excel）
                batch_process_county(county_dir, result_excel_data)

                # 按区县粒度导出：导出当前区县数据，然后清空
                if EXPORT_CONFIG["unit"] == "county":
                    export_verify_data(province_dir, result_excel_data)
                    result_excel_data = []

            # 按城市粒度导出：导出当前城市下所有区县数据，然后清空
            if EXPORT_CONFIG["unit"] == "city":
                export_verify_data(province_dir, result_excel_data)
                result_excel_data = []

        # 按省份粒度导出：导出当前省份下所有数据，然后清空
        if EXPORT_CONFIG["unit"] == "province":
            export_verify_data(province_dir, result_excel_data)
            result_excel_data = []


if __name__ == "__main__":
    main()
