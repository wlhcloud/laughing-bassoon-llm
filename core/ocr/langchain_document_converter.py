import os
from re import S
from typing import Dict, List
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from langchain_core.documents import Document

from core.ocr.base64_image_extractor import ImageInfo


class LangChainDocumentConverter:
    """LangChain文档转换器"""

    def __init__(self):
        self.chunk_size = 500
        self.chunk_overlap = 50
        # Markdown标题分割器配置
        self.header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "H1"),
                ("##", "H2"),
                ("###", "H3"),
            ],
            strip_headers=False,
        )
        separators_long_str = r"\n\n||\n\t||\n# ||\n## ||\n### ||\n#### ||\n##### ||\n- ||\n* ||\n1. ||\n2. ||\n3. ||\n> ||```||\n```||\n·||\n●||\n■||\n【||\n】||\n「||\n」||\n《||\n》||。||！||？||；||：||……||—||～||，||、|| ||\t||"
        separators = [sep for sep in separators_long_str.split("||") if sep]
        self.recursive_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=separators,
            keep_separator=True,
        )

    def convert_to_documents(
        self, markdown_content: str, metadata: Dict = None
    ) -> List[Document]:
        """
        将Markdown内容转换为LangChain Documents

        Args:
            markdown_content: Markdown内容
            metadata: 基础元数据

        Returns:
            List[Document]: LangChain文档列表
        """
        base_metadata = metadata.copy() if metadata else {}

        # 1. 首先按标题分割
        header_docs = self.header_splitter.split_text(markdown_content)

        # 2. 进一步分割过长的文档
        all_documents = []

        for i, doc in enumerate(header_docs):
            doc_metadata = doc.metadata.copy()
            doc_metadata.update(base_metadata)
            doc_metadata.update(
                {
                    "chunk_index": i,
                    "total_chunks": len(header_docs),
                    "split_by": "headers",
                }
            )

            # 如果文档太长，进一步分割
            if len(doc.page_content) > 1000:
                sub_docs = self.recursive_splitter.split_documents([doc])

                for j, sub_doc in enumerate(sub_docs):
                    sub_metadata = sub_doc.metadata.copy()
                    sub_metadata.update(doc_metadata)
                    sub_metadata.update(
                        {
                            "sub_chunk_index": j,
                            "total_sub_chunks": len(sub_docs),
                            "parent_chunk": i,
                        }
                    )

                    final_doc = Document(
                        page_content=sub_doc.page_content, metadata=sub_metadata
                    )
                    all_documents.append(final_doc)
            else:
                final_doc = Document(
                    page_content=doc.page_content, metadata=doc_metadata
                )
                all_documents.append(final_doc)

        return all_documents

    def create_image_documents(
        self, image_infos: List[ImageInfo], parent_metadata: Dict = None
    ) -> List[Document]:
        """
        创建图片描述文档

        Args:
            image_infos: 图片信息列表
            parent_metadata: 父文档元数据

        Returns:
            图片文档列表
        """
        image_docs = []

        for img_info in image_infos:
            # 构建图片描述内容
            content = self._create_image_description(img_info)

            metadata = {
                "document_type": "image_description",
                "content_type": "image",
                "image_id": img_info.id,
                "image_alt": img_info.alt_text,
                "image_path": img_info.filepath,
                "image_page": img_info.page_no,
                "image_format": img_info.format,
                "image_size_kb": img_info.size_kb,
                "is_image_document": True,
                "from_base64": True,
            }

            if parent_metadata:
                metadata.update(parent_metadata)

            doc = Document(page_content=content, metadata=metadata)
            image_docs.append(doc)

        return image_docs

    def _create_image_description(self, img_info: ImageInfo) -> str:
        """创建图片描述"""
        description = f"""
图片ID: {img_info.id}
描述: {img_info.alt_text}
所在页面: 第{img_info.page_no + 1}页
文件路径: {img_info.filepath}
原始格式: {img_info.format.upper()}
文件大小: {img_info.size_kb:.1f} KB

图片内容说明:
- 该图片为{os.path.basename(img_info.filepath)}中的插图
- 已从Base64格式提取并保存为PNG文件
- 可能是文物照片、线图、帛画细节等考古资料
"""
        return description.strip()
