import base64
from dataclasses import dataclass, field
import io
import os
from pathlib import Path
import re
from tkinter import Image
from typing import Dict, List, Tuple
import uuid
from loguru import logger as log


@dataclass
class ImageInfo:
    """图片信息类"""

    id: str
    alt_text: str
    filepath: str
    format: str
    page_no: int
    position: int
    size_kb: float = 0.0
    metadata: Dict = field(default_factory=dict)


class Base64ImageExtractor:
    """Base64图片提取器"""

    def __init__(self, base_output_dir: str = "./extracted_images"):
        self.base_output_dir = Path(base_output_dir)
        self.base_output_dir.mkdir(exist_ok=True)
        self.extracted_images: List[ImageInfo] = []

        # 图片匹配模式
        self.patterns = [
            r"!\[(.*?)\]\(data:image/(png|jpeg|jpg);base64,([a-zA-Z0-9+/=\s]+)\)",
            r'<img\s+[^>]*src=["\']data:image/(png|jpeg|jpg);base64,([a-zA-Z0-9+/=\s]+)["\'][^>]*alt=["\']([^"\']*)["\'][^>]*>',
        ]

    def extract_from_content(
        self, content: str, page_no: int = 0
    ) -> Tuple[str, List[ImageInfo]]:
        """
        从内容中提取Base64图片

        Args:
            content: 包含base64图片的内容
            page_no: 页面编号

        Returns:
            Tuple[str, List[ImageInfo]]: (处理后的内容, 图片信息列表)
        """
        page_images = []
        processed_content = content
        offset = 0

        # 为当前页面创建图片目录
        page_dir = self.base_output_dir / f"page_{page_no}"
        page_dir.mkdir(exist_ok=True)

        # 处理所有匹配的图片
        all_matches = []
        for pattern in self.patterns:
            matches = list(re.finditer(pattern, content, re.DOTALL | re.IGNORECASE))
            all_matches.extend(matches)

        # 按位置排序
        all_matches.sort(key=lambda x: x.start())

        for match in all_matches:
            try:
                if "![" in match.group(0):  # Markdown格式
                    alt_text = match.group(1).strip()
                    img_format = match.group(2).lower()
                    base64_data = match.group(3).strip()
                else:  # HTML格式
                    alt_text = (
                        match.group(3).strip() if match.group(3) else "未命名图片"
                    )
                    img_format = match.group(1).lower()
                    base64_data = match.group(2).strip()

                # 清理base64数据（移除空格和换行）
                base64_data = re.sub(r"\s+", "", base64_data)

                # 生成唯一ID和文件名
                img_id = str(uuid.uuid4())[:8]
                filename = f"{img_id}.png"
                filepath = page_dir / filename

                # 保存图片
                # self._save_base64_image(base64_data, filepath, img_format)

                # 获取文件大小
                # size_kb = os.path.getsize(filepath) / 1024

                # 创建图片信息
                img_info = ImageInfo(
                    id=img_id,
                    alt_text=alt_text or f"图片{img_id}",
                    filepath=str(filepath),
                    format=img_format,
                    page_no=page_no,
                    position=match.start(),
                    # size_kb=size_kb,
                    metadata={
                        "original_base64_preview": (
                            base64_data[:50] + "..."
                            if len(base64_data) > 50
                            else base64_data
                        ),
                        "saved_as_png": True,
                    },
                )

                # page_images.append(img_info)
                # self.extracted_images.append(img_info)

                # 替换内容（暂时为空）
                # new_tag = f"![{img_info.alt_text}]({filepath})"
                new_tag = ""

                start_pos = match.start() + offset
                end_pos = match.end() + offset

                processed_content = (
                    processed_content[:start_pos]
                    + new_tag
                    + processed_content[end_pos:]
                )

                offset += len(new_tag) - (match.end() - match.start())

            except Exception as e:
                log.error(f"提取页面{page_no}的图片失败: {e}")
                continue

        return processed_content, page_images

    def _save_base64_image(
        self, base64_str: str, output_path: Path, original_format: str
    ):
        """保存base64图片为PNG"""
        try:
            # 解码base64
            image_data = base64.b64decode(base64_str)

            # 根据格式处理
            if original_format in ["jpeg", "jpg"]:
                img = Image.open(io.BytesIO(image_data))

                # 转换模式
                if img.mode in ("RGBA", "LA", "P"):
                    img = img.convert("RGB")

                # 保存为PNG
                img.save(output_path, "PNG", optimize=True, quality=95)
            else:
                # PNG直接保存
                with open(output_path, "wb") as f:
                    f.write(image_data)

        except Exception as e:
            log.error(f"保存图片失败 {output_path}: {e}")
            raise

    def get_statistics(self) -> Dict:
        """获取图片提取统计"""
        if not self.extracted_images:
            return {}

        total_size = sum(img.size_kb for img in self.extracted_images)
        formats = {}
        for img in self.extracted_images:
            formats[img.format] = formats.get(img.format, 0) + 1

        return {
            "total_images": len(self.extracted_images),
            "total_size_kb": round(total_size, 2),
            "formats_distribution": formats,
            "by_page": self._get_images_by_page(),
            "output_directory": str(self.base_output_dir),
        }

    def _get_images_by_page(self) -> Dict:
        """按页面统计图片"""
        by_page = {}
        for img in self.extracted_images:
            page = img.page_no
            if page not in by_page:
                by_page[page] = []
            by_page[page].append(
                {"id": img.id, "alt": img.alt_text, "file": Path(img.filepath).name}
            )
        return by_page
