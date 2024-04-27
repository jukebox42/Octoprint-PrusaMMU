/**
 * Get the icon class that represents the state for the nav. Returns the ? if unknown.
 * 
 * @param {string} state - The state of the MMU
 */
const getNavActionIcon = (state) => {
  const iconStates = {
    [STATES.NOT_FOUND]: "fa-times",
    [STATES.STARTING]: "fa-spinner fa-spin",
    [STATES.OK]: "fa-check",
    [STATES.PAUSED_USER]: "fa-fingerprint",
    [STATES.ATTENTION]: "fa-exclamation-triangle",
  };
  if (Object.keys(iconStates).indexOf(state) !== -1) {
    return iconStates[state];
  }

  // Action Icon only shows global states
  if (
    state === STATES.UNLOADING ||
    state === STATES.LOADING ||
    state === STATES.LOADED ||
    state === STATES.LOADING_MMU ||
    state === STATES.CUTTING ||
    state === STATES.EJECTING
  ) {
    return ""
  }
  
  return "fa-question";
};

/**
 * Get the icon class that represewnts the state for the tool.
 * 
 * @param {string} state - The state of the MMU
 */
const getNavToolIcon = (state) => {
  const iconStates = {
    [STATES.LOADED]: "fa-pen-fancy",
    [STATES.UNLOADING]: "fa-long-arrow-alt-up",
    [STATES.LOADING]: "fa-long-arrow-alt-down",
    [STATES.LOADING_MMU]: "fa-long-arrow-alt-right",
    [STATES.CUTTING]: "fa-cut",
    [STATES.EJECTING]: "fa-eject",
  };
  if (Object.keys(iconStates).indexOf(state) !== -1) {
    return iconStates[state];
  }
  
  return "";
};

// === Log ==

const LOG_PLUGIN_NAME = `plugin_${PLUGIN_NAME}`;

/**
 * Simple function to log out debug messages if debug is on. Use like you would console.log().
 * 
 * @param {...any} args - arguments to pass directly to console.log.
 */
const log = (...args) => {
  if (!self.settings.debug()) {
    return;
  }
  const d = new Date();
  const showtime = `[${d.getHours()}:${d.getMinutes()}:${d.getSeconds()}]`
  console.log(String.fromCodePoint(0x1F6A9), showtime, `${LOG_PLUGIN_NAME}:`, ...args);
};