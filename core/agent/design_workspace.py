"""Conversation guidance and editable starter prompts for the advanced Designer workspace."""

DESIGNER_NOTE = (
    '\n\nAdvanced Designer workspace: coordinate layer styles, labels, QGIS map themes and print layouts. '
    'Load designer when offered; use brainstorm to compare and refine options before changes. '
    'Use only offered tools and the current user permissions. A draft or a chosen option is not approval to apply it.'
)

STARTERS = {
    'brainstorm': 'Help me brainstorm and refine a solution from the current context. Propose two or three options '
                 'and ask only questions that change the choice. Do not change the project yet.',
    'styles': 'In the advanced Designer workspace, propose refined layer styles and labels for this project. '
              'Compare two directions with readable colors and hierarchy. Do not apply them yet.',
    'layout': 'In the advanced Designer workspace, propose a print layout: purpose, page format, map, legend, '
              'scale and typography. Refine the proposal with me before creating or changing anything.',
    'themes': 'In the advanced Designer workspace, inspect existing QGIS map themes and propose how to organize '
              'them for different views and layouts. Do not save, replace, apply or remove a theme yet.',
}
