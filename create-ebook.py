# /// script
# dependencies = [
#   "ebooklib",
#   "beautifulsoup4",
#   "markdown"
# ]
# ///

import os
import re
import uuid
from pathlib import Path
from typing import List, Optional
import markdown
from ebooklib import epub
from bs4 import BeautifulSoup
import json
import sys


class MarkdownToEPUB:
    """Markdown to EPUB Converter"""

    def __init__(self, title="My Book", author="Unknown", language="zh"):
        self.book = epub.EpubBook()
        self.book.set_identifier(str(uuid.uuid4()))
        self.book.set_title(title)
        self.book.set_language(language)
        self.book.add_author(author)

        self.chapters = []
        self.spine = ["nav"]

        # Configure Markdown Parser
        self.md = markdown.Markdown(
            extensions=[
                "markdown.extensions.extra",  # Support for tables, code blocks, and more.
                "markdown.extensions.codehilite",  # Code Highlighting
                "markdown.extensions.toc",  # Table of Contents
                "markdown.extensions.meta",  # Metadata Support
                "markdown.extensions.tables",  # Table Support
                "markdown.extensions.fenced_code",  # Fencing code block
            ],
            extension_configs={
                "markdown.extensions.codehilite": {
                    "css_class": "highlight",
                    "use_pygments": True,
                },
                "markdown.extensions.toc": {"permalink": True},
            },
        )

        print(f"Initializing EPUB Converter: {title}")

    def add_markdown_file(
        self, md_path: Path, chapter_title: Optional[str] = None
    ) -> bool:
        """Add a single Markdown file as a chapter."""

        try:
            with open(md_path, "r", encoding="utf-8") as f:
                md_content = f.read()

            # Parse Markdown Content
            html_content = self.md.convert(md_content)

            # Retrieve Chapter Title
            if not chapter_title:
                chapter_title = self._extract_title(md_content, md_path)

            # Retrieve metadata (if available)
            metadata = getattr(self.md, "Meta", {})

            # Create Chapter
            chapter_id = f"chapter_{len(self.chapters) + 1}"
            chapter = epub.EpubHtml(
                title=chapter_title,
                file_name=f"{chapter_id}.xhtml",
                lang=self.book.language,
            )

            # Set Chapter Content
            chapter.content = self._create_xhtml_content(html_content, chapter_title)

            # Add to Books
            self.book.add_item(chapter)
            self.chapters.append(chapter)
            self.spine.append(chapter)

            print(f"✓ Chapter added: {chapter_title} ({md_path.name})")

            # Reset Markdown Parser State
            self.md.reset()

            return True

        except Exception as e:
            print(f"✗ Failed to add file {md_path}: {e}")
            return False

    def add_image_file(self, img_path: Path, parent_path: str) -> bool:
        """Add a single image."""
        try:
            image_content = open(img_path, "rb").read()
            prefix_len = len(parent_path) + 1
            img = epub.EpubImage(
                uid=img_path.name,
                file_name=str(img_path)[prefix_len:],
                media_type=self.image_media_type(img_path),
                content=image_content,
            )
            self.book.add_item(img)
            return True

        except Exception as e:
            print(f"✗ Failed to add file {img_path}: {e}")
            return False

    def find_images_glob(self, directory):
        """Use glob to recursively find images"""

        image_patterns = [
            "**/*.jpg",
            "**/*.jpeg",
            "**/*.png",
            "**/*.gif",
            "**/*.bmp",
            "**/*.tiff",
            "**/*.webp",
            "**/*.svg",
            "**/*.JPG",
            "**/*.JPEG",
            "**/*.PNG",
            "**/*.GIF",
            "**/*.BMP",
            "**/*.TIFF",
            "**/*.WEBP",
            "**/*.SVG",
        ]

        image_files = []
        for pattern in image_patterns:
            image_files.extend(directory.glob(pattern))

        return sorted(set(image_files))

    def add_markdown_directory(
        self, directory_path: str, pattern: str = "*.md"
    ) -> bool:
        """Batch add Markdown files from the directory"""

        directory = Path(directory_path)
        if not directory.exists():
            print(f"Directory does not exist: {directory_path}")
            return False

        # Find all Markdown files
        md_files = list(directory.glob(pattern))
        md_files.extend(directory.glob("*.markdown"))

        # Sort by filename
        md_files = sorted(set(md_files), key=lambda x: self._natural_sort_key(x.name))

        if not md_files:
            print(f"No Markdown files found in {directory_path}.")
            return False

        print(f"Found {len(md_files)} Markdown files")

        success_count = 0
        for md_file in md_files:
            if self.add_markdown_file(md_file):
                success_count += 1

        print(f"Found {len(md_files)} Markdown files.")

        # Find All Images
        img_files = self.find_images_glob(directory)
        print(f"Found {len(img_files)} Image files")
        for img_file in img_files:
            self.add_image_file(img_file, directory_path)

        return success_count > 0

    def add_custom_css(self, css_content: Optional[str] = None) -> bool:
        """Add custom CSS styles"""

        if css_content is None:
            css_content = self._get_default_css()

        try:
            css_item = epub.EpubItem(
                uid="style_default",
                file_name="style/default.css",
                media_type="text/css",
                content=css_content,
            )

            self.book.add_item(css_item)

            # Apply styles to all chapters
            for chapter in self.chapters:
                chapter.add_item(css_item)

            print("✓ CSS styles have been added.")
            return True

        except Exception as e:
            print(f"✗ Failed to add CSS styles: {{e}}")
            return False

    def image_media_type(self, image_path: Path) -> str:
        ext = image_path.suffix.lower()
        if ext in [".jpg", ".jpeg"]:
            return "image/jpeg"
        elif ext == ".png":
            return "image/png"
        elif ext == ".gif":
            return "image/gif"
        else:
            print(f"Unsupported image format: {ext}")
            return "image/png"

    def add_cover_image(self, image_path: str) -> bool:
        """Add cover image"""

        try:
            image_path = Path(image_path)
            if not image_path.exists():
                print(f"Cover image not found: {image_path}")
                return False

            with open(image_path, "rb") as f:
                cover_content = f.read()

            # Determine Image Type
            media_type = self.image_media_type(image_path)

            # Set Cover
            self.book.set_cover(f"cover{ext}", cover_content)
            print(f"✓ Cover added: {image_path.name}")
            return True

        except Exception as e:
            print(f"✗ Failed to add cover: {e}")
            return False

    def _extract_title(self, md_content: str, md_path: Path) -> str:
        """Extract titles from Markdown content"""

        lines = md_content.split("\n")

        # Locate the title in the YAML front matter
        if lines and lines[0].strip() == "---":
            yaml_end = -1
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == "---":
                    yaml_end = i
                    break

            if yaml_end > 0:
                try:
                    yaml_content = "\n".join(lines[1:yaml_end])
                    metadata = yaml.safe_load(yaml_content)
                    if isinstance(metadata, dict) and "title" in metadata:
                        return str(metadata["title"])
                except:
                    pass

        # Find the First H1 Heading
        for line in lines:
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
            elif line and lines.index(line) + 1 < len(lines):
                next_line = lines[lines.index(line) + 1].strip()
                if next_line and all(c == "=" for c in next_line):
                    return line

        # Use the Filename as the Title
        return md_path.stem.replace("_", " ").replace("-", " ").title()

    def _create_xhtml_content(self, html_content: str, title: str) -> str:
        """Create XHTML content that conforms to the EPUB standard."""

        # Clean HTML Content
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove any potential first h1 tag (to avoid duplication).
        first_h1 = soup.find("h1")
        if first_h1:
            first_h1.decompose()

        cleaned_content = str(soup)
        return cleaned_content

    def _get_default_css(self) -> str:
        """Retrieve the default CSS styles"""

        return """
/* EPUB 默认样式 */
body {
    font-family: "Times New Roman", serif;
    line-height: 1.6;
    margin: 1em;
    text-align: justify;
}

h1, h2, h3, h4, h5, h6 {
    font-family: "Arial", sans-serif;
    color: #333;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
}

h1 { font-size: 2em; border-bottom: 2px solid #333; padding-bottom: 0.3em; }
h2 { font-size: 1.5em; color: #666; }
h3 { font-size: 1.3em; }

p {
    margin: 1em 0;
    text-indent: 2em;
}

blockquote {
    margin: 1em 2em;
    padding: 0.5em 1em;
    border-left: 4px solid #ddd;
    background-color: #f9f9f9;
    font-style: italic;
}

code {
    font-family: "Courier New", monospace;
    background-color: #f4f4f4;
    padding: 0.2em 0.4em;
    border-radius: 3px;
    font-size: 0.9em;
}

pre {
    background-color: #f8f8f8;
    border: 1px solid #ddd;
    border-radius: 5px;
    padding: 1em;
    overflow-x: auto;
    margin: 1em 0;
}

pre code {
    background-color: transparent;
    padding: 0;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
}

th, td {
    border: 1px solid #ddd;
    padding: 0.5em;
    text-align: left;
}

th {
    background-color: #f2f2f2;
    font-weight: bold;
}

ul, ol {
    margin: 1em 0;
    padding-left: 2em;
}

li {
    margin: 0.5em 0;
}

a {
    color: #0066cc;
    text-decoration: none;
}

a:hover {
    text-decoration: underline;
}

img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1em auto;
}

/* 代码高亮样式 */
.highlight {
    background-color: #f8f8f8;
    border: 1px solid #ddd;
    border-radius: 5px;
    padding: 1em;
    margin: 1em 0;
}
"""

    def _natural_sort_key(self, text: str) -> List:
        """Natural sorting key function"""
        return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", text)]

    def generate_epub(self, output_path: str) -> bool:
        """Generate EPUB file"""

        try:
            if not self.chapters:
                print("Unable to generate EPUB without chapter content.")
                return False

            # Add default styles
            self.add_custom_css()

            # Create Directory
            self.book.toc = [
                (epub.Link(chapter.file_name, chapter.title, chapter.id), [])
                for chapter in self.chapters
            ]

            # Add Navigation File
            self.book.add_item(epub.EpubNcx())
            self.book.add_item(epub.EpubNav())

            # Set the spine (reading order)
            self.book.spine = self.spine

            # Ensure the output directory exists
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to the EPUB file
            epub.write_epub(str(output_path), self.book, {})

            print(f"🎉 EPUB file has been successfully generated: {output_path}")
            print(f"📚 Contains {len(self.chapters)} chapters")
            print(f"📖 Title: {self.book.get_metadata('DC', 'title')[0][0]}")
            print(f"✍️ Author: {self.book.get_metadata('DC', 'creator')[0][0]}")

            return True

        except Exception as e:
            print(f"✗ Failed to generate EPUB: {e}")
            return False


def main():
    """Main function"""
    global BOOK_META
    if len(sys.argv) < 1:
        markdown_dir = "./"
    else:
        markdown_dir = sys.argv[1]
    print(f"The resource directory is located at '{markdown_dir}'.")

    # markdown_dir format
    markdown_dir = str(Path(markdown_dir))
    title = markdown_dir.split("/")[-1]
    output_file = f"./output/{title}.epub"
    author = "Unknown"
    cover_path = markdown_dir + "/cover.png"
    language = "en"

    if os.path.exists(cover_path):
        cover_image = cover_path
    else:
        cover_image = None
    BOOK_META = {}
    BOOK_META["title"] = title
    BOOK_META["output_file"] = output_file
    BOOK_META["author"] = author
    BOOK_META["cover_path"] = cover_path
    BOOK_META["language"] = language
    BOOK_META["markdown_dir"] = markdown_dir

    print("🚀 Starting the conversion of Markdown files to EPUB...")

    # Create a Converter
    converter = MarkdownToEPUB(title=title, author=author, language=language)

    # Add Markdown Files
    if not converter.add_markdown_directory(markdown_dir):
        print("❌ No processable Markdown files found, conversion terminated.")
        return

    # Add Cover (If Available)
    if cover_image:
        converter.add_cover_image(cover_image)

    # Generate EPUB File
    if converter.generate_epub(output_file):
        print("✅ Conversion successful!")
    else:
        print("❌ Conversion failed!")


if __name__ == "__main__":
    main()
