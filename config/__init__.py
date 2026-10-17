# -*- coding: utf-8 -*-
"""
FilterMate Configuration Module.

Provides configuration loading, migration, structural validation and theme / feedback readers.
"""

from .config import ENV_VARS  # noqa: F401
from .feedback_config import FeedbackLevel, get_feedback_level, should_show_message  # noqa: F401
from .theme_helpers import (  # noqa: F401
    get_config_value,
    get_active_theme,
    get_theme_colors,
    get_background_colors,
    get_font_colors,
    get_accent_colors,
    get_available_themes,
)

__all__ = [
    # Core config
    'ENV_VARS',
    # Feedback
    'FeedbackLevel',
    'get_feedback_level',
    'should_show_message',
    # Theme
    'get_config_value',
    'get_active_theme',
    'get_theme_colors',
    'get_background_colors',
    'get_font_colors',
    'get_accent_colors',
    'get_available_themes',
]
