#!/usr/bin/env python3
"""Export module for The Audhd Scribbler. Exports never overwrite silently."""
import re
from pathlib import Path
from typing import Dict
from datetime import datetime
from .config import PROJECT_ROOT
from .file_io import read_text_file, write_text_file
from . import safety

def _output(path): return safety.unique_output_path(Path(path))

def export_markdown(file_path: str, output_path: str = None) -> str:
    path=Path(file_path)
    if not path.exists(): raise FileNotFoundError(f"File not found: {file_path}")
    if output_path is None: output_path=PROJECT_ROOT/"data"/"exports"/f"{path.stem}.md"
    out=_output(output_path); out.parent.mkdir(parents=True,exist_ok=True); write_text_file(out,read_text_file(path)); return str(out)

def export_plain_text(file_path: str, output_path: str = None) -> str:
    path=Path(file_path)
    if not path.exists(): raise FileNotFoundError(f"File not found: {file_path}")
    content=read_text_file(path)
    if content.startswith("---"):
        end=content.find("---",3)
        if end!=-1: content=content[end+3:].strip()
    content=re.sub(r'<!-- SCRIBBLER SUMMARY[\s\S]*?-->','',content).strip()
    if output_path is None: output_path=PROJECT_ROOT/"data"/"exports"/f"{path.stem}.txt"
    out=_output(output_path); out.parent.mkdir(parents=True,exist_ok=True); write_text_file(out,content); return str(out)

def _sanitize_for_docx(text):
    cleaned=[]
    for c in text:
        n=ord(c)
        if n==0: continue
        cleaned.append(c if n>=32 or n in (9,10,13) else ' ')
    return re.sub(r' {3,}','  ',''.join(cleaned))

def export_docx(file_path: str, output_path: str = None) -> str:
    try:
        from docx import Document
        from docx.shared import Pt
    except ImportError: raise ImportError("python-docx is required for DOCX export")
    path=Path(file_path)
    if not path.exists(): raise FileNotFoundError(f"File not found: {file_path}")
    content=read_text_file(path); body=content
    if body.startswith("---"):
        end=body.find("---",3)
        if end!=-1: body=body[end+3:].strip()
    body=re.sub(r'<!-- SCRIBBLER SUMMARY[\s\S]*?-->','',body).strip(); body=_sanitize_for_docx(body)
    if output_path is None: output_path=PROJECT_ROOT/"data"/"exports"/f"{path.stem}.docx"
    out=_output(output_path); out.parent.mkdir(parents=True,exist_ok=True)
    doc=Document(); doc.styles['Normal'].font.name='Calibri'; doc.styles['Normal'].font.size=Pt(11)
    doc.add_heading(_sanitize_for_docx(path.stem.replace('-',' ').replace('_',' ').title()),level=1)
    for para in re.split(r'\n\s*\n',body):
        para=para.strip()
        if not para: continue
        if para.startswith('# '): doc.add_heading(_sanitize_for_docx(para[2:]),level=1)
        elif para.startswith('## '): doc.add_heading(_sanitize_for_docx(para[3:]),level=2)
        elif para.startswith('### '): doc.add_heading(_sanitize_for_docx(para[4:]),level=3)
        else: doc.add_paragraph(_sanitize_for_docx(para))
    doc.save(str(out)); return str(out)

def export_analysis_report(file_path: str, analysis_results: Dict, output_path: str = None,
                           synthesis: Dict = None, fmt: str = "md") -> str:
    """Export analysis results as Markdown or JSON.

    Args:
        file_path: Path to the source file (used for the report title).
        analysis_results: Dict of {tool_key: result_dict} from analyze().
        output_path: Where to save. If None, defaults to data/reports/<stem>_analysis.<ext>.
        synthesis: Optional synthesis dict (placed at top of report).
        fmt: 'md' for Markdown (default) or 'json' for full JSON round-trip.
    """
    import json as _json
    path = Path(file_path)
    ext = "md" if fmt == "md" else "json"
    if output_path is None:
        output_path = PROJECT_ROOT / "data" / "reports" / f"{path.stem}_analysis.{ext}"
    out = _output(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "json":
        payload = {
            "file": str(path),
            "filename": path.name,
            "generated_at": datetime.now().isoformat(),
            "synthesis": synthesis,
            "tools": analysis_results,
        }
        write_text_file(out, _json.dumps(payload, ensure_ascii=False, indent=2))
        return str(out)

    # Markdown format
    lines = [
        f"# Analysis Report: {path.name}",
        f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        f"\n*File: `{path}`*",
    ]

    # Synthesis at the top
    if synthesis:
        lines += [
            "\n---\n\n## ✦ Synthesis\n",
            f"\n> {synthesis.get('summary', '')}\n" if synthesis.get('summary') else "",
        ]
        if synthesis.get('voice_consistency'):
            lines.append(f"\n**Voice consistency:** {synthesis['voice_consistency']}\n")
        if synthesis.get('narrator_distance'):
            lines.append(f"\n**Narrator distance:** {synthesis['narrator_distance']}\n")
        if synthesis.get('top_things_to_notice'):
            lines.append("\n### Top things to notice\n")
            for i, t in enumerate(synthesis['top_things_to_notice'], 1):
                lines.append(f"\n{i}. {t}")
        if synthesis.get('recurring_signals'):
            lines.append("\n\n### Recurring signals across tools\n")
            for s in synthesis['recurring_signals']:
                lines.append(f"\n- {s}")
        if synthesis.get('audhd_aware_notes'):
            lines.append("\n\n### AUDHD-aware notes\n")
            for n in synthesis['audhd_aware_notes']:
                lines.append(f"\n- {n}")
        if synthesis.get('what_this_does_not_mean'):
            lines.append("\n\n### What this does NOT mean\n")
            for n in synthesis['what_this_does_not_mean']:
                lines.append(f"\n- {n}")

    # Per-tool results
    for kind, result in analysis_results.items():
        if kind == "_synthesis":
            continue  # already handled above
        lines += [f"\n---\n\n## {kind.replace('_', ' ').title()}\n"]
        if isinstance(result, dict):
            if result.get("error"):
                lines.append(f"\n*Error: {result['error']}*\n")
                continue
            if "summary" in result:
                lines.append(f"\n{result['summary']}\n")
            if "strengths" in result:
                lines.append("\n### Strengths\n")
                lines.extend(f"- {s}" for s in result['strengths'])
            if "observations" in result:
                lines.append("\n### Observations\n")
                for obs in result['observations']:
                    if isinstance(obs, dict):
                        cat = obs.get('category', '').replace('_', ' ').title()
                        loc_str = obs.get('location', '')
                        # Add [¶N] anchor if loc is available
                        loc = obs.get('loc')
                        if loc and loc.get('paragraphs'):
                            paras = loc['paragraphs']
                            if len(paras) == 1:
                                loc_str += f" [¶{paras[0]}]"
                            elif len(paras) <= 3:
                                loc_str += f" [¶{', ¶'.join(str(p) for p in paras)}]"
                            else:
                                loc_str += f" [¶{paras[0]}-¶{paras[-1]}]"
                        lines.append(f"\n**{cat}** ({loc_str})\n")
                        lines.append(f"\n{obs.get('formatted', '')}\n")
                        if obs.get('evidence_quote'):
                            lines.append(f"\n> *Evidence: \"{obs['evidence_quote']}\"*\n")
                        if obs.get('why_it_matters'):
                            lines.append(f"\n*Why it matters: {obs['why_it_matters']}*\n")
                    else:
                        lines.append(f"\n- {obs}")
            # Compact metrics
            for key, val in result.items():
                if key in {'summary', 'strengths', 'observations', 'error'}: continue
                if isinstance(val, (dict, list)) and val:
                    lines.append(f"\n### {key.replace('_', ' ').title()}\n")
                    if isinstance(val, dict):
                        for k, v in val.items():
                            if isinstance(v, (dict, list)): continue  # skip nested
                            lines.append(f"- **{k}**: {v}")
                    elif isinstance(val, list):
                        for item in val[:10]:
                            if isinstance(item, dict):
                                # Format dict items as a single line
                                bits = [f"{k}={v}" for k, v in item.items() if not isinstance(v, (dict, list))]
                                lines.append(f"- {', '.join(bits)}")
                            else:
                                lines.append(f"- {item}")
                elif not isinstance(val, (dict, list)):
                    lines.append(f"\n**{key.replace('_', ' ').title()}**: {val}\n")

    write_text_file(out, '\n'.join(lines))
    return str(out)


def export_tag_index(format: str = "csv", include_excerpts: bool = True) -> str:
    """Export the tag_occurrences index as CSV, JSON, or Markdown.

    Returns the path to the exported file.
    """
    import csv as _csv
    import io as _io
    from . import db as _db

    occs = _db.get_tag_occurrences(limit=10000)
    if not occs:
        # Return an empty file with headers
        out_path = PROJECT_ROOT / "data" / "exports" / f"tag_index.{format}"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if format == "csv":
            out_path.write_text("file_path,tag_type,tag_value,paragraph,char_start,char_end,snippet\n", encoding="utf-8")
        elif format == "json":
            out_path.write_text("[]\n", encoding="utf-8")
        else:
            out_path.write_text("# Tag Index\n\n*No tags indexed yet.*\n", encoding="utf-8")
        return str(out_path)

    out_path = PROJECT_ROOT / "data" / "exports" / f"tag_index.{format}"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if format == "csv":
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            w = _csv.writer(f)
            w.writerow(["file_path", "filename", "tag_type", "tag_value", "paragraph", "char_start", "char_end", "snippet"])
            for o in occs:
                filename = Path(o["file_path"]).name if o.get("file_path") else ""
                w.writerow([
                    o.get("file_path", ""),
                    filename,
                    o.get("tag_type", ""),
                    o.get("tag_value", ""),
                    o.get("paragraph", ""),
                    o.get("char_start", ""),
                    o.get("char_end", ""),
                    (o.get("snippet", "") if include_excerpts else ""),
                ])
    elif format == "json":
        import json as _json
        payload = []
        for o in occs:
            filename = Path(o["file_path"]).name if o.get("file_path") else ""
            payload.append({
                "file_path": o.get("file_path", ""),
                "filename": filename,
                "tag_type": o.get("tag_type", ""),
                "tag_value": o.get("tag_value", ""),
                "paragraph": o.get("paragraph"),
                "char_start": o.get("char_start"),
                "char_end": o.get("char_end"),
                "snippet": o.get("snippet", "") if include_excerpts else "",
            })
        out_path.write_text(_json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    else:  # markdown
        lines = ["# Tag Index", "", f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*", ""]
        # Group by file, then tag_type, then tag_value
        by_file = {}
        for o in occs:
            fp = o["file_path"]
            if fp not in by_file:
                by_file[fp] = {}
            tt = o["tag_type"]
            if tt not in by_file[fp]:
                by_file[fp][tt] = {}
            tv = o["tag_value"]
            if tv not in by_file[fp][tt]:
                by_file[fp][tt][tv] = []
            by_file[fp][tt][tv].append(o)

        for fp, types in by_file.items():
            fname = Path(fp).name
            lines.append(f"\n## {fname}\n")
            for tt in sorted(types.keys()):
                lines.append(f"\n### {tt.replace('_', ' ').title()}\n")
                for tv in sorted(types[tt].keys()):
                    occ_list = types[tt][tv]
                    paras = sorted(set(o["paragraph"] for o in occ_list if o.get("paragraph")))
                    lines.append(f"\n- **{tv}** (¶{', ¶'.join(str(p) for p in paras)})")
                    if include_excerpts and occ_list:
                        snippet = occ_list[0].get("snippet", "")[:120]
                        if snippet:
                            lines.append(f"  \n  *{snippet}…*")

        out_path.write_text('\n'.join(lines), encoding="utf-8")

    return str(out_path)
