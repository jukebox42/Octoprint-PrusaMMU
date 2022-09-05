# coding=utf-8
from __future__ import absolute_import

# === Constants ===
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
