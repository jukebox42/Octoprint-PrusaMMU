# coding=utf-8
from __future__ import absolute_import


class MmuStates():
  NOT_FOUND = "NOT_FOUND"
  STARTING = "STARTING"
  OK = "OK"
  LOADED = "LOADED"
  UNLOADING = "UNLOADING"
  LOADING = "LOADING"
  PAUSED_USER = "PAUSED_USER"
  ATTENTION = "ATTENTION"


class MmuKeys():
  STATE="state"
  TOOL="tool"
  PREV_TOOL="previousTool"

DEFAULT_MMU_STATE = dict(
  state=MmuStates.NOT_FOUND,
  tool="",
  previousTool="",
)
