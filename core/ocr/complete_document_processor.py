import json
import os
from pathlib import Path
from typing import Dict, List

from core.ocr.base64_image_extractor import Base64ImageExtractor
from core.ocr.langchain_document_converter import LangChainDocumentConverter
from core.ocr.markdown_processor import MarkdownProcessor
from langchain_core.documents import Document
from loguru import logger as log


class CompleteDocumentProcessor:
    """完整的文档处理器"""

    def __init__(
        self, output_base_dir: str = "./processed_output", file_path: str = None
    ):
        self.output_base_dir = Path(output_base_dir)
        self.output_base_dir.mkdir(exist_ok=True)
        self.file_path = file_path

        # 初始化组件
        self.image_extractor = Base64ImageExtractor(self.output_base_dir / "images")
        self.markdown_processor = MarkdownProcessor(self.image_extractor)
        self.document_converter = LangChainDocumentConverter()

        # 结果存储
        self.processed_results: Dict = {}
        self.langchain_documents: List[Document] = []

    def process_ocr_results(self, ocr_results: List[Dict]) -> Dict:
        """
        处理OCR结果

        Args:
            ocr_results: DotsOCR返回的结果列表

        Returns:
            完整的处理结果
        """
        log.debug("=" * 60)
        log.debug("开始处理OCR结果...")
        log.debug(f"总计 {len(ocr_results)} 个页面")
        log.debug("=" * 60)

        try:
            # 1. 处理每个页面
            for result in ocr_results:
                self._process_single_page(result)

            # 2. 合并所有页面
            combined_md = self.markdown_processor.combine_all_pages()

            # 创建图片索引
            image_index = self.markdown_processor.create_image_index_document()

            # 保存文件
            saved_files = self._save_output_files(combined_md, image_index)

            # 转换为LangChain Documents
            self.langchain_documents = self._create_langchain_documents(combined_md)

            # 收集统计信息
            stats = self._collect_statistics()

            # 构建返回结果
            self.processed_results = {
                "success": True,
                "statistics": stats,
                # "saved_files": saved_files,
                "langchain_documents_count": len(self.langchain_documents),
                "extracted_images_count": len(self.image_extractor.extracted_images),
                # "combined_markdown": (
                #     combined_md[:500] + "..." if len(combined_md) > 500 else combined_md
                # ),
                "image_statistics": self.image_extractor.get_statistics(),
            }

            log.debug("" + "=" * 60)
            log.debug("处理完成!")
            log.debug(f"生成 {len(self.langchain_documents)} 个LangChain文档")
            log.debug(f"提取 {len(self.image_extractor.extracted_images)} 张图片")
            log.debug("=" * 60)

            return self.processed_results

        except Exception as e:
            print(f"处理失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "langchain_documents": [],
                "statistics": {},
            }

    def _process_single_page(self, ocr_result: Dict):
        """处理单个页面"""
        page_no = ocr_result.get("page_no", 0)

        # 读取Markdown内容
        md_path = ocr_result.get("md_content_nohf_path")
        if not md_path or not os.path.exists(md_path):
            print(f"  跳过: Markdown文件不存在")
            return

        with open(md_path, "r", encoding="utf-8") as f:
            original_content = f.read()

        # 构建页面元数据
        source_info = {
            "page_number": page_no + 1,
            "original_file": ocr_result.get("file_path", ""),
            "layout_json": ocr_result.get("layout_info_path", ""),
            "original_md_path": md_path,
            "input_dimensions": f"{ocr_result.get('input_width', 0)}x{ocr_result.get('input_height', 0)}",
        }

        # 处理页面
        page_info = self.markdown_processor.process_page(
            page_no=page_no, markdown_content=original_content, source_info=source_info
        )

    @property
    def filename(self):
        basename = os.path.basename(self.file_path)
        filename_without_ext = os.path.splitext(basename)[0]
        return filename_without_ext

    @property
    def filename_ext(self):
        basename = os.path.basename(self.file_path)
        return basename

    def _save_output_files(self, combined_md: str, image_index: str) -> Dict:
        """保存输出文件"""
        saved = {}

        # 保存合并的Markdown
        combined_path = self.output_base_dir / self.filename / "combined_document.md"
        combined_path.parent.mkdir(parents=True, exist_ok=True)
        with open(combined_path, "w", encoding="utf-8") as f:
            f.write(combined_md)
        saved["combined_markdown"] = str(combined_path)

        # 保存图片索引
        if image_index:
            index_path = self.output_base_dir / self.filename / "image_index.md"
            index_path.parent.mkdir(parents=True, exist_ok=True)
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(image_index)
            saved["image_index"] = str(index_path)

        # 保存处理配置
        config = {
            "output_directory": str(self.output_base_dir),
            "processor_version": "1.0.0",
            "components": {
                "image_extractor": "Base64ImageExtractor",
                "markdown_processor": "MarkdownProcessor",
                "document_converter": "LangChainDocumentConverter",
            },
        }
        config_path = self.output_base_dir / self.filename / "processor_config.json"
        combined_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        saved["config"] = str(config_path)

        return saved

    def _create_langchain_documents(self, combined_md: str) -> List[Document]:
        """创建LangChain文档"""
        # 基础元数据
        base_metadata = {
            "processed_by": "CompleteDocumentProcessor",
            "has_images": len(self.image_extractor.extracted_images) > 0,
            "total_images": len(self.image_extractor.extracted_images),
            "total_pages": len(self.markdown_processor.processed_pages),
        }

        # 转换主文档
        main_documents = self.document_converter.convert_to_documents(
            markdown_content=combined_md, metadata=base_metadata
        )

        # 创建图片文档
        # image_documents = self.document_converter.create_image_documents(
        #     image_infos=self.image_extractor.extracted_images,
        #     parent_metadata=base_metadata,
        # )

        # return main_documents + image_documents
        return main_documents

    def _collect_statistics(self) -> Dict:
        """收集统计信息"""
        total_text_length = sum(
            len(doc.page_content) for doc in self.langchain_documents
        )

        doc_types = {}
        for doc in self.langchain_documents:
            doc_type = doc.metadata.get("document_type", "text")
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1

        return {
            "total_documents": len(self.langchain_documents),
            "total_text_characters": total_text_length,
            "document_types": doc_types,
            "pages_processed": len(self.markdown_processor.processed_pages),
            "avg_document_length": (
                total_text_length // len(self.langchain_documents)
                if self.langchain_documents
                else 0
            ),
        }
