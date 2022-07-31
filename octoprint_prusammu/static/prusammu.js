$(() => {
  const DEBUG = true;
  const PLUGIN_NAME = "prusammu";
  const LOG_PLUGIN_NAME = `plugin_${PLUGIN_NAME}`;

  function PrusaMMU2ViewModel(parameters) {
    const self = this;
    if (DEBUG) {
      window.PrusaMMU2 = self;
    }

    self.global_settings = parameters[0];
    self.loginState = parameters[1];
    self.settings = {};
    self.modal = undefined;
  
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
     * @param {int|string} tool - The tool number, used to ensure we dont have a weird state or ""
     * @param {string} state - The state of the MMU from the backend
     */
    const getToolText = (tool, state) => {
       // This needs to be better. But if we load and we dont know the state then just assume it's
       // ready.
      if (state === "") {
        return gettext("Not Found"); 
      }

      switch (state) {
        case "OK":
          return gettext("Ready");
        case "UNLOADING":
          return gettext("Unloading...");
        case "LOADING":
          return gettext("Loading...");
        case "ATTENTION":
          return gettext("Needs Attention!");
        case "PAUSED_USER":
          return gettext("Awaiting User Input!");
        default:
          break;
      }
      // This likely means the printer isn't mounted.
      if (tool === "") {
        return gettext("Unknown Filament");
        
      }
      // If we made it here then we should assume the tool is loaded.
      const name = self.settings.filament()[tool].name();
      if (name === "") {
        return  gettext(`Filament ${(tool + 1)}`);
      }
      return `${(tool + 1)}: ${name}`;
    };

    /**
     * Gets the color of the tool from settings or leaves it inherited(grey).
     * 
     * @param {int|string} tool - The ID of the tool or ""
     * @param {string} state - The state of the MMU
     */
    const getToolColor = (tool, state) => {
      if (tool === "" || state === "OK") {
        return "inherited";
      }
      try {
        const color = self.settings.filament()[tool].color();
        if (!color) {
          return "inherited";
        }
        return color;
      } catch (e) {
        console.error(`${LOG_PLUGIN_NAME}: getToolColor Error`, e);
        return "inherited";
      }
    };

    /**
     * Update the nav display based on the state and tool (i.e. show the mmu state)
     * 
     * @param {string} tool - The tool id. It _might_ have a T so we strip it here
     * @param {string} state - The state of the MMU from the backend
     */
    const updateNav = (tool, state) => {
      const toolId = tool === "" ? "" : parseInt(tool.replace("T", ""));

      self.navText(getToolText(toolId, state));
      self.navColor(getToolColor(toolId, state));
      
      const iconStates = {
        "OK": "fa-check",
        "LOADED": "fa-pen-fancy",
        "UNLOADING": "fa-long-arrow-alt-up",
        "LOADING": "fa-long-arrow-alt-down",
        "PAUSED_USER": "fa-fingerprint",
        "ATTENTION": "fa-exclamation-triangle",
      };
      if (Object.keys(iconStates).indexOf(state) !== -1) {
        self.navIcon(iconStates[state]);
      } else {
        self.navIcon("fa-question");
      }

      log(
        "updateNav",
        { 
          "Params": { "tool": tool, "state": state },
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
      // I'm lazy and constantly reopening settings is more work than I want to put in.
      const tab = DEBUG ? "#settings_plugin_pluginmanager" : "#settings_plugin_prusammu";
      self.global_settings.selectTab(tab);
      // Find the plugin manager view and open the repo button.
      if (DEBUG) {
        self.global_settings.allViewModels.find(
          v => v.constructor.name === "PluginManagerViewModel"
        ).showRepository(true);
      }
    };

    /* =============================
     * =====  Modal Functions  =====
     * ============================= */

    /**
     * Generates an option from the backend used in the modal. Disabled items will not show.
     * 
     * @param {object} filament - The filament object from settings. This expects the object to not
     *                            be the function but the return of it.
     */
    const drawSelectOption = (filament) => {
      let color = "inherited";
      if (filament.color()) {
        color = filament.color();
      }
      self.navColor(color);
      const name = filament.name();
      const icon = `<i class="fas fa-pen-fancy" style="color: ${color}"></i> `;
      if (name === "") {
        return icon + gettext(`Filament ${filament.id()}`);
      }
      return `${icon} ${filament.id()}: ${filament.name()}`;
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
      const filament = self.settings.filament();

      const selections = {};
      filament.forEach((f, i) => {
        if (f.enabled()) {
          selections[i] = drawSelectOption(f);
        }
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
         updateNav(data.tool, data.state);
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
      updateNav(self.settings.mmuTool(), self.settings.mmuState());
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
      checkPrinterState();
    };

    /**
     * The server has connected to the printer.
     * 
     * @param {{port: int, baudrate: int}} payload - The data related to printer
     */
    self.onEventConnected = function(payload) {
      log("onEventConnected", payload);
      checkPrinterState();
    };

    /**
     * The server has disconnected from the printer. Used to zero out the MMU data on the nav.
     */
    self.onEventDisconnected = function() {
      log("onEventDisconnected");
      updateNav("", "");
    };

    self.onEventPrintDone = function() {
      log("onEventPrintDone");
      checkPrinterState();
    }

    /* =============================
     * =====  Misc. Functions  =====
     * ============================= */

    /**
     * We get the printer state to avoid tool getting "stuck" issues and showing the wrong state
     * (like filament loaded when printer is off). There's probably a cleaner way to do this but
     * I'm too lazy to figure it out.
     */
    const checkPrinterState = () => {
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
            updateNav("", mmuState); // send it the "ready" signal.
            return;
          }
          const tempMmuState = self.settings.mmuState();
          const tempMmuTool = self.settings.mmuTool();
          return updateNav(tempMmuTool, tempMmuState);
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
    dependencies: ["settingsViewModel","loginStateViewModel", "printerStateViewModel"],
    elements: ["#navbar_plugin_prusammu"]
  });
});