"""Design tokens — semantic colors for Tuttle's dark theme.

Based on Apple Human Interface Guidelines dark-mode system colors
and macOS Ventura's native app palette.
"""

# ── Backgrounds ──────────────────────────────────────────────
bg = "#1C1C1E"  # main window / page background (Apple systemBackground)
bg_sidebar = "#2C2C2E"  # sidebar panel (Apple secondarySystemBackground)
bg_surface = "#3A3A3C"  # cards, panels (Apple systemGray4)
bg_surface_hovered = "#48484A"  # hovered cards (Apple systemGray3)
bg_titlebar = "#1C1C1E"  # title bar (seamless with bg)
bg_statusbar = "#2C2C2E"  # status bar (matches sidebar for native feel)
bg_statusbar_warning = "#3A3A3C"  # status bar with warnings (items use warning color)
bg_statusbar_danger = "#3A3A3C"  # status bar with overdue items (items use danger color)
bg_toolbar = "#2C2C2E"  # toolbar matches sidebar for cohesive chrome
bg_input = "#3A3A3C"  # text field fill

# ── Text ─────────────────────────────────────────────────────
text_primary = "#E5E5E7"  # main text (Apple label, dark)
text_secondary = "#AEAEB2"  # secondary text (Apple secondaryLabel)
text_muted = "#8E8E93"  # labels, placeholders (Apple systemGray)
text_inverse = "#FFFFFF"  # text on accent backgrounds

# ── Accent ───────────────────────────────────────────────────
accent = "#0A84FF"  # primary accent (macOS system blue)
accent_hovered = "#409CFF"  # hovered accent
accent_muted = "#1a3a5c"  # selected-item bg tint

# ── Semantic ─────────────────────────────────────────────────
danger = "#FF453A"  # destructive actions (macOS system red)
success = "#30D158"  # success indicators (macOS system green)
warning = "#FFD60A"  # warnings (macOS system yellow)

# ── Status colors ────────────────────────────────────────────
status_active = "#30D158"  # active projects/contracts
status_upcoming = "#0A84FF"  # upcoming / scheduled
status_completed = "#8E8E93"  # completed / archived
status_overdue = "#FF453A"  # overdue invoices
status_draft = "#636366"  # draft / not yet sent
goal_purple = "#BF5AF2"  # financial goals (macOS system purple)

# ── Borders & separators ─────────────────────────────────────
border = "#38383A"  # card borders, dividers
border_subtle = "#2C2C2E"  # very subtle separators
separator = "#1C1C1E"  # hairline dividers

# ── Activity bar ─────────────────────────────────────────────
activity_bar_bg = "#333333"  # activity bar background
activity_bar_icon = "#8E8E93"  # inactive icon
activity_bar_icon_active = "#FFFFFF"  # active icon
activity_bar_indicator = "#FFFFFF"  # active indicator bar

# ── Backward-compatibility aliases ───────────────────────────
# Maps old constant names to new tokens so un-migrated code still works.
PRIMARY_COLOR = accent
ERROR_COLOR = danger
DANGER_COLOR = danger
GRAY_COLOR = text_secondary
GRAY_DARK_COLOR = text_muted
BLACK_COLOR = "#1E1C28"
BLACK_COLOR_ALT = bg_surface
WHITE_COLOR = text_inverse
WHITE_COLOR_ALT = "#F6F6F6"
GRAY_LIGHT_COLOR = "#E5E4EA"
BORDER_DARK_COLOR = border
SIDEBAR_DARK_COLOR = bg_sidebar
SIDEBAR_LIGHT_COLOR = bg_sidebar  # no light mode
ACTION_BAR_DARK_COLOR = bg_toolbar
ACTION_BAR_LIGHT_COLOR = bg_toolbar  # no light mode
