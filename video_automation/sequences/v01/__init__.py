"""
Video V01 — Installation & Premier Pas
=======================================
14 sequences mapping the SCRIPT_V01_INSTALLATION.md tutorial.
"""
from __future__ import annotations

from sequences.v01.s00_hook import V01S00Hook
from sequences.v01.s01_install import V01S01Install
from sequences.v01.s02_first_launch import V01S02FirstLaunch
from sequences.v01.s03_interface import V01S03Interface
from sequences.v01.s04_sidebar import V01S04Sidebar
from sequences.v01.s05_action_bar import V01S05ActionBar
from sequences.v01.s06_first_filter import V01S06FirstFilter
from sequences.v01.s07_dark_theme import V01S07DarkTheme
from sequences.v01.s08_language import V01S08Language
from sequences.v01.s09_verbose import V01S09Verbose
from sequences.v01.s10_log_panel import V01S10LogPanel
from sequences.v01.s11_auto_display import V01S11AutoDisplay
from sequences.v01.s12_persistence import V01S12Persistence
from sequences.v01.s13_conclusion import V01S13Conclusion

V01_SEQUENCES = [
    V01S00Hook,
    V01S01Install,
    V01S02FirstLaunch,
    V01S03Interface,
    V01S04Sidebar,
    V01S05ActionBar,
    V01S06FirstFilter,
    V01S07DarkTheme,
    V01S08Language,
    V01S09Verbose,
    V01S10LogPanel,
    V01S11AutoDisplay,
    V01S12Persistence,
    V01S13Conclusion,
]

__all__ = ["V01_SEQUENCES"]
