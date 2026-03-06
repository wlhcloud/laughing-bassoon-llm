import os
import json
from typing import List, Dict, Optional, Tuple
from langchain_core.documents import Document
import torch
from core.ocr.dots_ocr.parser import DotsOCRParser
from core.ocr.complete_document_processor import CompleteDocumentProcessor
from loguru import logger as log


class OCRDocumentProcessor:
    """OCR文档处理器"""

    def __init__(self):
        # 获取OCR配置
        self._orc_url = "www.wlhcloud.top"
        self._orc_port = 9114
        self._orc_api_key = "fsfsdfsdfdsfsdf"
        self._ocr_model_name = "dots_ocr"

    def parse_pdf_with_ocr(
        self, pdf_path: str, output_dir: str = "./ocr_output"
    ) -> Dict:
        """
        使用DotsOCR解析PDF文件

        Args:
            pdf_path: PDF文件路径
            output_dir: 输出目录

        Returns:
            OCR解析结果
        """
        try:
            # 创建DotsOCR解析器实例
            dots_ocr_parser = DotsOCRParser(
                ip=self._orc_url,
                port=self._orc_port,
                model_name=self._ocr_model_name,
                temperature=0.1,
                top_p=1.0,
                max_completion_tokens=16384,
                num_thread=32,
                dpi=200,
                output_dir=output_dir,
            )

            # 解析文件
            result = dots_ocr_parser.parse_file(
                pdf_path,
                prompt_mode="prompt_layout_all_en",  # 或根据需求选择
                fitz_preprocess=True,
            )

            return result

        except Exception as e:
            log.error(f"OCR解析失败 {pdf_path}: {e}")
            raise

    def process_pdf_to_documents(self, pdf_path: str) -> Tuple[List[Document], Dict]:
        """
        将PDF转换为LangChain Documents（包含图片处理）

        Args:
            pdf_path: PDF文件路径

        Returns:
            Tuple[List[Document], Dict]: (文档列表, 处理统计)
        """
        try:
            # 初始化处理器
            complete_processor = CompleteDocumentProcessor(file_path=pdf_path)
            log.info(f"开始OCR处理PDF: {pdf_path}")

            # 1. 使用DotsOCR解析PDF
            ocr_results = self.parse_pdf_with_ocr(pdf_path)

            if not ocr_results:
                raise ValueError(f"OCR解析返回空结果: {pdf_path}")

            # 2. 使用完整处理器处理图片和文档
            complete_result = complete_processor.process_ocr_results(ocr_results)

            if not complete_result["success"]:
                raise ValueError(
                    f"文档处理失败: {complete_result.get('error', '未知错误')}"
                )

            # 3. 获取处理后的文档
            documents = complete_processor.langchain_documents

            # 4. 添加额外的元数据
            for doc in documents:
                if "source" not in doc.metadata:
                    doc.metadata["source"] = os.path.basename(pdf_path)
                doc.metadata["processed_by"] = "OCR"
                doc.metadata["file_type"] = "pdf_ocr"

            log.info(f"OCR处理完成: 生成 {len(documents)} 个文档")

            return documents, {
                "ocr_pages": complete_result.get("statistics", {}).get("ocr_pages", 0),
                "processed_documents": len(documents),
                "extracted_images": len(
                    complete_processor.image_extractor.extracted_images
                ),
                "success": True,
            }

        except Exception as e:
            log.error(f"PDF OCR处理失败 {pdf_path}: {e}")
            return [], {"success": False, "error": str(e)}

    def __del__(self):
        """析构函数：实例销毁时自动清理显存（销毁钩子）"""
        try:
            if hasattr(self, "_temp_parser") and self._temp_parser is not None:
                del self._temp_parser
            if hasattr(self, "_temp_processor") and self._temp_processor is not None:
                del self._temp_processor
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
            log.info("OCRDocumentProcessor实例已销毁，显存已清理")
        except Exception as e:
            log.warning(f"析构函数清理显存时出错: {e}")
