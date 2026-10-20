import re

# ``` ... ``` across multiple lines. DOTALL lets "." match newlines;
# ".*?" is non-greedy: it stops at the NEAREST closing fence.
CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)


def protect_code_blocks(text):
    """
    Replace every fenced code block with a placeholder like @@CODE0@@.
    Returns (text_with_placeholders, list_of_original_blocks).
    """
    blocks = []

    def stash(match):
        # append the matched text to `blocks`
        blocks.append(match.group(0))

        # return the placeholder for this block, e.g. "@@CODE0@@"
        return f"@@CODE{len(blocks) - 1}@@"

    protected = CODE_FENCE.sub(stash, text)
    return protected, blocks


def restore_code_blocks(text, blocks):
    """Put each block back where its placeholder is."""
    # loop over blocks with their index; replace "@@CODE{index}@@" with the block text
    for index, block in enumerate(blocks):
        text = text.replace(f"@@CODE{index}@@", block)
    return text


# First line "Originally reported by: ...", then blank line(s) and an optional "---".
# \A anchors to the very start of the text.
BB_HEADER = re.compile(r"\A\s*Originally reported by:[^\n]*\n+(?:---[ \t]*\n+)?")

# "---" line followed by the "- Bitbucket: <url>" line. Not anchored to the end.
BB_FOOTER = re.compile(r"\n*---[ \t]*\n- Bitbucket: https://bitbucket\.org/\S+[ \t]*\n*")


def normalize_newlines(text):
    """Windows line endings -> \\n. Run this first."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def remove_bitbucket_wrapper(text):
    """Remove the migration header and footer added to issues imported from Bitbucket."""
    text = BB_HEADER.sub("", text)
    text = BB_FOOTER.sub("\n", text)
    return text.strip()


HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
IMG_TAG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
# Only specific layout tags. A generic "<.*?>" stripper would delete
# pytest output such as "<Module test_x.py>" or "<Function test_y>".
LAYOUT_TAG = re.compile(r"</?(?:details|summary|br|div)\b[^>]*>", re.IGNORECASE)
FENCE_PARTS = re.compile(r"\A```[^\n]*\n?(.*?)\n?```\Z", re.DOTALL)


def remove_html_noise(text):
    """Drop HTML comments, tag clutter, and mark images. Run with code blocks protected."""
    text = HTML_COMMENT.sub("", text)
    text = MD_IMAGE.sub("[IMAGE]", text)
    text = IMG_TAG.sub("[IMAGE]", text)
    text = LAYOUT_TAG.sub("\n", text)
    return text


def tidy_whitespace(text):
    """Strip trailing spaces and collapse 3+ newlines into one blank line."""
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def mark_block(block):
    """Turn a fenced block into [CODE]...[/CODE] or [TRACEBACK]...[/TRACEBACK]."""
    m = FENCE_PARTS.match(block)
    inner = m.group(1) if (m and "\n" in block) else block.strip("`")
    is_traceback = (
        "Traceback (most recent call last)" in inner
        or re.search(r"^E {3}", inner, re.MULTILINE)  # pytest-style "E   Error" lines
    )
    tag = "TRACEBACK" if is_traceback else "CODE"
    return f"[{tag}]\n{inner}\n[/{tag}]"


def clean_body(text):
    """Full pipeline for one issue/comment body."""
    text = normalize_newlines(text or "")
    text, blocks = protect_code_blocks(text)       # code is now untouchable
    text = remove_bitbucket_wrapper(text)
    text = remove_html_noise(text)
    text = tidy_whitespace(text)
    blocks = [mark_block(b) for b in blocks]
    return restore_code_blocks(text, blocks)


if __name__ == "__main__":
    sample = "Before\n```python\nprint('<!-- keep me -->')\n```\nAfter ```x``` end"

    protected, blocks = protect_code_blocks(sample)
    assert len(blocks) == 2
    assert "print(" not in protected
    assert "@@CODE0@@" in protected and "@@CODE1@@" in protected
    assert restore_code_blocks(protected, blocks) == sample
    assert protect_code_blocks("no code here") == ("no code here", [])
    wrapped = (
        "Originally reported by: **Ronny Pfannschmidt (BitBucket: [r](http://x), GitHub: [r](http://y))**"
        "\n\n---\n\nReal text\n\n---\n- Bitbucket: https://bitbucket.org/pytest-dev/pytest/issue/12\n"
    )
    assert remove_bitbucket_wrapper(wrapped) == "Real text"
    anon = "Originally reported by: **Anonymous**\n\n---\n\nHello"
    assert remove_bitbucket_wrapper(anon) == "Hello"
    plain = "Normal issue.\n\n---\n\nA horizontal rule in the middle stays."
    assert remove_bitbucket_wrapper(plain) == plain
    assert normalize_newlines("a\r\nb") == "a\nb"
    assert remove_html_noise("a<!-- hidden\nmulti-line -->b") == "ab"
    assert remove_html_noise("see ![shot](http://x/y.png)") == "see [IMAGE]"
    assert remove_html_noise("<Module test_x.py>") == "<Module test_x.py>"
    assert remove_html_noise("<details><summary>Log</summary>x</details>").count("<") == 0
    assert tidy_whitespace("a  \n\n\n\nb\n") == "a\n\nb"
    assert mark_block("```python\nprint(1)\n```") == "[CODE]\nprint(1)\n[/CODE]"
    assert mark_block("```x```") == "[CODE]\nx\n[/CODE]"
    assert mark_block("```\nTraceback (most recent call last):\n  boom\n```").startswith("[TRACEBACK]")
    raw = "Hi<!-- hide -->\r\n\r\n\r\n\r\nText ![shot](http://x/y.png)\r\n```python\nprint('<!-- keep -->')\n```"
    assert clean_body(raw) == "Hi\n\nText [IMAGE]\n[CODE]\nprint('<!-- keep -->')\n[/CODE]"
    assert clean_body(None) == ""
    print("all tests passed")