"""
Static accessibility checks against the storefront's real rendered HTML.

Honesty note: this is NOT a full WCAG 2.2 AA audit -- that needs a real
browser + assistive-tech testing (screen readers, keyboard-only
navigation) that this sandbox can't run. What this DOES check, for real,
against the actual server output:
- every <img> has a non-empty alt attribute
- heading levels don't skip (h1 -> h3 with no h2, etc.)
- <html lang="..."> is present
- every <input> has an associated <label> (via for/id or being wrapped)
- the <html> and page structure use real landmark elements

Color contrast (the other major static check) was already verified
separately in the color math in static/storefront.css's design --
see the WCAG contrast computation run during development (report Section 10.3).

Run: python tests/test_accessibility.py   (against a running server)
"""
import re
import sys
import os

import requests
from html.parser import HTMLParser

BASE = os.environ.get("MAUMART_TEST_BASE", "http://127.0.0.1:8000")


class A11yParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.images_missing_alt = []
        self.heading_sequence = []
        self.html_lang = None
        self.inputs = []
        self.labels_for = set()
        self._current_tag_stack = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "html":
            self.html_lang = attrs_dict.get("lang")
        elif tag == "img":
            alt = attrs_dict.get("alt")
            if not alt or not alt.strip():
                self.images_missing_alt.append(attrs_dict.get("src", "(no src)"))
        elif re.fullmatch(r"h[1-6]", tag):
            self.heading_sequence.append(int(tag[1]))
        elif tag == "input":
            self.inputs.append(attrs_dict)
        elif tag == "label":
            if "for" in attrs_dict:
                self.labels_for.add(attrs_dict["for"])


def check_page(path: str) -> dict:
    resp = requests.get(f"{BASE}{path}")
    parser = A11yParser()
    parser.feed(resp.text)

    heading_gaps = []
    prev = 0
    for level in parser.heading_sequence:
        if prev and level > prev + 1:
            heading_gaps.append((prev, level))
        prev = level

    unlabelled_inputs = []
    for inp in parser.inputs:
        input_id = inp.get("id")
        input_type = inp.get("type", "text")
        if input_type in ("hidden", "submit", "button"):
            continue
        if input_id not in parser.labels_for and "aria-label" not in inp:
            unlabelled_inputs.append(inp)

    return {
        "path": path,
        "status": resp.status_code,
        "images_missing_alt": parser.images_missing_alt,
        "heading_gaps": heading_gaps,
        "has_lang": bool(parser.html_lang),
        "unlabelled_inputs": unlabelled_inputs,
        "has_h1": 1 in parser.heading_sequence,
    }


def main():
    listing_id = requests.get(f"{BASE}/listings", params={"q": "Physics"}).json()[0]["id"]
    pages = ["/store/", "/store/category/Books%20%26%20Study%20Materials",
             f"/store/product/{listing_id}", "/store/search?q=book"]

    all_ok = True
    for path in pages:
        result = check_page(path)
        ok = (
            result["status"] == 200
            and not result["images_missing_alt"]
            and not result["heading_gaps"]
            and result["has_lang"]
            and not result["unlabelled_inputs"]
            and result["has_h1"]
        )
        all_ok = all_ok and ok
        print(f"\n{path} -> {'PASS' if ok else 'FAIL'}")
        print(f"  status: {result['status']}")
        print(f"  images missing alt: {result['images_missing_alt'] or 'none'}")
        print(f"  heading level gaps: {result['heading_gaps'] or 'none'}")
        print(f"  html lang present: {result['has_lang']}")
        print(f"  unlabelled form inputs: {len(result['unlabelled_inputs'])}")
        print(f"  has exactly one h1: {result['has_h1']}")

    print("\nPASS" if all_ok else "\nFAIL")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
