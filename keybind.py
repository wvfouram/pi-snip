#!/usr/bin/python3
# Adds Super+Shift+S -> pi-snip --snip to the desktop's keyboard config (labwc, wayfire, openbox).
# Use "--remove" to take the shortcut out again.
import os
import re
import shutil
import sys
import time
import xml.dom.minidom

HOME = os.path.expanduser("~")
BIND_XML = '<keybind key="W-S-s"><action name="Execute" command="pi-snip --snip" /></keybind>'
ANY_WE = re.compile(r'<keybind\s+key="W-S-s"\s*>.*?</keybind>\s*', re.S)


def add_xml(path, fallback_src, root_tag, remove=False):
    if not os.path.exists(path):
        if remove:
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if fallback_src and os.path.exists(fallback_src):
            shutil.copy(fallback_src, path)
        else:
            with open(path, "w") as f:
                f.write(f'<?xml version="1.0"?>\n<{root_tag}>\n</{root_tag}>\n')
    with open(path) as f:
        txt = f.read()
    if remove:
        new = txt.replace(BIND_XML + "\n    ", "").replace(BIND_XML, "")
        if new != txt:
            with open(path, "w") as f:
                f.write(new)
            print(f"  {path}: removed Super+Shift+S")
        return
    if BIND_XML in txt:
        print(f"  {path}: Super+Shift+S already set")
        return
    backup = f"{path}.bak-{int(time.time())}"
    shutil.copy(path, backup)
    # replace any existing Super+Shift+S binding
    txt = ANY_WE.sub("", txt)
    if re.search(r"<keyboard\s*>\s*<default\s*/>", txt):
        new = re.sub(r"(<keyboard\s*>\s*<default\s*/>)", r"\1\n    " + BIND_XML, txt, count=1)
    elif re.search(r"<keyboard\s*>", txt):
        new = re.sub(r"(<keyboard\s*>)", r"\1\n    " + BIND_XML, txt, count=1)
    elif re.search(r"<keyboard\s*/>", txt):
        new = re.sub(r"<keyboard\s*/>", "<keyboard>\n    <default />\n    " + BIND_XML + "\n  </keyboard>",
                     txt, count=1)
    else:
        block = "  <keyboard>\n    <default />\n    " + BIND_XML + "\n  </keyboard>\n"
        new = txt.replace(f"</{root_tag}>", block + f"</{root_tag}>")
    try:
        xml.dom.minidom.parseString(new)
    except Exception as e:
        print(f"  {path}: could not add shortcut safely ({e}); left unchanged")
        return
    with open(path, "w") as f:
        f.write(new)
    print(f"  {path}: added Super+Shift+S (backup: {backup})")


def add_wayfire(path, remove=False):
    with open(path) as f:
        txt = f.read()
    lines = "binding_pisnip = <super> <shift> KEY_S\ncommand_pisnip = pi-snip --snip\n"
    if remove:
        if lines in txt:
            with open(path, "w") as f:
                f.write(txt.replace(lines, ""))
            print(f"  {path}: removed Super+Shift+S")
        return
    if "pi-snip" in txt:
        print(f"  {path}: shortcut already set")
        return
    shutil.copy(path, f"{path}.bak-{int(time.time())}")
    if re.search(r"^\[command\]\s*$", txt, re.M):
        txt = re.sub(r"^(\[command\]\s*\n)", r"\1" + lines, txt, count=1, flags=re.M)
    else:
        txt = txt.rstrip("\n") + "\n\n[command]\n" + lines
    with open(path, "w") as f:
        f.write(txt)
    print(f"  {path}: added Super+Shift+S")


def main():
    remove = "--remove" in sys.argv
    did = False
    if shutil.which("labwc") or os.path.exists(f"{HOME}/.config/labwc"):
        add_xml(f"{HOME}/.config/labwc/rc.xml", "/etc/xdg/labwc/rc.xml", "labwc_config", remove)
        did = True
    if os.path.exists(f"{HOME}/.config/wayfire.ini"):
        add_wayfire(f"{HOME}/.config/wayfire.ini", remove)
        did = True
    ob = f"{HOME}/.config/openbox/lxde-pi-rc.xml"
    if os.path.exists(ob):
        add_xml(ob, None, "openbox_config", remove)
        did = True
    if not did:
        print("  No supported desktop config found; open Snipping Tool from the menu instead.")


if __name__ == "__main__":
    main()
