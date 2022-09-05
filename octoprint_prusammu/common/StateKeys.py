# coding=utf-8
from __future__ import absolute_import


class StateKeys():
  ACTIVE="active"
  SELECTED_FILAMENT="selectedFilament"

DEFAULT_STATE = dict(
  active=False, # Tracks when the modal is being displayed
  selectedFilament=None, # Tracks when a user selects a filament (in modal)
)
