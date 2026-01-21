"""
Book text extraction script for research library.

Extracts text from PDFs and EPUBs, organizing by chapter/section.
Outputs structured markdown files for model consumption.

Usage:
    python -m research.books.scripts.extract_books [--book BOOK_ID] [--all]
"""

import json
import re
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# Optional imports - gracefully handle missing packages
try:
    import fitz  # PyMuPDF - better than PyPDF2 for text extraction
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from ebooklib import epub, ITEM_DOCUMENT
    from bs4 import BeautifulSoup
    HAS_EPUB = True
except ImportError:
    HAS_EPUB = False


BOOKS_DIR = Path(__file__).parent.parent
INDEX_FILE = BOOKS_DIR / "index" / "book_index.json"
EXTRACTS_DIR = BOOKS_DIR / "extracts"

# Custom chapter configurations for books with non-standard formats
# Maps book_id -> list of chapter titles in order
BOOK_CHAPTER_CONFIG = {
    "complete_offensive_line": [
        "Characteristics of Offensive Linemen",
        "Stances",
        "Drive Blocks",
        "Reach Blocks",
        "Cutoff Blocks",
        "Down Blocks",
        "Combination Blocks",
        "Stretch Plays",
        "Inside Zone",
        "Option",
        "Pass Protection",
        "Pass Progression and Drills",
        "Conditioning and Core Work",
    ],
    "coaching_offensive_linemen": [
        "Selecting the Offensive Lineman",
        "Fundamental Concepts for Offensive Line Play",
        "Presnap Fundamentals and the Exchange",
        "One-Man Blocks",
        "Two-Man Blocks",
        "Pull Blocks",
        "Run-Blocking Drills",
        "Pass Blocking",
        "Pass-Blocking Drills",
        "Goal Line Blocking",
        "Offensive Linemen in the Kicking Game",
        "Run-Blocking Schemes",
        "Adopting an Alignment Philosophy",
    ],
    "coaching_linebackers": [
        "What Makes a Good Linebacker Coach?",
        "What Makes a Good Linebacker?",
        "A Basic Game Plan for Success",
        # Note: Some titles have OCR variations - using partial matches
        "How to Play the",  # Matches "Split 6/G" chapter
        "How to Play",      # Matches "Linebacker in Special Defenses"
        "What Are The Fundamentals",
        "Drills",           # Matches both Individual and Group drills sections
        "How to Keep Your Players",
        "How to Prepare for the Moment",
        "How to Deal With the Moment",
        "How to Evaluate Your Players",
        "How to Condition Your Players",
        "Eat to Compete",
    ],
}


@dataclass
class Chapter:
    """A chapter or section from a book."""
    title: str
    number: Optional[int] = None
    content: str = ""
    page_start: Optional[int] = None
    page_end: Optional[int] = None


@dataclass
class ExtractedBook:
    """Full extracted content from a book."""
    id: str
    title: str
    author: str
    chapters: list[Chapter] = field(default_factory=list)
    raw_text: str = ""
    format: str = ""


def load_book_index() -> dict:
    """Load the book index JSON."""
    with open(INDEX_FILE) as f:
        return json.load(f)


def split_by_chapter_config(raw_text: str, book_id: str) -> list[Chapter]:
    """Split extracted text using custom chapter configuration."""
    chapter_titles = BOOK_CHAPTER_CONFIG.get(book_id, [])
    if not chapter_titles:
        return []

    chapters = []
    lines = raw_text.split('\n')

    # Find each chapter start position
    chapter_starts = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        for idx, title in enumerate(chapter_titles):
            # Match chapter title at start of line
            # Use startswith for partial matching (handles OCR variations)
            if stripped.startswith(title):
                chapter_starts.append((i, idx, stripped))  # Use actual line as title
                break

    # Remove duplicates (keep first occurrence that isn't in TOC area)
    # TOC entries are usually in first 100-200 lines
    seen = set()
    filtered_starts = []
    for line_num, ch_idx, title in chapter_starts:
        if ch_idx not in seen and line_num > 200:  # Skip TOC area
            seen.add(ch_idx)
            filtered_starts.append((line_num, ch_idx, title))

    # Sort by position in book
    filtered_starts.sort(key=lambda x: x[0])

    # Extract chapter content
    for i, (start_line, ch_idx, title) in enumerate(filtered_starts):
        # Chapter ends at next chapter start or end of file
        if i + 1 < len(filtered_starts):
            end_line = filtered_starts[i + 1][0]
        else:
            end_line = len(lines)

        content = '\n'.join(lines[start_line:end_line])

        chapter = Chapter(
            title=title,
            number=ch_idx + 1,
            content=content
        )
        chapters.append(chapter)

    return chapters


def extract_pdf(filepath: Path, book_meta: dict) -> ExtractedBook:
    """Extract text from a PDF file using PyMuPDF."""
    if not HAS_PYMUPDF:
        print("  ERROR: PyMuPDF not installed. Run: pip install pymupdf")
        return None

    doc = fitz.open(filepath)

    book = ExtractedBook(
        id=book_meta["id"],
        title=book_meta["title"],
        author=book_meta["author"],
        format="pdf"
    )

    full_text = []
    current_chapter = None
    chapter_pattern = re.compile(
        r'^(CHAPTER|Chapter|PART|Part)\s*(\d+|[IVX]+)[:\s]*(.*)$',
        re.MULTILINE
    )

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        full_text.append(text)

        # Look for chapter headings
        for match in chapter_pattern.finditer(text):
            chapter_type = match.group(1)
            chapter_num = match.group(2)
            chapter_title = match.group(3).strip()

            # Save previous chapter
            if current_chapter and current_chapter.content.strip():
                current_chapter.page_end = page_num
                book.chapters.append(current_chapter)

            # Start new chapter
            try:
                num = int(chapter_num)
            except ValueError:
                # Roman numeral - convert
                roman_map = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
                             'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10}
                num = roman_map.get(chapter_num, 0)

            current_chapter = Chapter(
                title=f"{chapter_type} {chapter_num}: {chapter_title}" if chapter_title else f"{chapter_type} {chapter_num}",
                number=num,
                page_start=page_num + 1
            )

        # Add text to current chapter
        if current_chapter:
            current_chapter.content += text + "\n"

    # Save final chapter
    if current_chapter and current_chapter.content.strip():
        current_chapter.page_end = len(doc)
        book.chapters.append(current_chapter)

    book.raw_text = "\n".join(full_text)
    doc.close()

    # Prefer custom config if available (more reliable than OCR-based pattern matching)
    if book_meta["id"] in BOOK_CHAPTER_CONFIG and BOOK_CHAPTER_CONFIG[book_meta["id"]]:
        print("  Using custom chapter configuration...")
        book.chapters = split_by_chapter_config(book.raw_text, book_meta["id"])

    return book


def extract_epub(filepath: Path, book_meta: dict) -> ExtractedBook:
    """Extract text from an EPUB file."""
    if not HAS_EPUB:
        print("  ERROR: ebooklib not installed. Run: pip install ebooklib beautifulsoup4")
        return None

    epub_book = epub.read_epub(filepath)

    book = ExtractedBook(
        id=book_meta["id"],
        title=book_meta["title"],
        author=book_meta["author"],
        format="epub"
    )

    full_text = []
    chapter_num = 0

    for item in epub_book.get_items():
        if item.get_type() == ITEM_DOCUMENT:
            # Parse HTML content
            soup = BeautifulSoup(item.get_content(), 'html.parser')

            # Get title from h1/h2 tags
            title_tag = soup.find(['h1', 'h2'])
            title = title_tag.get_text().strip() if title_tag else f"Section {chapter_num + 1}"

            # Get text content
            text = soup.get_text(separator='\n')
            text = re.sub(r'\n{3,}', '\n\n', text)  # Normalize whitespace

            if text.strip():
                chapter_num += 1
                chapter = Chapter(
                    title=title,
                    number=chapter_num,
                    content=text
                )
                book.chapters.append(chapter)
                full_text.append(text)

    book.raw_text = "\n\n".join(full_text)

    return book


def save_extracted_book(book: ExtractedBook):
    """Save extracted book to markdown files."""
    book_dir = EXTRACTS_DIR / book.id
    book_dir.mkdir(parents=True, exist_ok=True)

    # Save full text
    full_path = book_dir / "full_text.md"
    with open(full_path, 'w') as f:
        f.write(f"# {book.title}\n\n")
        f.write(f"**Author:** {book.author}\n\n")
        f.write("---\n\n")
        f.write(book.raw_text)

    # Save individual chapters
    if book.chapters:
        chapters_dir = book_dir / "chapters"
        chapters_dir.mkdir(exist_ok=True)

        for chapter in book.chapters:
            # Create safe filename
            safe_title = re.sub(r'[^\w\s-]', '', chapter.title)[:50]
            safe_title = re.sub(r'\s+', '_', safe_title).lower()
            filename = f"{chapter.number:02d}_{safe_title}.md" if chapter.number else f"{safe_title}.md"

            chapter_path = chapters_dir / filename
            with open(chapter_path, 'w') as f:
                f.write(f"# {chapter.title}\n\n")
                if chapter.page_start:
                    f.write(f"*Pages {chapter.page_start}-{chapter.page_end}*\n\n")
                f.write("---\n\n")
                f.write(chapter.content)

        # Save chapter index
        index_path = book_dir / "chapters.json"
        with open(index_path, 'w') as f:
            chapters_data = [
                {
                    "number": c.number,
                    "title": c.title,
                    "page_start": c.page_start,
                    "page_end": c.page_end,
                    "word_count": len(c.content.split())
                }
                for c in book.chapters
            ]
            json.dump(chapters_data, f, indent=2)

    print(f"  Saved to {book_dir}/")
    print(f"    - full_text.md ({len(book.raw_text):,} chars)")
    print(f"    - {len(book.chapters)} chapters")


def extract_book(book_id: str, index: dict) -> Optional[ExtractedBook]:
    """Extract a single book by ID."""
    book_meta = None
    for book in index["books"]:
        if book["id"] == book_id:
            book_meta = book
            break

    if not book_meta:
        print(f"Book not found: {book_id}")
        return None

    filepath = BOOKS_DIR / book_meta["filename"]
    if not filepath.exists():
        print(f"File not found: {filepath}")
        return None

    print(f"Extracting: {book_meta['title']}")
    print(f"  File: {book_meta['filename'][:60]}...")

    if book_meta["format"] == "pdf":
        return extract_pdf(filepath, book_meta)
    elif book_meta["format"] == "epub":
        return extract_epub(filepath, book_meta)
    else:
        print(f"  Unknown format: {book_meta['format']}")
        return None


def extract_all_books():
    """Extract all books in the index."""
    index = load_book_index()

    for book_meta in index["books"]:
        print(f"\n{'='*60}")
        extracted = extract_book(book_meta["id"], index)
        if extracted:
            save_extracted_book(extracted)


def extract_by_topic(topic: str, index: dict) -> list[str]:
    """Get book IDs relevant to a topic."""
    topic_data = index.get("topic_index", {}).get(topic)
    if topic_data:
        return topic_data.get("sources", [])
    return []


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Extract text from research books")
    parser.add_argument("--book", help="Extract specific book by ID")
    parser.add_argument("--all", action="store_true", help="Extract all books")
    parser.add_argument("--topic", help="Extract books for a topic (e.g., ol_techniques)")
    parser.add_argument("--list", action="store_true", help="List available books")
    parser.add_argument("--check-deps", action="store_true", help="Check dependencies")

    args = parser.parse_args()

    if args.check_deps:
        print("Dependency check:")
        print(f"  PyMuPDF (PDF): {'✓ installed' if HAS_PYMUPDF else '✗ missing - pip install pymupdf'}")
        print(f"  ebooklib (EPUB): {'✓ installed' if HAS_EPUB else '✗ missing - pip install ebooklib beautifulsoup4'}")
        return

    index = load_book_index()

    if args.list:
        print("Available books:")
        for book in index["books"]:
            print(f"  {book['id']}: {book['title']} ({book['format']})")
        return

    if args.book:
        extracted = extract_book(args.book, index)
        if extracted:
            save_extracted_book(extracted)
    elif args.topic:
        book_ids = extract_by_topic(args.topic, index)
        if not book_ids:
            print(f"No books found for topic: {args.topic}")
            return
        print(f"Extracting {len(book_ids)} books for topic: {args.topic}")
        for book_id in book_ids:
            extracted = extract_book(book_id, index)
            if extracted:
                save_extracted_book(extracted)
    elif args.all:
        extract_all_books()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
