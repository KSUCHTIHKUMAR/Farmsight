"""Port of src/main.tsx + index.html: builds the full HTML page string."""
import os

from python.app import App

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS_PATH = os.path.join(ROOT, "src", "index.css")


def load_css():
    with open(CSS_PATH, encoding="utf-8") as f:
        return f.read()


def render_page(app_html=None):
    """index.html shell with <div id="root"> filled by the rendered <App />.

    Fonts (Manrope, Inter, Noto Sans Telugu) come from the @import url(...)
    at the top of src/index.css, which is inlined into a <style> tag.
    """
    if app_html is None:
        app_html = App()
    return f"""<!doctype html>
<html lang="<!-- figma:lang -->">
  <head>
    <!-- figma:head-start -->
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title><!-- figma:title --></title>
    <style>
{load_css()}
    </style>
    <!-- figma:head-end -->
  </head>
  <body>
    <!-- figma:body-start -->
    <div id="root">{app_html}</div>
    <!-- figma:body-end -->
  </body>
</html>
"""


def main():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(render_page())
    return path


if __name__ == "__main__":
    print(main())
