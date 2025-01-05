# coding=utf-8
from __future__ import absolute_import


class MmuStates():
  DETECTED="DETECTED" # TODO to be added later in place of the starter OK
  NOT_FOUND="NOT_FOUND"
  STARTING="STARTING"
  OK="OK"
  LOADED="LOADED"
  UNLOADING="UNLOADING"
  LOADING="LOADING"
  PAUSED_USER="PAUSED_USER"
  ATTENTION="ATTENTION"
  LOADING_MMU="LOADING_MMU"
  CUTTING="CUTTING"
  EJECTING="EJECTING"
  # TODO: Fix, only used for MK4 state tracking, should be accepted in js too.
  UNLOADING_FINAL="UNLOADING_FINAL"