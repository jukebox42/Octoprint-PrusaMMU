$(() => {
  const PLUGIN_NAME = "prusammu";
  const LOG_PLUGIN_NAME = `plugin_${PLUGIN_NAME}`;
  const STATES = {
    NOT_FOUND: "NOT_FOUND",
    STARTING: "STARTING",
    OK: "OK",
    LOADED: "LOADED",
    UNLOADING: "UNLOADING",
    LOADING: "LOADING",
    PAUSED_USER: "PAUSED_USER",
    ATTENTION: "ATTENTION",
  }
  const FILAMENT_SOURCE_NAMES = {
    SPOOL_MANAGER: "spoolManager",
    FILAMENT_MANAGER: "filamentManager",
  };

  function PrusaMMU2ViewModel(parameters) {
    const self = this;

    self.globalSettings = parameters[0]; // settingsViewModel
    self.loginState = parameters[1]; // loginStateViewModel
    // self.printerState = parameters[2]; // printerStateViewModel
    self.filamentSources = {
      filamentManager: parameters[3], // filamentManagerViewModel
      spoolManager: parameters[4], // spoolManagerViewModel
    };
    self.settings = {};
    self.modal = undefined;

    self.isSimpleDisplayMode = ko.observable(false);
    self.shouldShowNav = ko.observable(false);

    self.navActionText = ko.observable("Not Found");
    self.navActionIcon = ko.observable("fa-times");

    self.navToolText = ko.observable("");
    self.navToolColor = ko.observable("inherited");
    self.navToolIcon = ko.observable("");
    self.navPreviousToolText = ko.observable("");
    self.navPreviousToolColor = ko.observable("inherited");

    /* =============================
     * =====   Nav Functions   =====
     * ============================= */

    /**
     * Returns the text of the mmu state.
     * 
     * @param {string} state - The state of the MMU from the backend
     * @param {number|string} tool - The tool number, ensures we dont have a weird state or ""
     * @param {[{id, name, type, color, enabled}, ...]} filament - The filament object representing
     *                                                              the tool (see getFilamentList())
     */
    const getNavActionText = (state, tool, filament, hasPrevious) => {
      if (state === "" || state === STATES.NOT_FOUND) {
        return gettext("Not Found"); 
      }

      switch (state) {
        case STATES.STARTING:
          return gettext("Starting...");
        case STATES.OK:
          return gettext("Ready");
        case STATES.UNLOADING:
          if (hasPrevious) {
            return gettext("Changing Filament...");
          }
          return gettext("Unloading...");
        case STATES.LOADING:
          if (hasPrevious) {
            return gettext("Changing Filament...");
          }
          return gettext("Loading...");
        case STATES.ATTENTION:
          return gettext("Needs Attention!");
        case STATES.PAUSED_USER:
          return gettext("Awaiting User Input!");
      }

      return getFilamentDisplayName(tool, filament);
    };

    /**
     * Get the icon class that represewnts the state for the nav. Returns the ? if unknown.
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
      if (state === STATES.UNLOADING || state === STATES.LOADING || state === STATES.LOADED) {
        return ""
      }
      
      return "fa-question";
    }

    /**
     * Returns the text of the tool based on the state returned.
     * 
     * @param {number|string} tool - The tool number, ensures we dont have a weird state or ""
     * @param {string} state - The state of the MMU from the backend
     * @param {[{id, name, type, color, enabled}, ...]} filament - The filament object representing
     *                                                              the tool (see getFilamentList())
     */
    const getNavToolText = (tool, state, filament) => {
      if (tool === "") {
        return gettext("Unknown Filament");
      }

      switch (state) {
        case STATES.UNLOADING:
          return gettext("Unloading") + " " + getFilamentDisplayName(tool, filament);
        case STATES.LOADING:
          return gettext("Loading") + " " + getFilamentDisplayName(tool, filament);
      }

      // If we made it here then the tool is loaded.
      return  getFilamentDisplayName(tool, filament);
    };

    /**
     * Gets the color of the tool from settings or leaves it inherited (grey).
     * 
     * @param {int|string} tool - The ID of the tool or ""
     * @param {[{id, name, type, color, enabled}, ...]} filament - The filament object representing
     *                                                              the tool (see getFilamentList())
     */
    const getNavToolColor = (tool, filament) => {
      if (tool === "") {
        return "inherited";
      }

      return getFilamentDisplayColor(filament);
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
      };
      if (Object.keys(iconStates).indexOf(state) !== -1) {
        return iconStates[state];
      }
      
      return "";
    }

    /**
     * Update the nav display based on the state and tool (i.e. show the mmu state)
     *
     * @param {string} state - The state of the MMU from the backend
     * @param {string} tool - The tool id. It _might_ have a T so we strip it here
     * @param {string} previousTool - The previous tool id. It _might_ have a T so we strip it here
     */
    const updateNav = (state, tool, previousTool) => {
      const toolId = parseInt(tool, 10);
      const previousToolId = parseInt(previousTool, 10);
      // Fetch filament data from the correct source
      const filamentList = self.getFilamentList();
      const currentFilament = filamentList.find(f => f.index === toolId);
      const previousFilament = filamentList.find(f => f.index === previousToolId);

      // global state icon & text
      self.navActionText(getNavActionText(state, toolId, currentFilament, !!previousFilament));
      self.navActionIcon(getNavActionIcon(state));

      // Filament specific icons & text
      if (state === STATES.UNLOADING || state === STATES.LOADING || state === STATES.LOADED) {
        if (previousTool && state !== STATES.LOADED) {
          self.navPreviousToolColor(getNavToolColor(previousToolId, previousFilament));
          self.navPreviousToolText(getNavToolText(previousToolId, STATES.UNLOADING, previousFilament));
        } else {
          self.navPreviousToolColor("inherited");
          self.navPreviousToolText("");
        }
        // TODO: handle the final unload where we dont have a "current filament".
        self.navToolColor(getNavToolColor(toolId, currentFilament));
        self.navToolText(getNavToolText(toolId, state, currentFilament));
        self.navToolIcon(getNavToolIcon(state))
      } else {
        self.navToolColor("inherited");
        self.navToolText("");
        self.navToolIcon("");
        self.navPreviousToolColor("inherited");
        self.navPreviousToolText("");
      }

      log(
        "updateNav",
        { 
          "params": { "tool": toolId, "previousTool": previousToolId, "state": state },
          "currentFilament": currentFilament,
          "previousFilament": previousFilament,
          "action": { "text": self.navActionText(), "icon": self.navActionIcon() },
          "tool": { "text": self.navToolText(), "icon": self.navActionIcon(), "color": self.navToolColor() },
          "prevTool": { "text": self.navPreviousToolText(), "color": self.navPreviousToolColor() },
        }
      );
    };

    /**
     * Used for the click event on the nav to open the plugin settings.
     */
     self.openSettings = () => {
      self.globalSettings.show();
      self.globalSettings.selectTab("#settings_plugin_prusammu");
    };

    /* =============================
     * =====  Modal Functions  =====
     * ============================= */

    /**
     * Generates an option from the backend used in the modal. Disabled items will not show.
     * 
     * @param {[{id, name, type, color, enabled}, ...]} filament - The filament object representing
     *                                                              the tool (see getFilamentList())
     */
    const drawSelectOption = (filament) => {
      const color = getFilamentDisplayColor(filament);
      const icon = `<i class="fas fa-pen-fancy" style="color: ${color}"></i> `;
      return icon + getFilamentDisplayName(filament.index, filament);
    };

    /**
     * Handles selection event of the option and passed it to the backend.
     * 
     * @param {int} index - the ID of the tool to use 
     */
    const selectCallback = (index) => {
      log("selectCallback", index);
      return OctoPrint.simpleApiCommand(PLUGIN_NAME, "select", { choice: index });
    };

    /**
     * Closes the modal. duh...
     */
    const closeModal = () => {
      if (self.modal) {
        self.modal.modal("hide");
      }
    };

    /**
     * Opens the modal and generated the filament options.
     */
    const showModal = () => {
      const selections = {};
      const filament = self.getFilamentList();
      filament.forEach(f => {
        // Made a mess, I should have not increased the index anywhere but the display, or not at all...
        selections[f.index] = drawSelectOption(f);
      });

      const opts = {
        title: gettext("Prusa MMU"),
        message: gettext(`Select the filament spool: (From ${self.settings.filamentSource()})`),
        selections: selections,
        maycancel: true,
        onselect: (index) => {
          if (index > -1) {
            selectCallback(index);
          }
        },
        onclose: () => {
          self.modal = undefined;
        }
      };

      self.modal = showSelectionDialog(opts);
      setTimeout(closeModal, self.settings.timeout() * 1000);
    };

    /* =============================
     * ==== Octoprint Functions ====
     * =============================
     * https://docs.octoprint.org/en/master/plugins/viewmodels.html */

    /**
     * Fired when a plugin message is sent from the server.
     * 
     * @param {string} plugin - The name of the plugin that triggered the message.
     * @param {data} - The data sent from the api.
     */
    self.onDataUpdaterPluginMessage = (plugin, data) => {
      if (!self.loginState.isUser() || plugin !== PLUGIN_NAME) {
        return;
      }

      log("onDataUpdaterPluginMessage", plugin, data);
      switch (data.action) {
        case "show":
          showModal();
          break;
        case "close":
          closeModal();
          break;
        case "nav":
         updateNav(data.state, data.tool, data.previousTool);
          break;
        // case "debug": these just exist to get logged and we do that above.
      }
    };

    /**
     * Called just before the settings view model is sent to the server. This is useful, for
     * example, if your plugin needs to compute persisted settings from a custom view model.
     */
    self.onSettingsBeforeSave = () => {
      log("onSettingsBeforeSave");
      self.shouldShowNav(self.settings.displayActiveFilament());
      self.isSimpleDisplayMode(self.settings.simpleDisplayMode());
    };

    /**
     * Called per view model before attempting to bind it to its binding targets.
     */
    self.onBeforeBinding = () => {
      self.settings = self.globalSettings.settings.plugins.prusammu;
    };

    /**
     * Called after the startup of the web app has been completed. Used to show/hide the nav and
     * load the printer state.
     */
    self.onStartupComplete = () => {
      log("onStartupComplete");
      self.shouldShowNav(self.settings.displayActiveFilament());
      self.isSimpleDisplayMode(self.settings.simpleDisplayMode());
      OctoPrint.simpleApiCommand(PLUGIN_NAME, "getmmu");
    };

    /* =============================
     * ==== Filament Functions  ====
     * ============================= */

    /**
     * Get the filament array for the dropdown display. This checks all the sources we have.
     *
     * @returns [{id, name, type, color, enabled}, ...]
     */
    self.getFilamentList = () => {
      let filament = [];
      filament = self.settings.filament().map(f => {
        return {
          enabled: f.enabled(),
          id: parseInt(f.id(), 10),
          index: parseInt(f.id(), 10) - 1,
          name: f.name(),
          type: "",
          color: f.color(),
        };
      }).filter(f => f.enabled);
      log("getFilament Start(internal)", filament, "Source Target:", self.settings.filamentSource());

      if (self.filamentSources.filamentManager !== null && self.settings.filamentSource() === FILAMENT_SOURCE_NAMES.FILAMENT_MANAGER) {
        filament = [];

        try {
          const spools = self.filamentSources.filamentManager.selectedSpools();
          spools?.forEach((spool, i) => {
            if (!spool || i >= 5) {
              return;
            }
            filament.push({
              enabled: true,
              id: i + 1,
              index: i,
              name: spool.name,
              type: spool.profile.material,
              color: spool.color
            });
          });
          log("getFilament filamentManager", filament, spools);
        } catch(e) {
          console.error("Create a github issue with the following:", "prusammu Error: getFilament filamentManager failed.", e)
        }
      } else if (self.filamentSources.spoolManager !== null && self.settings.filamentSource() === FILAMENT_SOURCE_NAMES.SPOOL_MANAGER) {
        filament = [];

        try {
          const spools = self.filamentSources.spoolManager.api_getSelectedSpoolInformations();
          spools?.forEach(spool => {
            if (!spool) {
              return;
            }
            filament.push({
              enabled: true,
              id: parseInt(spool.toolIndex, 10) + 1,
              index: parseInt(spool.toolIndex, 10),
              name: spool.spoolName,
              type: spool.material,
              color: spool.color
            });
          });
          log("getFilament SpoolManager", filament, spools);
        } catch(e) {
          console.error("Create a github issue with the following:", "prusammu Error: getFilament SpoolManager failed.", e)
        }
      } else if (self.settings.filamentSource() === "gcode") {
        filament = self.settings.gcodeFilament().map(f => {
          return {
            enabled: true,
            id: parseInt(f.id(), 10),
            index: parseInt(f.id(), 10) - 1,
            name: f.name(),
            type: "",
            color: f.color(),
          };
        });
        log("getFilament gcode", filament);
      }

      // Catchall if we got zero back, default to showing something.
      if (filament.length === 0) {
        filament = [
          {id: 1, index: 0, name: "", type: "", color: "", enabled: true},
          {id: 2, index: 1, name: "", type: "", color: "", enabled: true},
          {id: 3, index: 2, name: "", type: "", color: "", enabled: true},
          {id: 4, index: 3, name: "", type: "", color: "", enabled: true},
          {id: 5, index: 4, name: "", type: "", color: "", enabled: true},
        ];
        log("getFilament fallback", filament);
      }

      return filament;
    }

    /**
     * Get the nav display name of the filament.
     *
     * @param {number} tool 
     * @param {[{id, name, type, color, enabled}, ...]} filament - The filament object representing
     *                                                              the tool (see getFilamentList())
     */
    const getFilamentDisplayName = (tool, filament) => {
      const index = self.settings.indexAtZero() ? tool : tool + 1;
      try {
        if (!filament.name) {
          return gettext(`Filament ${index}`);
        }

        let display = `${index}: ${filament.name}`;
        if (filament.type) {
          display += ` (${filament.type})`;
        }
        return display;
      } catch(e) {
        return `${index}: ${gettext("Unknown Filament")}`;
      }
    }

    /**
     * Get the nav display color of the filament.
     *
     * @param {[{id, name, type, color, enabled}, ...]} filament - The filament object representing
     *                                                              the tool (see getFilamentList())
     */
    const getFilamentDisplayColor = (filament) => {
      return filament && filament.color ? filament.color : "inherited";
    }

    /* =============================
     * =====  Misc. Functions  =====
     * ============================= */

    /**
     * Simple function to log out debug messages if debug is on. Use like you would console.log().
     * 
     * @param {...any} args - arguments to pass directly to console.warn.
     */
    const log = (...args) => {
      if (!self.settings.debug()) {
        return;
      }
      const d = new Date();
      const showtime = `[${d.getHours()}:${d.getMinutes()}:${d.getSeconds()}]`
      console.log(String.fromCodePoint(0x1F6A9), showtime, `${LOG_PLUGIN_NAME}:`, ...args);
    }
  }

  OCTOPRINT_VIEWMODELS.push({
    construct: PrusaMMU2ViewModel,
    dependencies: [
      "settingsViewModel","loginStateViewModel", "printerStateViewModel",
      "filamentManagerViewModel","spoolManagerViewModel"
    ],
    optional: ["filamentManagerViewModel","spoolManagerViewModel"],
    elements: ["#navbar_plugin_prusammu"]
  });
});