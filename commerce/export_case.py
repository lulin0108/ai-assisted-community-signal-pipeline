"""Bundle the desk cable case as one shareable HTML file."""

import argparse
import base64
from pathlib import Path


COMMERCE_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT = COMMERCE_DIR.parent / "output" / "html" / "desk-cable-case-with-image.html"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    output = parser.parse_args().output

    html = (COMMERCE_DIR / "desk-cable-case.html").read_text(encoding="utf-8")
    css = (COMMERCE_DIR / "styles.css").read_text(encoding="utf-8")
    image = base64.b64encode((COMMERCE_DIR / "desk-cable-concept.webp").read_bytes()).decode("ascii")
    stylesheet_tag = '<link rel="stylesheet" href="styles.css">'
    image_reference = 'src="desk-cable-concept.webp"'
    if html.count(stylesheet_tag) != 1 or html.count(image_reference) != 1:
        raise ValueError("The desk cable case must reference the stylesheet and concept image once each.")

    html = html.replace(stylesheet_tag, f"<style>\n{css}\n</style>")
    html = html.replace(image_reference, f'src="data:image/webp;base64,{image}"')
    html = html.replace('href="index.html"', 'href="#main"').replace("返回选品工作台", "返回顶部")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    print(output.resolve())


if __name__ == "__main__":
    main()
