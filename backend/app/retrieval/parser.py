from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader


@dataclass(frozen=True)
class TextPage:
    text: str
    page_number: int | None = None


@dataclass(frozen=True)
class TextChunk:
    content: str
    page_number: int | None
    section: str | None
    start_offset: int
    end_offset: int
    context_before: str = ""
    context_after: str = ""


CONTENT_TYPES = {
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def content_type_for(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in CONTENT_TYPES:
        raise ValueError("仅支持 TXT、Markdown、文字型 PDF、PNG、JPEG 和 WebP")
    return CONTENT_TYPES[suffix]


def parse_source(data: bytes, filename: str) -> list[TextPage]:
    content_type = content_type_for(filename)
    if content_type.startswith("image/"):
        raise ValueError("图片须经视觉模型解析")
    if content_type == "application/pdf":
        if not data.startswith(b"%PDF-"):
            raise ValueError("文件内容不是有效 PDF")
        try:
            reader = PdfReader(BytesIO(data), strict=False)
            pages = [
                TextPage(page.extract_text() or "", number)
                for number, page in enumerate(reader.pages, 1)
            ]
        except Exception as exc:
            raise ValueError("PDF 解析失败") from exc
    else:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("文本文件必须采用 UTF-8 编码") from exc
        if "\x00" in text:
            raise ValueError("文本文件包含无效字符")
        pages = [TextPage(text)]
    if not any(page.text.strip() for page in pages):
        raise ValueError("未提取到文字；当前不支持扫描件 OCR")
    return pages


def split_pages(pages: list[TextPage], max_chars: int = 900, overlap: int = 120) -> list[TextChunk]:
    if max_chars <= overlap or overlap < 0:
        raise ValueError("切片长度必须大于重叠长度")
    chunks: list[TextChunk] = []
    for page in pages:
        text = page.text
        start = 0
        while start < len(text):
            end = min(start + max_chars, len(text))
            if end < len(text):
                candidates = [
                    text.rfind(mark, start + max_chars // 2, end)
                    for mark in ("\n\n", "\n", "。", "！", "？", ". ")
                ]
                boundary = max(candidates)
                if boundary > start:
                    end = boundary + (2 if text[boundary : boundary + 2] in ("\n\n", ". ") else 1)
            raw = text[start:end]
            left = len(raw) - len(raw.lstrip())
            right = len(raw.rstrip())
            if right > left:
                chunk_start = start + left
                chunk_end = start + right
                section = None
                if page.page_number is None:
                    headings = [
                        line.lstrip("# ").strip()
                        for line in text[:chunk_start].splitlines()
                        if line.startswith("#")
                    ]
                    section = headings[-1][:255] if headings else None
                chunks.append(
                    TextChunk(
                        text[chunk_start:chunk_end],
                        page.page_number,
                        section,
                        chunk_start,
                        chunk_end,
                        text[max(0, chunk_start - 180) : chunk_start].strip(),
                        text[chunk_end : min(len(text), chunk_end + 180)].strip(),
                    )
                )
            if end == len(text):
                break
            start = max(end - overlap, start + 1)
    return chunks
