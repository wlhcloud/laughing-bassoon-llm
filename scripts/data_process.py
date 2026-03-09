import pandas as pd
import os
from loguru import logger as log

from utils.file_utils import get_dir_name


def read_excel_get_notices(file_path, sheet_name="Sheet1", check_col=1):
    """
    将通知名称与对应的文保单位信息匹配
    :param file_path: Excel文件完整路径
    :param sheet_name: 工作表名称
    :param check_col: 要校验是否为数字的列索引（从0开始，比如1=第二列）
    :return: 字典，key=通知名称，value=对应文保单位列表
    """
    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
    df = df.dropna(how="all")
    df = df.reset_index(drop=True)

    # 存储最终结果：通知名称 -> 文保单位列表
    result = {}
    current_notice = None  # 记录当前匹配的通知名称
    allow_append = False  # 标记：是否允许当前通知接收文保单位数据

    for idx, row in df.iterrows():
        notice_check_content = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""

        if (
            "关于" in notice_check_content
            or "通知" in notice_check_content
            or "保护单位" in notice_check_content
        ) and len(notice_check_content) < 100:
            current_notice = notice_check_content
            result[current_notice] = []

            if idx + 1 < len(df):  # 确保下一行存在
                next_row_check_col = (
                    str(df.iloc[idx + 1, check_col]).strip()
                    if pd.notna(df.iloc[idx + 1, check_col])
                    else ""
                )
                allow_append = next_row_check_col.replace(".", "").isdigit()
            else:
                allow_append = False

        else:
            current_check_content = (
                str(row.iloc[check_col]).strip()
                if pd.notna(row.iloc[check_col])
                else ""
            )

            if (
                current_notice is not None
                and allow_append
                and current_check_content != ""
                and current_check_content.replace(".", "").isdigit()
            ):

                wenbao_info = [
                    str(cell).strip() if pd.notna(cell) else "" for cell in row
                ]
                result[current_notice].append(wenbao_info)

    result = {notice: wb_list for notice, wb_list in result.items() if len(wb_list) > 0}
    log.info(f"识别到通知行：{result.keys()}")
    return result


def export_verify_data(export_dir, result_data):
    """
    导出验证的文保单位数据
    province_dir: 省文件夹
    """
    base_name = get_dir_name(export_dir)
    # 8. 生成Excel文件
    if result_data:
        # 创建DataFrame
        df = pd.DataFrame(result_data)
        # 按指定列顺序排列
        column_order = [
            "省",
            "市",
            "区/县",
            "通知",
            "公布名录中的单位名称",
            "公布名录中的单位地址",
            "公布文件中的单位名称",
            "公布文件中的单位地址",
            "单位名称相似度",
            "单位名称是否匹配",
            "单位地址相似度",
            "单位地址是否匹配",
        ]
        df = df[column_order]

        # 生成Excel文件路径（保存到区县目录下）
        excel_output_path = os.path.join(
            export_dir, f"{base_name}_文保单位匹配结果.xlsx"
        )

        # 写入Excel（不包含索引）
        try:
            df.to_excel(excel_output_path, index=False, engine="openpyxl")
            log.success(f"Excel文件已生成：{excel_output_path}")
        except Exception as e:
            log.error(f"生成Excel失败：{str(e)}", exc_info=True)
    else:
        log.warning(f"{base_name} 无有效数据，未生成Excel文件")
