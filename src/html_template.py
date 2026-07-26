import os

def load_template():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(current_dir, "templates", "main.html")
    
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"<html><body><h1>Template Load Error</h1><p>{str(e)}</p></body></html>"

HTML_TEMPLATE = load_template()
