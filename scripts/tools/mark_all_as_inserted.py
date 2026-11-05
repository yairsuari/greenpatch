"""Mark every run, paragraph mark and table row of a .docx as a tracked insertion.

Use for newly written manuscript content, so that all text Claude adds appears in
Word as tracked changes (see CLAUDE.md, manuscript rules). Runs already inside
<w:ins> or <w:del> are left untouched.

Usage:
    python scripts/tools/mark_all_as_inserted.py in.docx out.docx [--author Claude]
"""
import argparse
import datetime as dt
import shutil
import tempfile
import zipfile
from pathlib import Path

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


def q(tag):
    return f"{{{W}}}{tag}"


def mark(xml_bytes, author, date):
    root = etree.fromstring(xml_bytes)
    next_id = [9000]

    def rev(tag):
        el = etree.Element(q(tag))
        el.set(q("id"), str(next_id[0]))
        el.set(q("author"), author)
        el.set(q("date"), date)
        next_id[0] += 1
        return el

    body = root.find("w:body", NS)

    # 1. Wrap runs that are not already tracked.
    for r in list(body.iter(q("r"))):
        anc = r.getparent()
        if anc.tag in (q("ins"), q("del")):
            continue
        ins = rev("ins")
        anc.replace(r, ins)
        ins.append(r)

    # 2. Paragraph marks.
    for p in body.iter(q("p")):
        ppr = p.find("w:pPr", NS)
        if ppr is None:
            ppr = etree.Element(q("pPr"))
            p.insert(0, ppr)
        rpr = ppr.find("w:rPr", NS)
        if rpr is None:
            rpr = etree.Element(q("rPr"))
            # rPr must precede sectPr / pPrChange inside pPr
            idx = len(ppr)
            for i, child in enumerate(ppr):
                if child.tag in (q("sectPr"), q("pPrChange")):
                    idx = i
                    break
            ppr.insert(idx, rpr)
        if rpr.find("w:ins", NS) is None:
            rpr.insert(0, rev("ins"))

    # 3. Table rows.
    for tr in body.iter(q("tr")):
        trpr = tr.find("w:trPr", NS)
        if trpr is None:
            trpr = etree.Element(q("trPr"))
            idx = 1 if len(tr) and tr[0].tag == q("tblPrEx") else 0
            tr.insert(idx, trpr)
        if trpr.find("w:ins", NS) is None:
            change = trpr.find("w:trPrChange", NS)
            if change is not None:
                change.addprevious(rev("ins"))
            else:
                trpr.append(rev("ins"))

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--author", default="Claude")
    a = ap.parse_args()
    date = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_out = Path(tmp) / "out.docx"
        with zipfile.ZipFile(a.src) as zin, zipfile.ZipFile(tmp_out, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename == "word/document.xml":
                    data = mark(data, a.author, date)
                zout.writestr(item, data)
        shutil.copy(tmp_out, a.dst)
    print(f"Marked all content in {a.dst} as inserted by {a.author} ({date})")


if __name__ == "__main__":
    main()
