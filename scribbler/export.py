#!/usr/bin/env python3
"""Export module for The Audhd Scribbler.

Exports tagged files and analysis results to various formats:
- Markdown (clean, with frontmatter)
- DOCX (Word document)
- Plain text (stripped of metadata)
"""
import json
import re
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from .config import PROJECT_ROOT
from .file_io import read_text_file, write_text_file
from . import db


def export_markdown(file_path: str, output_path: str = None) -> str:
    """Export a file as clean markdown (preserves YAML frontmatter)."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    content = read_text_file(path)

    if output_path is None:
        output_path = str(PROJECT_ROOT / "data" / "exports" / f"{path.stem}.md")

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_text_file(out_path, content)
    return str(out_path)


def export_plain_text(file_path: str, output_path: str = None) -> str:
    """Export a file as plain text (strips YAML frontmatter and summary comments)."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    content = read_text_file(path)

    # Strip YAML frontmatter
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            content = content[end + 3:].strip()

    # Strip summary comments
    content = re.sub(r'<!-- SCRIBBLER SUMMARY[\s\S]*?-->', '', content).strip()

    if output_path is None:
        output_path = str(PROJECT_ROOT / "data" / "exports" / f"{path.stem}.txt")

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_text_file(out_path, content)
    return str(out_path)


def export_docx(file_path: str, output_path: str = None) -> str:
    """Export a file as a Word document."""
    try:
        from docx import Document
        from docx.shared import Pt, Inches
    except ImportError:
        raise ImportError(
            "python-docx not installed. Install with: pip install python-docx"
        )

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    content = read_text_file(path)

    # Strip YAML frontmatter for the DOCX body
    body_text = content
    if body_text.startswith("---"):
        end = body_text.find("---", 3)
        if end != -1:
            body_text = body_text[end + 3:].strip()

    # Strip summary comments
    body_text = re.sub(r'<!-- SCRIBBLER SUMMARY[\s\S]*?-->', '', body_text).strip()

    if output_path is None:
        output_path = str(PROJECT_ROOT / "data" / "exports" / f"{path.stem}.docx")

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    doc = Document()

    # Set default font
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)

    # Add title (filename without extension)
    title = path.stem.replace('-', ' ').replace('_', ' ').title()
    heading = doc.add_heading(title, level=1)

    # Split into paragraphs and add
    paragraphs = re.split(r'\n\s*\n', body_text)
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        # Check if it's a heading (starts with #)
        if para.startswith('# '):
            doc.add_heading(para[2:], level=1)
        elif para.startswith('## '):
            doc.add_heading(para[3:], level=2)
        elif para.startswith('### '):
            doc.add_heading(para[4:], level=3)
        else:
            # Regular paragraph
            p = doc.add_paragraph(para)

    doc.save(str(out_path))
    return str(out_path)


def export_analysis_report(file_path: str, analysis_results: Dict, output_path: str = None) -> str:
    """Export analysis results as a formatted markdown report."""
    path = Path(file_path)

    if output_path is None:
        output_path = str(PROJECT_ROOT / "data" / "reports" / f"{path.stem}_analysis.md")

    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append(f"# Analysis Report: {path.name}")
    lines.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")

    for analysis_type, result in analysis_results.items():
        lines.append(f"\n---\n\n## {analysis_type.title()}\n")

        if isinstance(result, dict):
            if "summary" in result:
                lines.append(f"\n{result['summary']}\n")

            if "strengths" in result:
                lines.append("\n### Strengths\n")
                for s in result["strengths"]:
                    lines.append(f"- {s}")

            if "observations" in result:
                lines.append("\n### Observations\n")
                for obs in result["observations"]:
                    if isinstance(obs, dict):
                        lines.append(f"\n**{obs.get('category', '').replace('_', ' ').title()}** ({obs.get('location', '')})")
                        lines.append(f"\n{obs.get('formatted', '')}\n")
                    else:
                        lines.append(f"\n- {obs}")

            # Output other key fields
            for key, val in result.items():
                if key not in ["summary", "strengths", "observations", "error"]:
                    lines.append(f"\n### {key.replace('_', ' ').title()}\n")
                    if isinstance(val, dict):
                        for k, v in val.items():
                            lines.append(f"- **{k}**: {v}")
                    elif isinstance(val, list):
                        for item in val:
                            lines.append(f"- {item}")
                    else:
                        lines.append(f"{val}")

    write_text_file(out_path, "\n".join(lines))
    return str(out_path)
