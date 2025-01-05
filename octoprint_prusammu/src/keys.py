# coding=utf-8
from __future__ import absolute_import


# === Events ===

EVENT_PREFIX = "plugin_prusammu_"

class PluginEventKeys():
  REGISTER_MMU_CHANGE = "mmu_change"
  REGISTER_MMU_CHANGED = "mmu_changed"
  REGISTER_SHOW_PROMPT = "show_prompt"
  REGISTER_REFRESH_NAV = "refresh_nav"

  MMU_CHANGE = "{}{}".format(EVENT_PREFIX, REGISTER_MMU_CHANGE)
  MMU_CHANGED = "{}{}".format(EVENT_PREFIX, REGISTER_MMU_CHANGED)
  SHOW_PROMPT = "{}{}".format(EVENT_PREFIX, REGISTER_SHOW_PROMPT)
  REFRESH_NAV = "{}{}".format(EVENT_PREFIX, REGISTER_REFRESH_NAV)

# === Settings ===

class SettingsKeys():
  DEBUG="debug"
  TIMEOUT="timeout"
  USE_DEFAULT_FILAMENT="useDefaultFilament"
  DISPLAY_ACTIVE_FILAMENT="displayActiveFilament"
  SIMPLE_DISPLAY_MODE="simpleDisplayMode"
  ADVANCED_DISPLAY_MODE="advancedDisplayMode"
  DEFAULT_FILAMENT="defaultFilament"
  FILAMENT_SOURCE="filamentSource"
  FILAMENT_SOURCES="filamentSources" # remove this
  FILAMENT="filament"
  FILAMENT_MAP="filamentMap"
  USE_FILAMENT_MAP="useFilamentMap"
  ENABLE_PROMPT="enablePrompt"
  PRUSA_VERSION="prusaVersion"

# === State ===

class StateKeys():
  ACTIVE="active"
  SELECTED_FILAMENT="selectedFilament"

DEFAULT_STATE = dict(
  active=False, # Tracks when the modal is being displayed
  selectedFilament=None, # Tracks when a user selects a filament (in modal)
)

# === MMU ===

class MmuKeys():
  STATE="state"
  LAST_LINE="lastLine"
  TOOL="tool"
  PREV_TOOL="previousTool"
  RESPONSE="response"
  RESPONSE_DATA="responseData"
  PRUSA_VERSION="prusaVersion"