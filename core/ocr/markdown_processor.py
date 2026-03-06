from typing import Dict, List
from core.ocr.base64_image_extractor import Base64ImageExtractor


class MarkdownProcessor:
    """Markdown文档处理器"""

    def __init__(self, image_extractor: Base64ImageExtractor = None):
        self.image_extractor = image_extractor or Base64ImageExtractor()
        self.processed_pages: List[Dict] = []

    def process_page(
        self, page_no: int, markdown_content: str, source_info: Dict = None
    ) -> Dict:
        """
        处理单个页面

        Args:
            page_no: 页面编号
            markdown_content: Markdown内容
            source_info: 来源信息

        Returns:
            处理后的页面信息
        """
        # 提取图片
        processed_content, extracted_images = self.image_extractor.extract_from_content(
            markdown_content, page_no
        )

        # 构建页面信息
        page_info = {
            "page_no": page_no,
            "original_content_length": len(markdown_content),
            "processed_content_length": len(processed_content),
            "has_images": len(extracted_images) > 0,
            "image_count": len(extracted_images),
            "extracted_images": [
                {
                    "id": img.id,
                    "alt_text": img.alt_text,
                    "filepath": img.filepath,
                    "size_kb": img.size_kb,
                }
                for img in extracted_images
            ],
            "processed_content": processed_content,
            "source_info": source_info or {},
        }

        self.processed_pages.append(page_info)
        return page_info

    def combine_all_pages(
        self, include_page_breaks: bool = False, include_image_index: bool = False
    ) -> str:
        """合并所有页面"""
        combined_parts = []

        for i, page_info in enumerate(
            sorted(self.processed_pages, key=lambda x: x["page_no"])
        ):
            content = page_info["processed_content"]

            combined_parts.append(content)

            # 添加图片索引（如果有）
            if include_image_index and page_info["extracted_images"]:
                combined_parts.append(f"\n\n**本页图片索引:**\n")
                for img in page_info["extracted_images"]:
                    combined_parts.append(
                        f"- ![{img['alt_text']}]({img['filepath']})\n"
                    )

        return "".join(combined_parts)

    def create_image_index_document(self) -> str:
        """创建图片索引文档"""
        if not self.image_extractor.extracted_images:
            return ""

        index_content = "# 文档图片索引\n\n"
        index_content += (
            f"总计: {len(self.image_extractor.extracted_images)} 张图片\n\n"
        )

        # 按页面分组
        images_by_page = {}
        for img in self.image_extractor.extracted_images:
            page = img.page_no
            if page not in images_by_page:
                images_by_page[page] = []
            images_by_page[page].append(img)

        for page_no in sorted(images_by_page.keys()):
            index_content += f"## 第 {page_no+1} 页\n\n"

            for img in images_by_page[page_no]:
                index_content += f"### 图片 {img.id}\n"
                index_content += f"- **描述**: {img.alt_text}\n"
                index_content += f"- **文件**: {img.filepath}\n"
                index_content += f"- **格式**: {img.format.upper()} → PNG\n"
                index_content += f"- **大小**: {img.size_kb:.1f} KB\n\n"

        return index_content
