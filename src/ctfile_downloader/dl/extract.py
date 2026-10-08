import re, json, urllib.request

def extract_links(share_url: str) -> list:
    """Parse ctfile share page: find file ids in JS config, build direct URLs."""
    with urllib.request.urlopen(share_url, timeout=15) as r:
        html = r.read().decode("utf-8", "ignore")
    # ctfile embeds file ids in a JS array like: file_id_list = [12345, 67890]
    m = re.search(r"file_id_list\s*=\s*\[([^\]]+)\]", html)
    ids = re.findall(r"\d+", m.group(1)) if m else []
    return [f"https://webapi.ctfile.com/get_file_url.php?fid={i}" for i in ids]
