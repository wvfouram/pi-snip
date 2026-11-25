#!/usr/bin/python3
# Snipping Tool for Raspberry Pi, styled after the Windows 11 Snipping Tool (dark).
import os
import sys
import re
import json
import math
import time
import shutil
import signal
import threading
import subprocess

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf, Pango, Gio, GObject  # noqa: E402,F401
import cairo  # noqa: E402

HOME = os.path.expanduser("~")
C_ACCENT = "#4CC2FF"
def hexc(h, a=1.0):
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)


def _rr(cr, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    cr.close_path()


def _line(cr, *pts):
    cr.move_to(*pts[0])
    for p in pts[1:]:
        cr.line_to(*p)
    cr.stroke()


def draw_glyph(cr, name, s, col):
    """Monochrome line icons for buttons."""
    cr.save()
    cr.scale(s / 16.0, s / 16.0)
    cr.set_source_rgba(*col)
    cr.set_line_width(1.15)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    pi = math.pi
    L = lambda *p: _line(cr, *p)  # noqa: E731
    if name == "back":
        L((13.5, 8), (2.5, 8))
        L((7, 3.5), (2.5, 8), (7, 12.5))
    elif name == "forward":
        L((2.5, 8), (13.5, 8))
        L((9, 3.5), (13.5, 8), (9, 12.5))
    elif name == "up":
        L((8, 13.5), (8, 2.5))
        L((3.5, 7), (8, 2.5), (12.5, 7))
    elif name == "refresh":
        cr.arc(8, 8, 5.5, -pi * 0.35, pi * 1.55)
        cr.stroke()
        L((12.9, 1.8), (12.6, 4.9), (9.6, 4.6))
    elif name == "plus":
        L((8, 2.5), (8, 13.5))
        L((2.5, 8), (13.5, 8))
    elif name == "new":
        cr.set_source_rgba(*hexc(C_ACCENT))
        cr.arc(8, 8, 6.5, 0, 2 * pi)
        cr.stroke()
        L((8, 4.8), (8, 11.2))
        L((4.8, 8), (11.2, 8))
    elif name == "cut":
        cr.arc(4.5, 12, 2, 0, 2 * pi)
        cr.stroke()
        cr.arc(11.5, 12, 2, 0, 2 * pi)
        cr.stroke()
        L((5.8, 10.5), (11, 1.8))
        L((10.2, 10.5), (5, 1.8))
    elif name == "copy":
        _rr(cr, 5, 1.5, 9, 10.5, 1.5)
        cr.stroke()
        cr.move_to(3, 4.5)
        cr.line_to(3, 13)
        cr.arc_negative(4.5, 13, 1.5, pi, pi / 2)
        cr.line_to(11, 14.5)
        cr.stroke()
    elif name == "paste":
        _rr(cr, 2.5, 3, 11, 11.5, 1.5)
        cr.stroke()
        _rr(cr, 5.5, 1.5, 5, 3, 1)
        cr.stroke()
        L((5.5, 8), (10.5, 8))
        L((5.5, 11), (9, 11))
    elif name == "rename":
        _rr(cr, 1.5, 4.5, 13, 7, 1.3)
        cr.stroke()
        L((4, 8), (8, 8))
        L((10.5, 2.5), (10.5, 13.5))
        L((9, 2.5), (12, 2.5))
        L((9, 13.5), (12, 13.5))
    elif name == "delete" or name == "trash":
        L((2.5, 4), (13.5, 4))
        L((6, 4), (6.5, 2), (9.5, 2), (10, 4))
        cr.move_to(4, 4)
        cr.line_to(4.8, 14)
        cr.line_to(11.2, 14)
        cr.line_to(12, 4)
        cr.stroke()
        L((6.8, 6.8), (7, 11.5))
        L((9.2, 6.8), (9, 11.5))
    elif name == "sort":
        L((4.5, 2.5), (4.5, 13.5))
        L((2, 5), (4.5, 2.5), (7, 5))
        L((11.5, 2.5), (11.5, 13.5))
        L((9, 11), (11.5, 13.5), (14, 11))
    elif name == "view":
        for y in (3, 8, 13):
            L((2, y), (14, y))
    elif name == "more":
        for x in (3, 8, 13):
            cr.arc(x, 8, 1.1, 0, 2 * pi)
            cr.fill()
    elif name == "chevdown":
        L((4, 6), (8, 10), (12, 6))
    elif name == "chevright":
        L((6, 4), (10, 8), (6, 12))
    elif name == "close":
        L((3.5, 3.5), (12.5, 12.5))
        L((12.5, 3.5), (3.5, 12.5))
    elif name == "min":
        L((3, 8), (13, 8))
    elif name == "max":
        _rr(cr, 3, 3, 10, 10, 1.2)
        cr.stroke()
    elif name == "restore":
        _rr(cr, 3, 5, 8, 8, 1.2)
        cr.stroke()
        L((5, 3), (12, 3), (13, 4), (13, 11))
    elif name == "search":
        cr.arc(6.6, 6.6, 4.6, 0, 2 * pi)
        cr.stroke()
        L((10, 10), (14, 14))
    elif name == "pane":
        _rr(cr, 1.5, 2.5, 13, 11, 1.5)
        cr.stroke()
        L((10, 2.5), (10, 13.5))
    elif name == "terminal":
        _rr(cr, 1.5, 2.5, 13, 11, 1.5)
        cr.stroke()
        L((4, 6), (6.5, 8), (4, 10))
        L((8, 10.5), (11.5, 10.5))
    elif name == "properties":
        _rr(cr, 2.5, 1.5, 11, 13, 1.5)
        cr.stroke()
        for y in (5, 8, 11):
            cr.arc(5.2, y, 0.8, 0, 2 * pi)
            cr.fill()
            L((7.2, y), (11, y))
    elif name == "pin":
        cr.move_to(6, 2)
        cr.line_to(10, 2)
        cr.line_to(9.5, 6.5)
        cr.line_to(12, 9)
        cr.line_to(4, 9)
        cr.line_to(6.5, 6.5)
        cr.close_path()
        cr.stroke()
        L((8, 9), (8, 14))
    elif name == "pin-fill":
        cr.set_line_width(1.0)
        cr.translate(8, 8)
        cr.rotate(pi / 4)
        cr.translate(-8, -8)
        cr.move_to(6, 2)
        cr.line_to(10, 2)
        cr.line_to(9.5, 6.5)
        cr.line_to(12, 9)
        cr.line_to(4, 9)
        cr.line_to(6.5, 6.5)
        cr.close_path()
        cr.stroke()
        L((8, 9), (8, 14))
    elif name == "folder":
        cr.move_to(1.5, 4)
        cr.line_to(6, 4)
        cr.line_to(7.5, 5.5)
        cr.line_to(14.5, 5.5)
        cr.line_to(14.5, 13)
        cr.line_to(1.5, 13)
        cr.close_path()
        cr.stroke()
    elif name == "file":
        cr.move_to(3.5, 1.5)
        cr.line_to(9.5, 1.5)
        cr.line_to(12.5, 4.5)
        cr.line_to(12.5, 14.5)
        cr.line_to(3.5, 14.5)
        cr.close_path()
        cr.stroke()
        L((9.5, 1.5), (9.5, 4.5), (12.5, 4.5))
    elif name == "zip":
        _rr(cr, 2.5, 1.5, 11, 13, 1.5)
        cr.stroke()
        for y in (3, 5, 7):
            L((7, y), (9, y))
        _rr(cr, 6.5, 9, 3, 3.5, 0.6)
        cr.stroke()
    elif name == "extract":
        _rr(cr, 2.5, 6.5, 11, 8, 1.5)
        cr.stroke()
        L((8, 1.5), (8, 10))
        L((5.5, 7.5), (8, 10), (10.5, 7.5))
    elif name == "restoreitem":
        cr.arc(8.5, 8.5, 5, -pi * 0.9, pi * 0.6)
        cr.stroke()
        L((2, 3.5), (3.6, 6.6), (6.6, 5.4))
    elif name == "open":
        _rr(cr, 1.5, 1.5, 13, 13, 2)
        cr.stroke()
        L((7, 9), (12.5, 3.5))
        L((8.5, 3.5), (12.5, 3.5), (12.5, 7.5))
    elif name == "newtab":
        _rr(cr, 1.5, 3.5, 13, 10, 1.5)
        cr.stroke()
        L((1.5, 6), (8, 6))
        L((8, 3.5), (8, 6))
    elif name == "check":
        L((3, 8.5), (6.5, 12), (13, 4.5))
    elif name == "eject":
        cr.move_to(8, 3)
        cr.line_to(13, 9)
        cr.line_to(3, 9)
        cr.close_path()
        cr.stroke()
        L((3, 12.5), (13, 12.5))
    elif name == "details-view":
        for y in (3.5, 8, 12.5):
            _rr(cr, 1.5, y - 1.2, 2.4, 2.4, 0.5)
            cr.stroke()
            L((6, y), (14.5, y))
    elif name == "icons-view":
        for x in (2, 9):
            for y in (2, 9):
                _rr(cr, x, y, 5, 5, 1.2)
                cr.stroke()
    elif name == "selectall":
        _rr(cr, 2, 2, 12, 12, 1.5)
        cr.stroke()
        L((5, 8), (7.2, 10.2), (11, 6))
    elif name == "info":
        cr.arc(8, 8, 6, 0, 2 * pi)
        cr.stroke()
        L((8, 7), (8, 11.5))
        cr.arc(8, 4.8, 0.9, 0, 2 * pi)
        cr.fill()
    elif name == "share":
        cr.arc(4, 8, 1.8, 0, 2 * pi)
        cr.stroke()
        cr.arc(12, 3.8, 1.8, 0, 2 * pi)
        cr.stroke()
        cr.arc(12, 12.2, 1.8, 0, 2 * pi)
        cr.stroke()
        L((5.6, 7.1), (10.4, 4.7))
        L((5.6, 8.9), (10.4, 11.3))
    elif name == "network":
        _rr(cr, 5, 1.5, 6, 4.5, 1)
        cr.stroke()
        L((8, 6), (8, 9))
        L((3, 9), (13, 9))
        L((3, 9), (3, 11))
        L((13, 9), (13, 11))
        _rr(cr, 1, 11, 4, 3.5, 0.8)
        cr.stroke()
        _rr(cr, 11, 11, 4, 3.5, 0.8)
        cr.stroke()
    elif name == "link":
        cr.arc(5.5, 10.5, 3, pi * 0.25, pi * 1.75)
        cr.stroke()
        cr.arc(10.5, 5.5, 3, pi * 1.25, pi * 0.75)
        cr.stroke()
        L((6.5, 9.5), (9.5, 6.5))
    else:
        draw_glyph_extra(cr, name, L, pi)
    cr.restore()




# ----------------------------------------------------------------------------
# Shared Windows 11 dark style
# ----------------------------------------------------------------------------
BASE_CSS = """
* { font-family: "Segoe UI Variable Text", "Segoe UI", "Selawik", "Open Sans", "Noto Sans", sans-serif; }
window.fx, window.fx-dialog { background-color: #202020; color: #ffffff; font-size: 12px; }
.fx label { color: #ffffff; }
headerbar.fx-title { background: #202020; border: none; box-shadow: none; min-height: 40px; padding: 0; margin: 0; }
headerbar.fx-title:backdrop { background: #202020; }
.app-title { font-size: 12px; color: #ffffff; margin-left: 4px; }
.app-title:backdrop { color: rgba(255,255,255,0.55); }
button.wc { background: transparent; border: none; border-radius: 0; min-width: 46px; min-height: 32px; padding: 0; box-shadow: none; }
button.wc:hover { background-color: rgba(255,255,255,0.06); }
button.wc.close:hover { background-color: #C42B1C; }
.tabstrip { margin-top: 6px; margin-left: 6px; }
button.tab { outline-color: transparent; background: transparent; border: none; border-radius: 8px 8px 0 0; min-height: 34px;
   padding: 0 6px 0 12px; box-shadow: none; margin-right: 1px; }
button.tab:hover { background-color: rgba(255,255,255,0.04); }
button.tab.active { background-color: #2C2C2C; }
button.tab label { font-size: 12px; }
button.tab-x { background: transparent; border: none; border-radius: 4px; min-width: 24px; min-height: 24px; padding: 0; box-shadow: none; }
button.tab-x:hover { background-color: rgba(255,255,255,0.08); }
button.tab-new { background: transparent; border: none; border-radius: 4px; min-width: 32px; min-height: 28px; padding: 0;
   box-shadow: none; margin-top: 4px; margin-left: 2px; }
button.tab-new:hover { background-color: rgba(255,255,255,0.06); }
.bar { background-color: #2C2C2C; padding: 4px 8px; }
.bar-bottom { border-bottom: 1px solid rgba(255,255,255,0.06); }
button.tb, button.nb { background: transparent; border: none; border-radius: 4px; min-height: 32px; padding: 0 9px; box-shadow: none; color: #ffffff; }
button.nb { min-width: 34px; padding: 0; }
button.tb:hover, button.nb:hover { background-color: rgba(255,255,255,0.06); }
button.tb:active, button.nb:active { background-color: rgba(255,255,255,0.04); }
button.tb:disabled label { color: rgba(255,255,255,0.36); }
button.tb label { font-size: 12px; }
button.tb.on, button.nb.on { background-color: rgba(255,255,255,0.09); }
.vsep { background-color: rgba(255,255,255,0.08); min-width: 1px; margin: 6px 6px; }
.status { background-color: #202020; padding: 4px 12px; border-top: 1px solid rgba(255,255,255,0.06); }
.status label { font-size: 12px; color: rgba(255,255,255,0.786); }
.sec { color: rgba(255,255,255,0.786); }
.ter { color: rgba(255,255,255,0.545); }
.big-title { font-size: 20px; font-weight: 600; }
.sect-title { font-size: 14px; font-weight: 600; }
entry.field, entry.fx-search { background-color: rgba(255,255,255,0.06); color: #ffffff; border: 1px solid rgba(255,255,255,0.07);
   border-bottom: 1px solid rgba(255,255,255,0.54); border-radius: 4px; min-height: 30px; padding: 0 10px; box-shadow: none;
   font-size: 12px; caret-color: #ffffff; }
entry.field:focus, entry.fx-search:focus { background-color: #1c1c1c; border-bottom: 2px solid #4CC2FF; }
entry selection, textview text selection, entry selection:focus, textview text selection:focus { background-color: #0078D4; color: #ffffff; }
scrollbar { background: transparent; border: none; }
scrollbar slider { background-color: rgba(255,255,255,0.45); border-radius: 6px; min-width: 3px; min-height: 3px; border: none; }
scrollbar:hover slider { min-width: 6px; min-height: 6px; background-color: rgba(255,255,255,0.55); }
scrollbar trough { background: transparent; border: none; }
scale trough { background-color: rgba(255,255,255,0.3); border: none; border-radius: 2px; min-height: 4px; min-width: 4px; }
scale highlight { background-color: #4CC2FF; border: none; border-radius: 2px; min-height: 4px; min-width: 4px; }
scale slider { background-color: #4CC2FF; border: 5px solid #454545; border-radius: 50%; min-width: 12px; min-height: 12px; box-shadow: none; }
scale slider:hover { border-width: 4px; }
menu, .menu, .context-menu { background-color: #2C2C2C; color: #ffffff; border: 1px solid rgba(0,0,0,0.45); border-radius: 8px; padding: 4px; }
menu menuitem { padding: 6px 12px; border-radius: 4px; color: #ffffff; min-height: 18px; }
menu menuitem:hover { background-color: rgba(255,255,255,0.06); }
menu menuitem:disabled label { color: rgba(255,255,255,0.36); }
menu menuitem label { color: #ffffff; font-size: 12px; }
menu menuitem arrow { color: rgba(255,255,255,0.786); }
menu separator { background-color: rgba(255,255,255,0.08); margin: 4px 0; min-height: 1px; }
window.fx button, window.fx-dialog button { background-image: none; text-shadow: none; -gtk-icon-shadow: none; }
button.primary { background-color: #4CC2FF; color: #000000; border: none; border-radius: 4px; min-height: 30px; padding: 0 16px; box-shadow: none; }
button.primary label { color: #000000; }
button.primary:hover { background-color: #48B1E8; }
button.secondary { background-color: rgba(255,255,255,0.06); color: #ffffff; border: 1px solid rgba(255,255,255,0.09); border-radius: 4px; min-height: 30px; padding: 0 16px; box-shadow: none; }
button.secondary:hover { background-color: rgba(255,255,255,0.09); }
.dlg-body { background-color: #2B2B2B; padding: 24px; }
.dlg-foot { background-color: #202020; padding: 22px 24px; border-top: 1px solid rgba(0,0,0,0.3); }
.dlg-title { font-size: 20px; font-weight: 600; }
.fx-dialog label { color: #ffffff; }
.fx-dialog label.sec { color: rgba(255,255,255,0.786); }
.fx-dialog label.ter { color: rgba(255,255,255,0.545); }
checkbutton check { background-color: rgba(0,0,0,0.1); border: 1px solid rgba(255,255,255,0.6); border-radius: 4px; min-width: 18px; min-height: 18px; -gtk-icon-source: none; color: #000000; }
checkbutton check:checked { background-color: #4CC2FF; border-color: #4CC2FF; -gtk-icon-source: -gtk-icontheme("object-select-symbolic"); }
checkbutton label { color: #ffffff; font-size: 12px; margin-left: 6px; }
radiobutton radio { background-color: rgba(0,0,0,0.1); border: 1px solid rgba(255,255,255,0.6); border-radius: 50%; min-width: 18px; min-height: 18px; -gtk-icon-source: none; }
radiobutton radio:checked { background-color: #000000; border: 5px solid #4CC2FF; }
radiobutton label { color: #ffffff; font-size: 12px; margin-left: 6px; }
switch { background-color: transparent; border: 1px solid rgba(255,255,255,0.6); border-radius: 12px; min-width: 40px; min-height: 18px; }
switch:checked { background-color: #4CC2FF; border-color: #4CC2FF; }
switch slider { background-color: rgba(255,255,255,0.8); border-radius: 50%; min-width: 12px; min-height: 12px; margin: 3px; border: none; box-shadow: none; }
switch:checked slider { background-color: #000000; }
switch image { color: transparent; }
combobox button, combobox box { background-color: rgba(255,255,255,0.06); color: #ffffff; border: 1px solid rgba(255,255,255,0.07); border-radius: 4px; box-shadow: none; min-height: 30px; }
combobox button cellview, combobox button label, combobox arrow { color: #ffffff; }
spinbutton { background-color: rgba(255,255,255,0.06); color: #ffffff; border: 1px solid rgba(255,255,255,0.07); border-radius: 4px; box-shadow: none; }
spinbutton entry { background: transparent; border: none; box-shadow: none; color: #ffffff; }
spinbutton button { background: transparent; border: none; box-shadow: none; color: #ffffff; }
tooltip, tooltip.background { background-color: #2C2C2C; border: 1px solid rgba(0,0,0,0.4); border-radius: 4px; }
tooltip label { color: #ffffff; font-size: 12px; }
.set-group { background-color: rgba(255,255,255,0.05); border-radius: 4px; border: 1px solid rgba(0,0,0,0.2); padding: 12px 16px; }
.set-head { font-size: 13px; }
.set-desc { font-size: 12px; color: rgba(255,255,255,0.6); }
"""


def apply_css(extra=""):
    prov = Gtk.CssProvider()
    prov.load_from_data((BASE_CSS + extra).encode())
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), prov,
                                             Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 10)
    Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", True)


def draw_glyph_extra(cr, name, L, pi):
    if name == "save":
        _rr(cr, 2, 2, 12, 12, 1.5)
        cr.stroke()
        _rr(cr, 4.5, 2, 6, 4, 0.5)
        cr.stroke()
        _rr(cr, 4.5, 9, 7, 5, 0.5)
        cr.stroke()
    elif name == "undo":
        cr.move_to(3, 7)
        cr.curve_to(6, 3.5, 13, 4.5, 13, 10)
        cr.stroke()
        L((3, 3), (3, 7), (7, 7))
    elif name == "redo":
        cr.move_to(13, 7)
        cr.curve_to(10, 3.5, 3, 4.5, 3, 10)
        cr.stroke()
        L((13, 3), (13, 7), (9, 7))
    elif name == "replace":
        L((2, 5), (10, 5))
        L((7.5, 2.5), (10, 5), (7.5, 7.5))
        L((14, 11), (6, 11))
        L((8.5, 8.5), (6, 11), (8.5, 13.5))
    elif name == "zoomin":
        cr.arc(6.6, 6.6, 4.6, 0, 2 * pi)
        cr.stroke()
        L((10, 10), (14, 14))
        L((4.6, 6.6), (8.6, 6.6))
        L((6.6, 4.6), (6.6, 8.6))
    elif name == "zoomout":
        cr.arc(6.6, 6.6, 4.6, 0, 2 * pi)
        cr.stroke()
        L((10, 10), (14, 14))
        L((4.6, 6.6), (8.6, 6.6))
    elif name == "fit":
        L((2, 5.5), (2, 2), (5.5, 2))
        L((10.5, 2), (14, 2), (14, 5.5))
        L((14, 10.5), (14, 14), (10.5, 14))
        L((5.5, 14), (2, 14), (2, 10.5))
    elif name == "wrap":
        L((2, 3), (14, 3))
        cr.move_to(2, 8)
        cr.line_to(11.5, 8)
        cr.curve_to(15, 8, 15, 13, 11.5, 13)
        cr.line_to(8, 13)
        cr.stroke()
        L((9.5, 11.3), (8, 13), (9.5, 14.7))
        L((2, 13), (5, 13))
    elif name == "play":
        cr.move_to(4.5, 2.5)
        cr.line_to(13, 8)
        cr.line_to(4.5, 13.5)
        cr.close_path()
        cr.fill()
    elif name == "pause":
        _rr(cr, 3.5, 2.5, 3, 11, 0.8)
        cr.fill()
        _rr(cr, 9.5, 2.5, 3, 11, 0.8)
        cr.fill()
    elif name in ("next", "prev"):
        if name == "prev":
            cr.translate(16, 0)
            cr.scale(-1, 1)
        cr.move_to(3, 3)
        cr.line_to(10.5, 8)
        cr.line_to(3, 13)
        cr.close_path()
        cr.fill()
        _rr(cr, 11, 3, 2, 10, 0.6)
        cr.fill()
    elif name == "shuffle":
        L((2, 4), (5, 4), (11, 12), (14, 12))
        L((2, 12), (5, 12), (11, 4), (14, 4))
        L((12, 2), (14, 4), (12, 6))
        L((12, 10), (14, 12), (12, 14))
    elif name in ("repeat", "repeat1"):
        cr.move_to(3, 9)
        cr.line_to(3, 6)
        cr.arc(5, 6, 2, pi, 1.5 * pi)
        cr.line_to(13, 4)
        cr.stroke()
        L((11, 2), (13, 4), (11, 6))
        cr.move_to(13, 7)
        cr.line_to(13, 10)
        cr.arc(11, 10, 2, 0, 0.5 * pi)
        cr.line_to(3, 12)
        cr.stroke()
        L((5, 10), (3, 12), (5, 14))
        if name == "repeat1":
            cr.set_font_size(5)
            cr.move_to(6.8, 9.8)
            cr.show_text("1")
    elif name in ("volume", "mute"):
        cr.move_to(1.5, 6)
        cr.line_to(4.5, 6)
        cr.line_to(8, 2.5)
        cr.line_to(8, 13.5)
        cr.line_to(4.5, 10)
        cr.line_to(1.5, 10)
        cr.close_path()
        cr.stroke()
        if name == "mute":
            L((10.5, 6), (14.5, 10))
            L((14.5, 6), (10.5, 10))
        else:
            cr.arc(8, 8, 3.5, -pi / 3.5, pi / 3.5)
            cr.stroke()
            cr.arc(8, 8, 6.2, -pi / 3.5, pi / 3.5)
            cr.stroke()
    elif name == "fullscreen":
        L((2, 6), (2, 2), (6, 2))
        L((10, 2), (14, 2), (14, 6))
        L((14, 10), (14, 14), (10, 14))
        L((6, 14), (2, 14), (2, 10))
        L((2, 2), (6, 6))
        L((14, 14), (10, 10))
    elif name == "unfullscreen":
        L((6, 2), (6, 6), (2, 6))
        L((10, 2), (10, 6), (14, 6))
        L((10, 14), (10, 10), (14, 10))
        L((6, 14), (6, 10), (2, 10))
    elif name == "rotate":
        cr.arc(8, 9, 5, pi * 1.15, pi * 2.85)
        cr.stroke()
        L((2.5, 2.5), (3.4, 6.4), (7.2, 5.4))
    elif name == "heart":
        cr.move_to(8, 13.5)
        cr.curve_to(1, 8, 1.5, 2.5, 5, 2.5)
        cr.curve_to(6.5, 2.5, 7.5, 3.5, 8, 4.5)
        cr.curve_to(8.5, 3.5, 9.5, 2.5, 11, 2.5)
        cr.curve_to(14.5, 2.5, 15, 8, 8, 13.5)
        cr.stroke()
    elif name == "pen":
        L((2.5, 13.5), (3.2, 10.5), (11, 2.7), (13.3, 5), (5.5, 12.8), (2.5, 13.5))
        L((9.5, 4.2), (11.8, 6.5))
    elif name == "highlighter":
        L((3, 13.5), (13, 13.5))
        cr.move_to(5, 11)
        cr.line_to(11, 3)
        cr.line_to(13.5, 5)
        cr.line_to(7.5, 12.5)
        cr.line_to(5, 12.5)
        cr.close_path()
        cr.stroke()
    elif name == "eraser":
        cr.move_to(2.5, 10)
        cr.line_to(9, 3.5)
        cr.line_to(13.5, 8)
        cr.line_to(8, 13.5)
        cr.line_to(5.5, 13.5)
        cr.close_path()
        cr.stroke()
        L((6, 6.5), (10.5, 11))
        L((8, 13.5), (14, 13.5))
    elif name == "crop":
        L((4.5, 1.5), (4.5, 11.5), (14.5, 11.5))
        L((1.5, 4.5), (11.5, 4.5), (11.5, 14.5))
    elif name == "camera":
        _rr(cr, 1.5, 4, 13, 9.5, 1.6)
        cr.stroke()
        L((5, 4), (6, 2.5), (10, 2.5), (11, 4))
        cr.arc(8, 8.8, 2.6, 0, 2 * pi)
        cr.stroke()
    elif name == "timer":
        cr.arc(8, 9, 5.5, 0, 2 * pi)
        cr.stroke()
        L((8, 9), (8, 5.8))
        L((6.3, 1.8), (9.7, 1.8))
    elif name == "settings":
        n = 8
        cr.new_path()
        for i in range(n * 2):
            a = i * pi / n
            r = 6.6 if i % 2 == 0 else 5.0
            a1, a2 = a - pi / (n * 2.4), a + pi / (n * 2.4)
            cr.line_to(8 + r * math.cos(a1), 8 + r * math.sin(a1))
            cr.line_to(8 + r * math.cos(a2), 8 + r * math.sin(a2))
        cr.close_path()
        cr.stroke()
        cr.arc(8, 8, 2.2, 0, 2 * pi)
        cr.stroke()
    elif name == "history":
        cr.arc(8, 8, 6, pi * 1.05, pi * 2.85)
        cr.stroke()
        L((1.2, 6.2), (2.3, 8.6), (4.6, 7.3))
        L((8, 4.6), (8, 8.2), (10.5, 9.7))
    elif name == "image":
        _rr(cr, 1.5, 2.5, 13, 11, 1.5)
        cr.stroke()
        L((1.5, 11), (5.5, 7), (9, 10.5), (11, 8.5), (14.5, 12))
        cr.arc(10.5, 5.5, 1.2, 0, 2 * pi)
        cr.stroke()
    elif name == "music":
        cr.arc(4.5, 12, 2, 0, 2 * pi)
        cr.stroke()
        cr.arc(12, 10.5, 2, 0, 2 * pi)
        cr.stroke()
        L((6.5, 12), (6.5, 3.5), (14, 2), (14, 10.5))
    elif name == "video":
        _rr(cr, 1.5, 3.5, 9.5, 9, 1.5)
        cr.stroke()
        L((11, 6.5), (14.5, 4.5), (14.5, 11.5), (11, 9.5))
    elif name == "queue":
        for y in (3, 7):
            L((2, y), (14, y))
        L((2, 11), (8, 11))
        cr.move_to(10.5, 9)
        cr.line_to(14, 11.5)
        cr.line_to(10.5, 14)
        cr.close_path()
        cr.fill()
    elif name == "edit":
        L((2.5, 13.5), (3.2, 10.5), (11, 2.7), (13.3, 5), (5.5, 12.8), (2.5, 13.5))
    elif name == "slideshow":
        _rr(cr, 1.5, 2.5, 13, 9, 1.5)
        cr.stroke()
        cr.move_to(6.5, 5)
        cr.line_to(10, 7)
        cr.line_to(6.5, 9)
        cr.close_path()
        cr.fill()
        L((5, 14), (11, 14))
    elif name == "print":
        _rr(cr, 1.5, 6, 13, 6, 1.2)
        cr.stroke()
        L((4.5, 6), (4.5, 1.5), (11.5, 1.5), (11.5, 6))
        _rr(cr, 4.5, 9.5, 7, 5, 0.5)
        cr.stroke()
    elif name == "wallpaper":
        _rr(cr, 1.5, 2.5, 13, 9, 1.2)
        cr.stroke()
        L((1.5, 9.5), (5, 6), (8, 9), (10, 7), (14.5, 10.5))
        L((5.5, 14), (10.5, 14))
        L((8, 11.5), (8, 14))
    elif name == "list":
        for y in (3.5, 8, 12.5):
            cr.arc(2.5, y, 0.9, 0, 2 * pi)
            cr.fill()
            L((5.5, y), (14, y))
    elif name == "add":
        L((8, 2.5), (8, 13.5))
        L((2.5, 8), (13.5, 8))
    elif name == "split":
        _rr(cr, 1.5, 2.5, 13, 11, 1.5)
        cr.stroke()
        L((8, 2.5), (8, 13.5))
    elif name == "keyboard":
        _rr(cr, 1, 3.5, 14, 9, 1.5)
        cr.stroke()
        for x in (4, 6.7, 9.3, 12):
            cr.rectangle(x - 0.5, 6, 1, 1)
        cr.fill()
        L((4.5, 10), (11.5, 10))


class Icon(Gtk.DrawingArea):
    """Monochrome glyph icon."""

    def __init__(self, name, size=16, color=None):
        super().__init__()
        self.name = name
        self.size = size
        self.color = color
        self.set_size_request(size, size)
        self.set_valign(Gtk.Align.CENTER)
        self.connect("draw", self._draw)

    def set_icon(self, name):
        self.name = name
        self.queue_draw()

    def _draw(self, w, cr):
        col = self.color or (1, 1, 1, 1)
        p = self.get_parent()
        if not self.is_sensitive() or (p and not p.is_sensitive()):
            col = (1, 1, 1, 0.36)
        draw_glyph(cr, self.name, self.size, col)


class WinTitlebar(Gtk.HeaderBar):
    """Title bar with Windows 11 caption buttons. Pack your own widgets with pack_start()."""

    def __init__(self, window):
        super().__init__()
        self.win = window
        self.get_style_context().add_class("fx-title")
        self.set_show_close_button(False)
        self.set_custom_title(Gtk.Box())
        wc = Gtk.Box(spacing=0)
        wc.set_valign(Gtk.Align.START)
        for name, cb, extra in (("min", lambda *_: window.iconify(), ""),
                                ("max", lambda *_: self.toggle_max(), ""),
                                ("close", lambda *_: window.close(), "close")):
            b = Gtk.Button()
            b.get_style_context().add_class("wc")
            if extra:
                b.get_style_context().add_class(extra)
            ic = Icon(name, 10)
            b.add(ic)
            b.connect("clicked", cb)
            if name == "max":
                self.max_icon = ic
            wc.pack_start(b, False, False, 0)
        self.pack_end(wc)
        window.connect("window-state-event", self._wstate)
        window.set_titlebar(self)

    def toggle_max(self):
        if self.win.is_maximized():
            self.win.unmaximize()
        else:
            self.win.maximize()

    def _wstate(self, w, ev):
        maxed = bool(ev.new_window_state & Gdk.WindowState.MAXIMIZED)
        self.max_icon.set_icon("restore" if maxed else "max")
        return False


def app_title(text, logo_draw):
    """Little logo + app name for the left of the title bar."""
    box = Gtk.Box(spacing=8)
    box.set_margin_start(14)
    da = Gtk.DrawingArea()
    da.set_size_request(16, 16)
    da.set_valign(Gtk.Align.CENTER)
    da.connect("draw", lambda w, cr: logo_draw(cr, 16))
    box.pack_start(da, False, False, 0)
    lb = Gtk.Label(label=text)
    lb.get_style_context().add_class("app-title")
    box.pack_start(lb, False, False, 0)
    return box, lb


class JsonSettings(dict):
    def __init__(self, app_dir, defaults):
        super().__init__(defaults)
        self.dir = os.path.join(HOME, ".config", app_dir)
        self.file = os.path.join(self.dir, "settings.json")
        try:
            with open(self.file) as f:
                self.update(json.load(f))
        except (OSError, ValueError):
            pass

    def save(self):
        try:
            os.makedirs(self.dir, exist_ok=True)
            tmp = self.file + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self, f, indent=1)
            os.replace(tmp, self.file)
        except OSError:
            pass


def vsep():
    s = Gtk.Box()
    s.get_style_context().add_class("vsep")
    return s


def logo_pixbuf(draw, size):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    draw(cairo.Context(surf), size)
    return Gdk.pixbuf_get_from_surface(surf, 0, 0, size, size)
def label(text="", cls=None, xalign=0.0, ellipsize=False, wrap=False, markup=False):
    lb = Gtk.Label()
    if markup:
        lb.set_markup(text)
    else:
        lb.set_text(text)
    lb.set_xalign(xalign)
    if cls:
        for c in cls.split():
            lb.get_style_context().add_class(c)
    if ellipsize:
        lb.set_ellipsize(Pango.EllipsizeMode.END)
    if wrap:
        lb.set_line_wrap(True)
        lb.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
    return lb


def add_cls(w, *cls):
    ctx = w.get_style_context()
    for c in cls:
        ctx.add_class(c)
    return w


def tb_button(icon, text, cb=None, chev=False, tip=None):
    b = Gtk.Button()
    add_cls(b, "tb")
    box = Gtk.Box(spacing=7)
    if icon:
        box.pack_start(Icon(icon), False, False, 0)
    if text:
        box.pack_start(Gtk.Label(label=text), False, False, 0)
    if chev:
        box.pack_start(Icon("chevdown", 10), False, False, 0)
    b.add(box)
    b.set_relief(Gtk.ReliefStyle.NONE)
    b.set_tooltip_text(tip or text or None)
    if cb:
        b.connect("clicked", lambda w: cb(w))
    return b


def icon_button(icon, cb, cls="nb", tip=None, size=16):
    b = Gtk.Button()
    add_cls(b, cls)
    b.add(Icon(icon, size))
    b.set_relief(Gtk.ReliefStyle.NONE)
    if tip:
        b.set_tooltip_text(tip)
    b.connect("clicked", lambda w: cb(w))
    return b


def build_menu(spec):
    """spec: list of None (separator) or dicts: label, cb, icon, place, accel, sensitive, checked, sub."""
    menu = Gtk.Menu()
    add_cls(menu, "context-menu")
    for it in spec:
        if it is None:
            menu.append(Gtk.SeparatorMenuItem())
            continue
        mi = Gtk.MenuItem()
        box = Gtk.Box(spacing=12)
        ic = None
        if it.get("checked"):
            ic = Icon("check", 16)
        elif it.get("pixbuf") is not None:
            ic = Gtk.Image.new_from_pixbuf(it["pixbuf"])
        elif it.get("icon"):
            ic = Icon(it["icon"], 16)
        if ic is None:
            ic = Gtk.Box()
            ic.set_size_request(16, 16)
        box.pack_start(ic, False, False, 0)
        lb = Gtk.Label(label=it["label"])
        lb.set_xalign(0)
        box.pack_start(lb, True, True, 0)
        if it.get("accel"):
            al = Gtk.Label(label=it["accel"])
            al.get_style_context().add_class("dim-label")
            al.set_opacity(0.55)
            al.set_margin_start(24)
            box.pack_end(al, False, False, 0)
        mi.add(box)
        mi.set_sensitive(it.get("sensitive", True))
        if it.get("sub") is not None:
            mi.set_submenu(build_menu(it["sub"]))
        elif it.get("cb"):
            cb = it["cb"]
            mi.connect("activate", lambda w, cb=cb: GLib.idle_add(cb))
        menu.append(mi)
    menu.show_all()
    return menu


def popup_menu(menu, widget, event=None):
    menu.attach_to_widget(widget, None)
    if event is not None:
        menu.popup_at_pointer(event)
    else:
        menu.popup_at_widget(widget, Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST, None)


# ----------------------------------------------------------------------------
# Windows 11 style dialogs
# ----------------------------------------------------------------------------
class WinDialog(Gtk.Window):
    def __init__(self, parent, title, body=None, primary="OK", secondary="Cancel", width=440, extra=None,
                 markup=False):
        super().__init__(transient_for=parent, modal=True)
        add_cls(self, "fx-dialog")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_default_size(width, -1)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_title(title)
        self.cb = None
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        add_cls(self.body, "dlg-body")
        self.body.pack_start(label(title, "dlg-title"), False, False, 0)
        if body:
            lb = label(body, wrap=True, markup=markup)
            lb.set_max_width_chars(60)
            self.body.pack_start(lb, False, False, 0)
        if extra:
            self.body.pack_start(extra, False, False, 0)
        outer.pack_start(self.body, True, True, 0)
        self.foot = Gtk.Box(spacing=8, homogeneous=True)
        add_cls(self.foot, "dlg-foot")
        self.primary_btn = None
        if primary:
            pb = Gtk.Button(label=primary)
            add_cls(pb, "primary")
            pb.connect("clicked", lambda *_: self.done(True))
            self.foot.pack_start(pb, True, True, 0)
            pb.set_can_default(True)
            self.set_default(pb)
            self.primary_btn = pb
        if secondary:
            sb = Gtk.Button(label=secondary)
            add_cls(sb, "secondary")
            sb.connect("clicked", lambda *_: self.done(False))
            self.foot.pack_start(sb, True, True, 0)
        if primary or secondary:
            outer.pack_start(self.foot, False, False, 0)
        self.add(outer)
        self.connect("key-press-event", self._key)

    def _key(self, w, ev):
        if ev.keyval == Gdk.KEY_Escape:
            self.done(False)
            return True
        return False

    def done(self, ok):
        cb = self.cb
        self.cb = None
        self.hide()
        if cb:
            cb(ok)
        self.destroy()

    def ask(self, cb=None):
        self.cb = cb
        self.show_all()
        if self.primary_btn:
            self.primary_btn.grab_focus()


def info_dialog(parent, title, body):
    WinDialog(parent, title, body, primary="OK", secondary=None).ask()


def confirm(parent, title, body, yes, cb, no="Cancel"):
    WinDialog(parent, title, body, primary=yes, secondary=no).ask(cb)


def error_list_dialog(parent, title, errors):
    lines = []
    for p, msg in errors[:12]:
        lines.append(f"{os.path.basename(p) or p}: {msg}" if p else msg)
    if len(errors) > 12:
        lines.append(f"...and {len(errors) - 12} more")
    info_dialog(parent, title, "\n".join(lines))




# ----------------------------------------------------------------------------
# Snipping Tool
# ----------------------------------------------------------------------------
import datetime  # noqa: E402

APP_ID = "io.github.pisnip"
SHOTS_DIR = os.path.join(HOME, "Pictures", "Screenshots")
DEFAULTS = {"mode": "rect", "delay": 0, "autosave": True, "autocopy": True, "pen_color": "#E81123",
            "pen_size": 3, "hl_color": "#FFF100", "folder": SHOTS_DIR}
COLORS = ["#000000", "#FFFFFF", "#E81123", "#FF8C00", "#FFF100", "#16C60C", "#0078D4", "#B146C2"]
MODES = [("rect", "Rectangle", "rectmode"), ("free", "Freeform", "freemode"), ("full", "Full screen", "fullmode")]

CSS = """
.snipbar { background-color: #202020; padding: 8px 10px; }
.editbar { background-color: #2C2C2C; padding: 4px 8px; border-bottom: 1px solid rgba(255,255,255,0.06); }
.canvas-bg { background-color: #1C1C1C; }
.hint { font-size: 13px; color: rgba(255,255,255,0.75); }
button.swatch { min-width: 24px; min-height: 24px; padding: 0; border-radius: 12px; border: 2px solid transparent; box-shadow: none; }
button.swatch.on { border-color: #ffffff; }
.overlay-bar { background-color: #2C2C2C; border: 1px solid rgba(0,0,0,0.5); border-radius: 8px; padding: 4px; }
"""


def draw_logo(cr, s):
    cr.save()
    cr.scale(s / 16.0, s / 16.0)
    g = cairo.LinearGradient(0, 0, 16, 16)
    g.add_color_stop_rgb(0, 0.95, 0.35, 0.45)
    g.add_color_stop_rgb(1, 0.75, 0.15, 0.45)
    _rr(cr, 1, 1, 14, 14, 3)
    cr.set_source(g)
    cr.fill()
    cr.set_source_rgba(1, 1, 1, 0.95)
    cr.set_line_width(1.2)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.arc(5.2, 11, 1.7, 0, 2 * math.pi)
    cr.stroke()
    cr.arc(10.8, 11, 1.7, 0, 2 * math.pi)
    cr.stroke()
    cr.move_to(6.2, 9.7)
    cr.line_to(11, 3.5)
    cr.stroke()
    cr.move_to(9.8, 9.7)
    cr.line_to(5, 3.5)
    cr.stroke()
    cr.restore()


_orig_extra = draw_glyph_extra


def draw_glyph_extra(cr, name, L, pi):  # noqa: F811
    if name == "rectmode":
        cr.set_dash([1.6, 1.4])
        _rr(cr, 2, 3, 12, 10, 0.5)
        cr.stroke()
        cr.set_dash([])
    elif name == "freemode":
        cr.set_dash([1.6, 1.4])
        cr.move_to(3, 8)
        cr.curve_to(2, 3, 9, 1, 12, 4)
        cr.curve_to(15, 7, 12, 13, 8, 13)
        cr.curve_to(4, 13, 4, 10, 3, 8)
        cr.stroke()
        cr.set_dash([])
    elif name == "fullmode":
        _rr(cr, 1.5, 2.5, 13, 9, 1.2)
        cr.stroke()
        L((5.5, 14), (10.5, 14))
        L((8, 11.5), (8, 14))
        cr.set_dash([1.4, 1.2])
        _rr(cr, 3.5, 4.5, 9, 5, 0.5)
        cr.stroke()
        cr.set_dash([])
    elif name == "folder":
        cr.move_to(1.5, 4)
        cr.line_to(6, 4)
        cr.line_to(7.5, 5.5)
        cr.line_to(14.5, 5.5)
        cr.line_to(14.5, 13)
        cr.line_to(1.5, 13)
        cr.close_path()
        cr.stroke()
    else:
        _orig_extra(cr, name, L, pi)


# ---------------------------------------------------------------- capture
def capture_screen():
    """Return a GdkPixbuf of the whole screen (Wayland via grim, X11 via Gdk)."""
    if os.environ.get("WAYLAND_DISPLAY") and shutil.which("grim"):
        try:
            r = subprocess.run(["grim", "-t", "png", "-"], capture_output=True, timeout=15)
            if r.returncode == 0 and r.stdout:
                loader = GdkPixbuf.PixbufLoader.new_with_type("png")
                loader.write(r.stdout)
                loader.close()
                return loader.get_pixbuf(), None
            err = r.stderr.decode(errors="replace").strip()
        except (OSError, subprocess.SubprocessError, GLib.Error) as e:
            err = str(e)
        return None, err or "grim failed"
    if os.environ.get("WAYLAND_DISPLAY"):
        return None, "Install grim to take screenshots:  sudo apt install grim"
    root = Gdk.get_default_root_window()
    pb = Gdk.pixbuf_get_from_window(root, 0, 0, root.get_width(), root.get_height())
    return pb, None if pb else "Couldn't capture the screen"


def stamp_name():
    d = datetime.datetime.now()
    return f"Screenshot {d.strftime('%Y-%m-%d %H%M%S')}.png"


# ---------------------------------------------------------------- full-screen selector
class Selector(Gtk.Window):
    """Frozen screenshot shown full screen; drag to pick the area to keep."""

    def __init__(self, app, shot, mode, done):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.app = app
        self.shot = shot
        self.mode = mode
        self.done_cb = done
        self.start = None
        self.cur = None
        self.path = []
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_app_paintable(True)
        try:
            disp = Gdk.Display.get_default()
            mon = disp.get_primary_monitor() or disp.get_monitor(0)
            g = mon.get_geometry()
            self.set_default_size(g.width, g.height)
            self.move(g.x, g.y)
        except Exception:
            self.set_default_size(shot.get_width(), shot.get_height())
        self.da = Gtk.DrawingArea()
        self.da.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK |
                           Gdk.EventMask.POINTER_MOTION_MASK)
        self.da.connect("draw", self._draw)
        self.da.connect("button-press-event", self._press)
        self.da.connect("motion-notify-event", self._motion)
        self.da.connect("button-release-event", self._release)
        ov = Gtk.Overlay()
        ov.add(self.da)
        bar = Gtk.Box(spacing=2)
        bar.get_style_context().add_class("overlay-bar")
        bar.set_halign(Gtk.Align.CENTER)
        bar.set_valign(Gtk.Align.START)
        bar.set_margin_top(16)
        self.mode_btns = {}
        for key_, name, icon in MODES:
            b = icon_button(icon, lambda w, k=key_: self.set_mode(k), tip=name)
            bar.pack_start(b, False, False, 0)
            self.mode_btns[key_] = b
        bar.pack_start(vsep(), False, False, 0)
        bar.pack_start(icon_button("close", lambda w: self.finish(None), tip="Cancel (Esc)"), False, False, 0)
        ov.add_overlay(bar)
        self.add(ov)
        self.connect("key-press-event", self._key)
        self.set_mode(mode)
        cur = Gdk.Cursor.new_from_name(Gdk.Display.get_default(), "crosshair")
        self.connect("realize", lambda w: w.get_window().set_cursor(cur))
        self.show_all()
        self.fullscreen()
        self.present()

    def set_mode(self, m):
        self.mode = m
        for k, b in self.mode_btns.items():
            ctx = b.get_style_context()
            (ctx.add_class if k == m else ctx.remove_class)("on")
        if m == "full":
            GLib.idle_add(lambda: self.finish((0, 0, self.shot.get_width(), self.shot.get_height()), None) or False)

    def _scale(self):
        a = self.da.get_allocation()
        return min(a.width / self.shot.get_width(), a.height / self.shot.get_height()) or 1

    def _draw(self, w, cr):
        s = self._scale()
        cr.save()
        cr.scale(s, s)
        Gdk.cairo_set_source_pixbuf(cr, self.shot, 0, 0)
        cr.paint()
        cr.restore()
        cr.set_source_rgba(0, 0, 0, 0.5)
        cr.paint()
        clip = None
        if self.mode == "rect" and self.start and self.cur:
            x0, y0 = self.start
            x1, y1 = self.cur
            clip = lambda: cr.rectangle(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))  # noqa: E731
        elif self.mode == "free" and len(self.path) > 2:
            def clip():
                cr.move_to(*self.path[0])
                for p in self.path[1:]:
                    cr.line_to(*p)
                cr.close_path()
        if clip:
            cr.save()
            clip()
            cr.clip()
            cr.scale(s, s)
            Gdk.cairo_set_source_pixbuf(cr, self.shot, 0, 0)
            cr.paint()
            cr.restore()
            clip()
            cr.set_source_rgba(1, 1, 1, 0.9)
            cr.set_line_width(1.5)
            cr.stroke()

    def _press(self, w, ev):
        if ev.button != 1:
            return False
        self.start = (ev.x, ev.y)
        self.cur = (ev.x, ev.y)
        self.path = [(ev.x, ev.y)]
        return True

    def _motion(self, w, ev):
        if self.start:
            self.cur = (ev.x, ev.y)
            if self.mode == "free":
                self.path.append((ev.x, ev.y))
            self.da.queue_draw()
        return True

    def _release(self, w, ev):
        if not self.start:
            return True
        s = self._scale()
        if self.mode == "rect":
            x0, y0 = self.start
            x1, y1 = ev.x, ev.y
            if abs(x1 - x0) < 4 or abs(y1 - y0) < 4:
                self.start = None
                return True
            rect = (int(min(x0, x1) / s), int(min(y0, y1) / s), int(abs(x1 - x0) / s), int(abs(y1 - y0) / s))
            self.finish(rect, None)
        elif self.mode == "free":
            if len(self.path) < 4:
                self.start = None
                return True
            pts = [(x / s, y / s) for x, y in self.path]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            rect = (int(min(xs)), int(min(ys)), int(max(xs) - min(xs)) + 1, int(max(ys) - min(ys)) + 1)
            self.finish(rect, pts)
        return True

    def _key(self, w, ev):
        if ev.keyval == Gdk.KEY_Escape:
            self.finish(None)
            return True
        return False

    def finish(self, rect, poly=None):
        cb = self.done_cb
        self.done_cb = None
        self.destroy()
        if not cb:
            return
        if rect is None:
            cb(None)
            return
        x, y, w, h = rect
        W, H = self.shot.get_width(), self.shot.get_height()
        x, y = max(0, x), max(0, y)
        w, h = max(1, min(w, W - x)), max(1, min(h, H - y))
        sub = self.shot.new_subpixbuf(x, y, w, h).copy()
        if poly:
            surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
            cr = cairo.Context(surf)
            cr.move_to(poly[0][0] - x, poly[0][1] - y)
            for px, py in poly[1:]:
                cr.line_to(px - x, py - y)
            cr.close_path()
            cr.clip()
            Gdk.cairo_set_source_pixbuf(cr, sub, 0, 0)
            cr.paint()
            sub = Gdk.pixbuf_get_from_surface(surf, 0, 0, w, h)
        cb(sub)


# ---------------------------------------------------------------- editor canvas
class Canvas(Gtk.DrawingArea):
    def __init__(self, win):
        super().__init__()
        self.win = win
        self.base = None
        self.strokes = []
        self.redo_stack = []
        self.tool = "pen"
        self.drawing = None
        self.crop = None
        self.crop_start = None
        self.zoom = None
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.SCROLL_MASK |
                        Gdk.EventMask.SMOOTH_SCROLL_MASK)
        self.connect("draw", self._draw)
        self.connect("button-press-event", self._press)
        self.connect("motion-notify-event", self._motion)
        self.connect("button-release-event", self._release)

    def set_image(self, pb):
        self.base = pb
        self.strokes = []
        self.redo_stack = []
        self.crop = None
        self.queue_draw()

    def scale(self):
        if not self.base:
            return 1
        a = self.get_allocation()
        return min(1.0, (a.width - 32) / self.base.get_width(), (a.height - 32) / self.base.get_height())

    def origin(self):
        a = self.get_allocation()
        s = self.scale()
        return (a.width - self.base.get_width() * s) / 2, (a.height - self.base.get_height() * s) / 2

    def to_img(self, x, y):
        ox, oy = self.origin()
        s = self.scale()
        return (x - ox) / s, (y - oy) / s

    @staticmethod
    def paint_strokes(cr, strokes):
        for st_ in strokes:
            tool, col, width, pts = st_
            if len(pts) < 2:
                pts = pts + [(pts[0][0] + 0.1, pts[0][1] + 0.1)]
            c = hexc(col, 0.45 if tool == "hl" else 1.0)
            cr.set_source_rgba(*c)
            cr.set_line_width(width)
            cr.set_line_cap(cairo.LINE_CAP_ROUND if tool == "pen" else cairo.LINE_CAP_SQUARE)
            cr.set_line_join(cairo.LINE_JOIN_ROUND)
            cr.move_to(*pts[0])
            for p in pts[1:]:
                cr.line_to(*p)
            cr.stroke()

    def render(self):
        """Final picture: base + strokes."""
        w, h = self.base.get_width(), self.base.get_height()
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr = cairo.Context(surf)
        Gdk.cairo_set_source_pixbuf(cr, self.base, 0, 0)
        cr.paint()
        self.paint_strokes(cr, self.strokes)
        return Gdk.pixbuf_get_from_surface(surf, 0, 0, w, h)

    def _draw(self, w, cr):
        pass
        cr.set_source_rgb(0.11, 0.11, 0.11)
        cr.paint()
        if not self.base:
            return
        s = self.scale()
        ox, oy = self.origin()
        cr.save()
        cr.translate(ox, oy)
        cr.scale(s, s)
        # shadow
        cr.set_source_rgba(0, 0, 0, 0.4)
        cr.rectangle(3 / s, 3 / s, self.base.get_width(), self.base.get_height())
        cr.fill()
        Gdk.cairo_set_source_pixbuf(cr, self.base, 0, 0)
        cr.paint()
        self.paint_strokes(cr, self.strokes + ([self.drawing] if self.drawing else []))
        if self.tool == "crop":
            c = self.crop or (0, 0, self.base.get_width(), self.base.get_height())
            cr.set_source_rgba(0, 0, 0, 0.55)
            cr.rectangle(0, 0, self.base.get_width(), self.base.get_height())
            cr.rectangle(c[0] + c[2], c[1], -c[2], c[3])
            cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
            cr.fill()
            cr.set_source_rgba(1, 1, 1, 0.95)
            cr.set_line_width(2 / s)
            cr.rectangle(*c)
            cr.stroke()
        cr.restore()

    def _press(self, w, ev):
        if not self.base or ev.button != 1:
            return False
        x, y = self.to_img(ev.x, ev.y)
        st = self.win.st
        if self.tool == "pen":
            self.drawing = ["pen", st["pen_color"], st["pen_size"], [(x, y)]]
        elif self.tool == "hl":
            self.drawing = ["hl", st["hl_color"], 16, [(x, y)]]
        elif self.tool == "eraser":
            self._erase(x, y)
            self.drawing = ["eraser", None, 0, [(x, y)]]
        elif self.tool == "crop":
            self.crop_start = (x, y)
            self.crop = (x, y, 0, 0)
        self.queue_draw()
        return True

    def _erase(self, x, y):
        r = 10 / self.scale()
        keep = []
        for s_ in self.strokes:
            if any(abs(px - x) < r + s_[2] and abs(py - y) < r + s_[2] for px, py in s_[3]):
                self.redo_stack = []
                self.win.undo_log.append(("erase", s_, self.strokes.index(s_)))
                continue
            keep.append(s_)
        if len(keep) != len(self.strokes):
            self.strokes = keep
            self.win.changed()

    def _motion(self, w, ev):
        if not self.base:
            return False
        x, y = self.to_img(ev.x, ev.y)
        if self.drawing and self.drawing[0] in ("pen", "hl"):
            self.drawing[3].append((x, y))
            self.queue_draw()
        elif self.drawing and self.drawing[0] == "eraser":
            self._erase(x, y)
            self.queue_draw()
        elif self.crop_start:
            x0, y0 = self.crop_start
            W, H = self.base.get_width(), self.base.get_height()
            x, y = max(0, min(W, x)), max(0, min(H, y))
            self.crop = (min(x0, x), min(y0, y), abs(x - x0), abs(y - y0))
            self.queue_draw()
        return True

    def _release(self, w, ev):
        if self.drawing and self.drawing[0] in ("pen", "hl"):
            self.strokes.append(tuple(self.drawing[:3]) + (list(self.drawing[3]),))
            self.win.undo_log.append(("add", self.strokes[-1], len(self.strokes) - 1))
            self.redo_stack = []
            self.win.changed()
        self.drawing = None
        self.crop_start = None
        self.queue_draw()
        return True


# ---------------------------------------------------------------- main window
class SnipWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.app = app
        self.st = app.settings
        self.undo_log = []
        self.redo_log = []
        self.saved_path = None
        self._menu = None
        self.set_title("Snipping Tool")
        self.set_icon_name("pi-snip")
        self.get_style_context().add_class("fx")
        self.set_default_size(620, 200)
        self.connect("key-press-event", self._key)
        self.connect("delete-event", lambda *a: (self.st.save(), False)[1])
        tb = WinTitlebar(self)
        t, _ = app_title("Snipping Tool", draw_logo)
        tb.pack_start(t)
        tb.show_all()
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        bar = Gtk.Box(spacing=6)
        bar.get_style_context().add_class("snipbar")
        nb = Gtk.Button()
        nb.get_style_context().add_class("primary")
        bx = Gtk.Box(spacing=6)
        bx.pack_start(Icon("add", 14, color=(0, 0, 0, 1)), False, False, 0)
        bx.pack_start(Gtk.Label(label="New"), False, False, 0)
        nb.add(bx)
        nb.set_tooltip_text("New snip (Ctrl+N)")
        nb.connect("clicked", lambda w: self.new_snip())
        bar.pack_start(nb, False, False, 0)
        self.mode_btn = tb_button(self._mode_icon(), self._mode_name(), self._mode_menu, chev=True, tip="Snipping mode")
        bar.pack_start(self.mode_btn, False, False, 0)
        self.delay_btn = tb_button("timer", self._delay_name(), self._delay_menu, chev=True, tip="Delay")
        bar.pack_start(self.delay_btn, False, False, 0)
        bar.pack_end(icon_button("more", self._more_menu, tip="See more"), False, False, 0)
        root.pack_start(bar, False, False, 0)
        self.stack = Gtk.Stack()
        hint = label("Press New or Super+Shift+S to take a snip.\nAfterwards you can draw on it, crop it, copy or save it.",
                     "hint", xalign=0.5, wrap=True)
        hint.set_justify(Gtk.Justification.CENTER)
        hint.set_margin_top(14)
        hint.set_margin_bottom(18)
        self.stack.add_named(hint, "empty")
        ed = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        eb = Gtk.Box(spacing=2)
        eb.get_style_context().add_class("editbar")
        self.tool_btns = {}
        for key_, icon, tip in (("pen", "pen", "Ballpoint pen"), ("hl", "highlighter", "Highlighter"),
                                ("eraser", "eraser", "Eraser"), ("crop", "crop", "Crop")):
            b = icon_button(icon, lambda w, k=key_: self.set_tool(k), tip=tip)
            eb.pack_start(b, False, False, 0)
            self.tool_btns[key_] = b
        self.color_btn = Gtk.Button()
        self.color_btn.get_style_context().add_class("nb")
        self.color_da = Gtk.DrawingArea()
        self.color_da.set_size_request(16, 16)
        self.color_da.connect("draw", self._draw_swatch)
        self.color_btn.add(self.color_da)
        self.color_btn.set_tooltip_text("Ink color and size")
        self.color_btn.connect("clicked", self._color_pop)
        eb.pack_start(self.color_btn, False, False, 0)
        self.crop_done = tb_button("check", "Apply crop", lambda w: self.apply_crop())
        self.crop_done.get_child().show_all()
        self.crop_done.set_no_show_all(True)
        eb.pack_start(self.crop_done, False, False, 0)
        eb.pack_start(vsep(), False, False, 0)
        self.b_undo = icon_button("undo", lambda w: self.undo(), tip="Undo (Ctrl+Z)")
        self.b_redo = icon_button("redo", lambda w: self.redo(), tip="Redo (Ctrl+Y)")
        eb.pack_start(self.b_undo, False, False, 0)
        eb.pack_start(self.b_redo, False, False, 0)
        eb.pack_end(icon_button("copy", lambda w: self.copy(), tip="Copy (Ctrl+C)"), False, False, 0)
        eb.pack_end(icon_button("save", lambda w: self.save_as(), tip="Save as (Ctrl+S)"), False, False, 0)
        ed.pack_start(eb, False, False, 0)
        self.canvas = Canvas(self)
        ed.pack_start(self.canvas, True, True, 0)
        self.status = label("", "ter")
        self.status.set_margin_start(10)
        self.status.set_margin_top(4)
        self.status.set_margin_bottom(4)
        ed.pack_start(self.status, False, False, 0)
        self.stack.add_named(ed, "edit")
        root.pack_start(self.stack, True, True, 0)
        self.add(root)
        root.show_all()
        self.stack.set_visible_child_name("empty")
        self.set_tool("pen")
        self._sens()

    # ---------------- options
    def _mode_name(self):
        return {k: n for k, n, _ in MODES}.get(self.st["mode"], "Rectangle")

    def _mode_icon(self):
        return {k: i for k, _, i in MODES}.get(self.st["mode"], "rectmode")

    def _delay_name(self):
        d = self.st["delay"]
        return "No delay" if not d else f"{d} seconds"

    def _set_button(self, btn, icon, text):
        box = btn.get_child()
        ch = box.get_children()
        if isinstance(ch[0], Icon):
            ch[0].set_icon(icon)
        for c in ch:
            if isinstance(c, Gtk.Label):
                c.set_text(text)

    def _mode_menu(self, w):
        spec = [{"label": n, "icon": i, "checked": self.st["mode"] == k,
                 "cb": (lambda k=k: self._pick_mode(k))} for k, n, i in MODES]
        m = build_menu(spec)
        self._menu = m
        popup_menu(m, w)

    def _pick_mode(self, k):
        self.st["mode"] = k
        self._set_button(self.mode_btn, self._mode_icon(), self._mode_name())

    def _delay_menu(self, w):
        spec = [{"label": "No delay" if d == 0 else f"{d} seconds", "checked": self.st["delay"] == d,
                 "cb": (lambda d=d: self._pick_delay(d))} for d in (0, 3, 5, 10)]
        m = build_menu(spec)
        self._menu = m
        popup_menu(m, w)

    def _pick_delay(self, d):
        self.st["delay"] = d
        self._set_button(self.delay_btn, "timer", self._delay_name())

    def _more_menu(self, w):
        st = self.st
        m = build_menu([
            {"label": "Open screenshots folder", "icon": "folder", "cb": self.open_folder},
            None,
            {"label": "Automatically save screenshots", "checked": st["autosave"],
             "cb": lambda: st.__setitem__("autosave", not st["autosave"])},
            {"label": "Automatically copy to clipboard", "checked": st["autocopy"],
             "cb": lambda: st.__setitem__("autocopy", not st["autocopy"])},
            None,
            {"label": "About", "icon": "info", "cb": lambda: info_dialog(
                self, "Snipping Tool", "Snipping Tool for Raspberry Pi (pi-snip).\n"
                "Shortcut: Super+Shift+S\nScreenshots are saved in Pictures/Screenshots.")},
        ])
        self._menu = m
        popup_menu(m, w)

    def open_folder(self):
        os.makedirs(self.st["folder"], exist_ok=True)
        try:
            Gio.AppInfo.launch_default_for_uri(Gio.File.new_for_path(self.st["folder"]).get_uri(), None)
        except GLib.Error:
            pass

    # ---------------- snipping
    def new_snip(self, mode=None, quiet=False):
        """quiet: started from the keyboard shortcut; if cancelled, don't leave a window open."""
        self._quiet = quiet and not self.get_visible()
        self.hide()
        delay = (0 if quiet else int(self.st["delay"]) * 1000) + 350
        GLib.timeout_add(delay, self._grab, mode or self.st["mode"])

    def _grab(self, mode):
        shot, err = capture_screen()
        if shot is None:
            self.present()
            info_dialog(self, "Couldn't take a screenshot", err or "Unknown error")
            return False
        if mode == "full":
            self._got(shot)
            return False
        Selector(self.app, shot, mode, self._got)
        return False

    def _got(self, pb):
        if pb is None:
            if getattr(self, "_quiet", False) and self.canvas.base is None:
                self.destroy()
            else:
                self.present()
            return
        self.present()
        self.stack.set_visible_child_name("edit")
        self.canvas.set_image(pb)
        self.undo_log = []
        self.redo_log = []
        self.saved_path = None
        w = min(1200, max(620, pb.get_width() + 60))
        h = min(860, max(420, pb.get_height() + 200))
        if not self.is_maximized():
            self.resize(w, h)
        msg = []
        if self.st["autocopy"]:
            self.copy(quiet=True)
            msg.append("Copied to clipboard")
        if self.st["autosave"]:
            p = self.autosave()
            if p:
                msg.append(f"Saved to {p.replace(HOME, '~')}")
        self.status.set_text("    ".join(msg))
        self._sens()

    def autosave(self, pb=None):
        try:
            os.makedirs(self.st["folder"], exist_ok=True)
            p = self.saved_path or os.path.join(self.st["folder"], stamp_name())
            (pb or self.canvas.render()).savev(p, "png", [], [])
            self.saved_path = p
            return p
        except (OSError, GLib.Error):
            return None

    def changed(self):
        self._sens()
        if self.st["autosave"] and self.saved_path:
            self.autosave()

    def _sens(self):
        has = self.canvas.base is not None
        self.b_undo.set_sensitive(has and bool(self.undo_log))
        self.b_redo.set_sensitive(has and bool(self.redo_log))

    # ---------------- tools
    def set_tool(self, k):
        if self.canvas.tool == "crop" and k != "crop":
            self.canvas.crop = None
        self.canvas.tool = k
        for kk, b in self.tool_btns.items():
            ctx = b.get_style_context()
            (ctx.add_class if kk == k else ctx.remove_class)("on")
        self.crop_done.set_visible(k == "crop")
        self.canvas.queue_draw()

    def apply_crop(self):
        c = self.canvas.crop
        if not c or c[2] < 2 or c[3] < 2:
            self.set_tool("pen")
            return
        full = self.canvas.render()
        x, y, w, h = (int(v) for v in c)
        sub = full.new_subpixbuf(max(0, x), max(0, y), min(w, full.get_width() - x),
                                 min(h, full.get_height() - y)).copy()
        self.undo_log.append(("image", self.canvas.base, list(self.canvas.strokes)))
        self.canvas.base = sub
        self.canvas.strokes = []
        self.canvas.crop = None
        self.set_tool("pen")
        self.changed()

    def _draw_swatch(self, w, cr):
        col = self.st["hl_color"] if self.canvas.tool == "hl" else self.st["pen_color"]
        cr.set_source_rgba(*hexc(col))
        cr.arc(8, 8, 7, 0, 2 * math.pi)
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, 0.6)
        cr.set_line_width(1)
        cr.stroke()

    def _color_pop(self, w):
        pop = Gtk.Popover()
        pop.set_relative_to(w)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_start(10)
        box.set_margin_end(10)
        box.set_margin_top(10)
        box.set_margin_bottom(10)
        key_ = "hl_color" if self.canvas.tool == "hl" else "pen_color"
        g = Gtk.Grid(row_spacing=6, column_spacing=6)
        for i, c in enumerate(COLORS):
            b = Gtk.Button()
            b.get_style_context().add_class("swatch")
            if self.st[key_] == c:
                b.get_style_context().add_class("on")
            prov = Gtk.CssProvider()
            prov.load_from_data(f"button {{ background: {c}; }}".encode())
            b.get_style_context().add_provider(prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 30)
            b.connect("clicked", lambda w, c=c: (self.st.__setitem__(key_, c), self.color_da.queue_draw(),
                                                 pop.popdown()))
            g.attach(b, i % 4, i // 4, 1, 1)
        box.pack_start(g, False, False, 0)
        if key_ == "pen_color":
            box.pack_start(label("Size", "sec"), False, False, 0)
            sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 16, 1)
            sc.set_value(self.st["pen_size"])
            sc.set_draw_value(False)
            sc.set_size_request(160, -1)
            sc.connect("value-changed", lambda s: self.st.__setitem__("pen_size", int(s.get_value())))
            box.pack_start(sc, False, False, 0)
        pop.add(box)
        pop.show_all()
        pop.popup()

    # ---------------- undo / redo
    def undo(self):
        if not self.undo_log:
            return
        e = self.undo_log.pop()
        if e[0] == "add":
            if e[1] in self.canvas.strokes:
                self.canvas.strokes.remove(e[1])
        elif e[0] == "erase":
            self.canvas.strokes.insert(min(e[2], len(self.canvas.strokes)), e[1])
        elif e[0] == "image":
            cur = ("image", self.canvas.base, list(self.canvas.strokes))
            self.canvas.base, self.canvas.strokes = e[1], e[2]
            e = cur
        self.redo_log.append(e)
        self.canvas.queue_draw()
        self.changed()

    def redo(self):
        if not self.redo_log:
            return
        e = self.redo_log.pop()
        if e[0] == "add":
            self.canvas.strokes.append(e[1])
        elif e[0] == "erase":
            if e[1] in self.canvas.strokes:
                self.canvas.strokes.remove(e[1])
        elif e[0] == "image":
            cur = ("image", self.canvas.base, list(self.canvas.strokes))
            self.canvas.base, self.canvas.strokes = e[1], e[2]
            e = cur
        self.undo_log.append(e)
        self.canvas.queue_draw()
        self.changed()

    # ---------------- output
    def copy(self, quiet=False):
        if not self.canvas.base:
            return
        pb = self.canvas.render()
        Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_image(pb)
        if os.environ.get("WAYLAND_DISPLAY") and shutil.which("wl-copy"):
            # wl-copy keeps the picture on the clipboard after Snipping Tool closes
            try:
                ok, data = pb.save_to_bufferv("png", [], [])
                p = subprocess.Popen(["wl-copy", "--type", "image/png"], stdin=subprocess.PIPE,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                p.stdin.write(data)
                p.stdin.close()
            except (OSError, GLib.Error):
                pass
        if not quiet:
            self.status.set_text("Copied to clipboard")

    def save_as(self):
        if not self.canvas.base:
            return
        dlg = Gtk.FileChooserDialog(title="Save as", transient_for=self, action=Gtk.FileChooserAction.SAVE)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Save", Gtk.ResponseType.OK)
        dlg.set_do_overwrite_confirmation(True)
        os.makedirs(self.st["folder"], exist_ok=True)
        dlg.set_current_folder(self.st["folder"])
        dlg.set_current_name(os.path.basename(self.saved_path) if self.saved_path else stamp_name())
        ok = dlg.run() == Gtk.ResponseType.OK
        p = dlg.get_filename()
        dlg.destroy()
        if not ok or not p:
            return
        ext = os.path.splitext(p)[1].lower()
        typ = {".jpg": "jpeg", ".jpeg": "jpeg", ".bmp": "bmp"}.get(ext, "png")
        if typ == "png" and ext != ".png":
            p += ".png"
        try:
            pb = self.canvas.render()
            if typ == "jpeg":
                pb.savev(p, "jpeg", ["quality"], ["95"])
            else:
                pb.savev(p, typ, [], [])
            self.status.set_text(f"Saved to {p.replace(HOME, '~')}")
        except GLib.Error as e:
            info_dialog(self, "Couldn't save", e.message)

    def _key(self, w, ev):
        k = Gdk.keyval_to_lower(ev.keyval)
        ctrl = bool(ev.state & Gdk.ModifierType.CONTROL_MASK)
        if ctrl and k == Gdk.KEY_n:
            self.new_snip()
        elif ctrl and k == Gdk.KEY_c:
            self.copy()
        elif ctrl and k == Gdk.KEY_s:
            self.save_as()
        elif ctrl and k == Gdk.KEY_z:
            self.undo()
        elif ctrl and k == Gdk.KEY_y:
            self.redo()
        elif k in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and self.canvas.tool == "crop":
            self.apply_crop()
        elif k == Gdk.KEY_Escape and self.canvas.tool == "crop":
            self.set_tool("pen")
        else:
            return False
        return True


class SnipApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
        self.win = None

    def _closed(self, *a):
        self.win = None

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.settings = JsonSettings("pi-snip", DEFAULTS)
        apply_css(CSS)

    def do_command_line(self, cmd):
        args = cmd.get_arguments()[1:]
        if self.win is None:
            self.win = SnipWindow(self)
            self.win.connect("destroy", self._closed)
        if "--snip" in args or "--full" in args:
            self.win.new_snip("full" if "--full" in args else None, quiet=True)
        else:
            self.win.present()
        return 0


def main():
    GLib.set_prgname("pi-snip")
    GLib.set_application_name("Snipping Tool")
    app = SnipApp()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
