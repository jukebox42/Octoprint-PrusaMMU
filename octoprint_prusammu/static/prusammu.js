$(() => {
  const DEBUG = true;
  const PLUGIN_NAME = "prusammu";
  const LOG_PLUGIN_NAME = `plugin_${PLUGIN_NAME}`;
  const STATES = {
    OK: "OK",
    LOADED: "LOADED",
    UNLOADING: "UNLOADING",
    LOADING: "LOADING",
    PAUSED_USER: "PAUSED_USER",
    ATTENTION: "ATTENTION",
  }

  function PrusaMMU2ViewModel(parameters) {
    const self = this;
    if (DEBUG) {
      window.PrusaMMU2 = self;
    }

    self.global_settings = parameters[0]; // settingsViewModel
    self.loginState = parameters[1]; // loginStateViewModel
    // self.printerState = parameters[2]; // printerStateViewModel
    self.filamentSources = {
      filamentManager: parameters[3], // filamentManagerViewModel
      spoolManager: parameters[4], // spoolManagerViewModel
    };
    self.settings = {};
    self.modal = undefined;
  
    self.debug = ko.observable(DEBUG);
    self.isSimpleDisplayMode = ko.observable(false);
    self.shouldShowNav = ko.observable(false);
    self.navText = ko.observable("Not Found");
    self.navColor = ko.observable("inherited");
    self.navIcon = ko.observable("fa-times");

    /* =============================
     * =====   Nav Functions   =====
     * ============================= */

    /**
     * Returns the text of the tool based on the state returned.
     * 
     * @param {number|string} tool - The tool number, ensures we dont have a weird state or ""
     * @param {string} state - The state of the MMU from the backend
     * @param {[{id, name, type, color, enabled}, ...]} filament - The filament object representing
     *                                                              the tool (see getFilamentList())
     */
    const getToolText = (tool, state, filament) => {
       // This needs to be better. But if we load and we dont know the state then just assume it's
       // ready.
      if (state === "") {
        return gettext("Not Found"); 
      }

      switch (state) {
        case STATES.OK:
          return gettext("Ready");
        case STATES.UNLOADING:
          return gettext("Unloading...");
        case STATES.LOADING:
          return gettext("Loading...");
        case STATES.ATTENTION:
          return gettext("Needs Attention!");
        case STATES.PAUSED_USER:
          return gettext("Awaiting User Input!");
        default:
          break;
      }
      // This likely means the printer isn't mounted.
      if (tool === "") {
        return gettext("Unknown Filament");
      }

      // If we made it here then we should assume the tool is loaded.
      return getFilamentDisplayName(tool, filament);
    };

    /**
     * Gets the color of the tool from settings or leaves it inherited(grey).
     * 
     * @param {int|string} tool - The ID of the tool or ""
     * @param {string} state - The state of the MMU
     * @param {[{id, name, type, color, enabled}, ...]} filament - The filament object representing
     *                                                              the tool (see getFilamentList())
     */
    const getToolColor = (tool, state, filament) => {
      if (tool === "" || state === STATES.OK) {
        return "inherited";
      }

      return getFilamentDisplayColor(filament);
    };

    /**
     * Get the icon class that represewnts the state for the nav. Returns the ? if unknown.
     * 
     * @param {string} state - The state of the MMU
     */
    const getNavIcon = (state) => {
      const iconStates = {
        [STATES.OK]: "fa-check",
        [STATES.LOADED]: "fa-pen-fancy",
        [STATES.UNLOADING]: "fa-long-arrow-alt-up",
        [STATES.LOADING]: "fa-long-arrow-alt-down",
        [STATES.PAUSED_USER]: "fa-fingerprint",
        [STATES.ATTENTION]: "fa-exclamation-triangle",
      };
      if (Object.keys(iconStates).indexOf(state) !== -1) {
        return iconStates[state];
      }
      
      return "fa-question";
    }

    /**
     * Update the nav display based on the state and tool (i.e. show the mmu state)
     * 
     * @param {string} tool - The tool id. It _might_ have a T so we strip it here
     * @param {string} previousTool - The previous tool id. It _might_ have a T so we strip it here
     * @param {string} state - The state of the MMU from the backend
     */
    const updateNav = (tool, previousTool, state) => {
      const toolId = tool === "" ? "" : parseInt(tool.replace("T", ""));
      const prevToolId = previousTool === "" ? "" : parseInt(previousTool.replace("T", ""));

      // Fetch filament data from the correct source
      const filamentList = self.getFilamentList();
      const currentFilament = filamentList.find(f => f.id === toolId + 1);
      const previousFilament = filamentList.find(f => f.id === prevToolId + 1);

      
      // TODO: update this to show two icons, unloading and loading
      if (state === STATES.UNLOADING) {
        log("updateNav Unloading", previousFilament)
        self.navColor(getToolColor(toolId, state, previousFilament));
        self.navText(getToolText(toolId, state, previousFilament));
      } else {
        log("updateNav NOT Unloading", currentFilament)
        self.navText(getToolText(toolId, state, currentFilament));
        self.navColor(getToolColor(toolId, state, currentFilament));
      }
      self.navIcon(getNavIcon(state));

      log(
        "updateNav",
        { 
          "Params": { "tool": tool, "previousTool": previousTool, "state": state },
          "currentFilament": currentFilament,
          "previousFilament": previousFilament,
          "navText": self.navText(),
          "navColor": self.navColor(),
          "navIcon": self.navIcon(),
        }
      );
    };

    /**
     * Used for the click event on the nav to open the plugin settings.
     */
     self.openSettings = () => {
      self.global_settings.show();
      self.global_settings.selectTab("#settings_plugin_prusammu");
    };

    /**
     * I'm lazy and constantly reopening settings is more work than I want to put in.
     */
    self.openDebugSettings = () => {
      self.global_settings.show();
      self.global_settings.selectTab("#settings_plugin_pluginmanager");
      // Find the plugin manager view and open the repo button.
      self.global_settings.allViewModels.find(
          v => v.constructor.name === "PluginManagerViewModel"
        ).showRepository(true);
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
      return icon + getFilamentDisplayName((parseInt(filament.id) -1), filament);
    };

    /**
     * Handles selection event of the option and passed it to the backend.
     * 
     * @param {int} index - the ID of the tool to use 
     */
    const selectCallback = (index) => {
      log("selectCallback", index, `(Filament ${(index + 1)})`);
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
        selections[f.id - 1] = drawSelectOption(f);
      });

      const opts = {
        title: gettext("Prusa MMU"),
        message: gettext("Select the filament spool:"),
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
    self.onDataUpdaterPluginMessage = function(plugin, data) {
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
         updateNav(data.tool, data.previousTool, data.state);
          break;
        // case "debug": these just exist to get logged and we do that above.
      }
    };

    /**
     * Called just before the settings view model is sent to the server. This is useful, for
     * example, if your plugin needs to compute persisted settings from a custom view model.
     */
    self.onSettingsBeforeSave = function () {
      self.shouldShowNav(self.settings.displayActiveFilament());
      self.isSimpleDisplayMode(self.settings.simpleDisplayMode());

      // If a user changes a filament in settings mid print we should listen for that and redraw.
      updateNav(self.settings.mmuTool(), self.settings.mmuPreviousTool(), self.settings.mmuState());
    };

    /**
     * Called per view model before attempting to bind it to its binding targets.
     */
    self.onBeforeBinding = function () {
      self.settings = self.global_settings.settings.plugins.prusammu;
    };

    /**
     * Called after the startup of the web app has been completed. Used to show/hide the nav and
     * load the printer state.
     */
    self.onStartupComplete = function() {
      self.shouldShowNav(self.settings.displayActiveFilament());
      self.isSimpleDisplayMode(self.settings.simpleDisplayMode());
      self.checkPrinterState();
    };

    /**
     * The server has connected to the printer.
     * 
     * @param {{port: int, baudrate: int}} payload - The data related to printer
     */
    self.onEventConnected = function(payload) {
      log("onEventConnected", payload);
      self.checkPrinterState();
    };

    /**
     * The server has disconnected from the printer. Used to zero out the MMU data on the nav.
     */
    self.onEventDisconnected = function() {
      log("onEventDisconnected");
      updateNav("", "", "");
    };

    /**
     * The print has completed successfully.
     */
    self.onEventPrintDone = function() {
      log("onEventPrintDone");
      self.checkPrinterState();
    }

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
          id: f.id(),
          name: f.name(),
          type: "",
          color: f.color(),
        };
      }).filter(f => f.enabled);
      log("getFilament Start", filament);

      if (self.filamentSources.filamentManager !== null && self.settings.filamentSource() === "filamentManager") {
        filament = [];

        const spools = self.filamentSources.filamentManager.selectedSpools();
        spools?.forEach((spool, i) => {
          if (!spool || i >= 5) {
            return;
          }
          filament.push({
            enabled: true,
            id: i + 1,
            name: spool.name,
            type: spool.profile.material,
            color: spool.color
          });
        });
        log("getFilament filamentManager", filament, spools);
      } else if (self.filamentSources.spoolManager !== null && self.settings.filamentSource() === "spoolManager") {
        filament = [];

        const spools = self.filamentSources.spoolManager.api_getSelectedSpoolInformations();
        spools?.forEach(spool => {
          if (!spool || i >= 5) {
            return;
          }
          filament.push({
            enabled: true,
            id: spool.toolIndex + 1,
            name: spool.spoolName,
            type: spool.material,
            color: spool.color
          });
        });
        log("getFilament SpoolManager", filament, spools);
      } else if (self.settings.filamentSource() === "gcode") {
        filament = self.settings.gcodeFilament().map(f => {
          return {
            enabled: true,
            id: f.id(),
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
          {id: 1, name: "", type: "", color: "", enabled: true},
          {id: 2, name: "", type: "", color: "", enabled: true},
          {id: 3, name: "", type: "", color: "", enabled: true},
          {id: 4, name: "", type: "", color: "", enabled: true},
          {id: 5, name: "", type: "", color: "", enabled: true},
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
      log("getFilamentDisplayName", tool, filament);
      try {
        if (!filament.name) {
          return gettext(`Filament ${(tool + 1)}`);
        }

        let display = `${filament.id}: ${filament.name}`;
        if (filament.type) {
          display += ` (${filament.type})`;
        }
        return display;
      } catch(e) {
        return `${(tool + 1)}: ${gettext("Unknown Filament")}`;
      }
    }

    /**
     * Get the nav display color of the filament.
     *
     * @param {[{id, name, type, color, enabled}, ...]} filament - The filament object representing
     *                                                              the tool (see getFilamentList())
     */
    const getFilamentDisplayColor = (filament) => {
      log("getFilamentDisplayColor", filament);
      return filament && filament.color ? filament.color : "inherited";
    }

    /* =============================
     * =====  Misc. Functions  =====
     * ============================= */

    /**
     * We get the printer state to avoid tool getting "stuck" issues and showing the wrong state
     * (like filament loaded when printer is off). There's probably a cleaner way to do this but
     * I'm too lazy to figure it out.
     */
    self.checkPrinterState = () => {
      // This will fail if the printer isn't mounted.
      OctoPrint.printer.getFullState({exclude: ["temperature", "sd"]}).then(ret => {
        try {
          log("getFullState", ret);
          const flags = ret.state.flags;
          // If the printer is "ready", then it's not printing so show ready. Also clear out any
          // values, this is hoakey but works.
          if (flags.ready && !flags.printing && !flags.paused) {
            const mmuState = ret.state.text === "Operational" ? "OK" : ""
            self.global_settings.saveData({
              plugins: {
                prusammu: {
                  mmuState: mmuState,
                  mmuTool: "",
                }
              }
            });
            updateNav("", "", mmuState); // send it the "ready" signal.
            return;
          }
          const tempMmuState = self.settings.mmuState();
          const tempMmuTool = self.settings.mmuTool();
          const tempMmuPreviousTool = self.settings.mmuPreviousTool();
          return updateNav(tempMmuTool, tempMmuPreviousTool, tempMmuState);
        } catch (e) {
          console.error(`${LOG_PLUGIN_NAME}: onStartupComplete Error`, e);
        }
      });
    };

    /**
     * Simple function to log out debug messages if DEBUG is on. Use like you would console.log().
     * 
     * @param {...any} args - arguments to pass directly to console.warn.
     */
    const log = (...args) => {
      if (!DEBUG) {
        return;
      }
      console.log(String.fromCodePoint(0x1F6A9), `${LOG_PLUGIN_NAME}:`, ...args);
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