"""
Runtime hook — splash dengan animasi progress bar indeterminate via pure Win32.
Muncul instan saat EXE diklik, sebelum ekstraksi selesai.
"""
import ctypes
import ctypes.wintypes
import threading
import math
import time

user32   = ctypes.windll.user32
gdi32    = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

SW = 420
SH = 220

WS_POPUP      = 0x80000000
WS_VISIBLE    = 0x10000000
WS_EX_TOPMOST = 0x00000008
WM_DESTROY    = 0x0002
WM_PAINT      = 0x000F
WM_TIMER      = 0x0113

# Warna (BGR format)
C_BG      = 0x001C1C12
C_CARD    = 0x00282836
C_ACCENT  = 0x0000A5FF
C_WHITE   = 0x00FFFFFF
C_GRAY    = 0x00888888
C_BORDER  = 0x00402000

_hwnd      = None
_anim_pos  = 0.0
_running   = True
_dots      = 0


def _wnd_proc(hwnd, msg, wp, lp):
    global _anim_pos, _dots

    if msg == WM_PAINT:
        ps  = ctypes.create_string_buffer(64)
        hdc = user32.BeginPaint(hwnd, ps)
        _draw(hdc)
        user32.EndPaint(hwnd, ps)
        return 0

    if msg == WM_TIMER:
        _anim_pos = (_anim_pos + 0.03) % 1.0
        _dots      = (_dots + 1) % 4
        user32.InvalidateRect(hwnd, None, False)
        return 0

    if msg == WM_DESTROY:
        user32.KillTimer(hwnd, 1)
        user32.PostQuitMessage(0)
        return 0

    return user32.DefWindowProcW(hwnd, msg, wp, lp)


def _draw(hdc):
    # Background
    rc_all = ctypes.wintypes.RECT(0, 0, SW, SH)
    br_bg  = gdi32.CreateSolidBrush(C_BG)
    user32.FillRect(hdc, ctypes.byref(rc_all), br_bg)
    gdi32.DeleteObject(br_bg)

    # Card
    br_card = gdi32.CreateSolidBrush(C_CARD)
    rc_card = ctypes.wintypes.RECT(20, 20, SW - 20, SH - 20)
    user32.FillRect(hdc, ctypes.byref(rc_card), br_card)
    gdi32.DeleteObject(br_card)

    # Orange top bar (4px)
    br_acc = gdi32.CreateSolidBrush(C_ACCENT)
    rc_bar = ctypes.wintypes.RECT(20, 20, SW - 20, 24)
    user32.FillRect(hdc, ctypes.byref(rc_bar), br_acc)
    gdi32.DeleteObject(br_acc)

    gdi32.SetBkMode(hdc, 1)  # TRANSPARENT

    # Title "MangoDefend"
    gdi32.SetTextColor(hdc, C_WHITE)
    hf1 = gdi32.CreateFontW(24, 0, 0, 0, 700, 0, 0, 0, 0, 0, 0, 0, 0, "Segoe UI")
    gdi32.SelectObject(hdc, hf1)
    rc1 = ctypes.wintypes.RECT(0, 42, SW, 75)
    user32.DrawTextW(hdc, "MangoDefend", -1, ctypes.byref(rc1), 0x25)
    gdi32.DeleteObject(hf1)

    # Subtitle
    gdi32.SetTextColor(hdc, C_ACCENT)
    hf2 = gdi32.CreateFontW(12, 0, 0, 0, 400, 0, 0, 0, 0, 0, 0, 0, 0, "Segoe UI")
    gdi32.SelectObject(hdc, hf2)
    rc2 = ctypes.wintypes.RECT(0, 74, SW, 95)
    user32.DrawTextW(hdc, "AI Malware Protection", -1, ctypes.byref(rc2), 0x25)
    gdi32.DeleteObject(hf2)

    # Progress bar track
    bar_x  = 40
    bar_y  = 130
    bar_w  = SW - 80
    bar_h  = 8
    radius = 4
    br_track = gdi32.CreateSolidBrush(0x00333345)
    rc_track  = ctypes.wintypes.RECT(bar_x, bar_y, bar_x + bar_w, bar_y + bar_h)
    user32.FillRect(hdc, ctypes.byref(rc_track), br_track)
    gdi32.DeleteObject(br_track)

    # Animasi shimmer — blok berjalan dari kiri ke kanan
    block_w  = int(bar_w * 0.35)
    offset   = int(_anim_pos * (bar_w + block_w)) - block_w
    fill_x1  = max(bar_x, bar_x + offset)
    fill_x2  = min(bar_x + bar_w, bar_x + offset + block_w)
    if fill_x2 > fill_x1:
        br_fill = gdi32.CreateSolidBrush(C_ACCENT)
        rc_fill = ctypes.wintypes.RECT(fill_x1, bar_y, fill_x2, bar_y + bar_h)
        user32.FillRect(hdc, ctypes.byref(rc_fill), br_fill)
        gdi32.DeleteObject(br_fill)

    # Status text dengan dots animasi
    dots_str = "." * _dots
    status   = f"Mempersiapkan installer{dots_str}"
    gdi32.SetTextColor(hdc, C_GRAY)
    hf3 = gdi32.CreateFontW(11, 0, 0, 0, 400, 0, 0, 0, 0, 0, 0, 0, 0, "Segoe UI")
    gdi32.SelectObject(hdc, hf3)
    rc3 = ctypes.wintypes.RECT(0, 150, SW, 175)
    user32.DrawTextW(hdc, status, -1, ctypes.byref(rc3), 0x25)
    gdi32.DeleteObject(hf3)

    # Hint kecil
    gdi32.SetTextColor(hdc, 0x00555565)
    hf4 = gdi32.CreateFontW(10, 0, 0, 0, 400, 0, 0, 0, 0, 0, 0, 0, 0, "Segoe UI")
    gdi32.SelectObject(hdc, hf4)
    rc4 = ctypes.wintypes.RECT(0, 170, SW, 195)
    user32.DrawTextW(hdc, "Harap tunggu, sedang mengekstrak file...", -1, ctypes.byref(rc4), 0x25)
    gdi32.DeleteObject(hf4)


WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.wintypes.HWND,
    ctypes.c_uint, ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM
)
_proc = WNDPROC(_wnd_proc)


def _show_splash():
    global _hwnd
    hinstance = kernel32.GetModuleHandleW(None)
    cls_name  = "MGDSplash2"

    wc = (ctypes.c_ulong * 10)(0)
    wc[0] = ctypes.sizeof(wc) * 4
    wc[3] = hinstance
    wc[6] = ctypes.cast(_proc, ctypes.c_void_p).value
    wc[9] = ctypes.cast(ctypes.c_wchar_p(cls_name), ctypes.c_void_p).value
    user32.RegisterClassW(wc)

    sw_screen = user32.GetSystemMetrics(0)
    sh_screen = user32.GetSystemMetrics(1)
    x = (sw_screen - SW) // 2
    y = (sh_screen - SH) // 2

    _hwnd = user32.CreateWindowExW(
        WS_EX_TOPMOST, cls_name, "MangoDefend",
        WS_POPUP | WS_VISIBLE,
        x, y, SW, SH,
        None, None, hinstance, None
    )
    user32.UpdateWindow(_hwnd)

    # Timer 30ms untuk animasi ~33fps
    user32.SetTimer(_hwnd, 1, 30, None)

    msg = ctypes.create_string_buffer(48)
    while user32.GetMessageW(msg, None, 0, 0) > 0:
        user32.TranslateMessage(msg)
        user32.DispatchMessageW(msg)


def close_splash():
    global _hwnd
    if _hwnd:
        user32.PostMessageW(_hwnd, WM_DESTROY, 0, 0)
        _hwnd = None


_t = threading.Thread(target=_show_splash, daemon=True)
_t.start()
