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
    LOADING_MMU: "LOADING_MMU",
    CUTTING: "CUTTING",
    EJECTING: "EJECTING",
  }
  const RESPONSES = {
    PROCESSING: "P",
    ERROR: "E",
    FINISHED: "F",
    ACCEPTED: "A",
    REJECTED: "R",
    BUTTON: "B",
  }
  const FILAMENT_SOURCE_NAMES = {
    SPOOL_MANAGER: "spoolManager",
    FILAMENT_MANAGER: "filamentManager",
  };
  const MAX_FILAMENT_RETRY = 5;

  function PrusaMMU2ViewModel(parameters) {
    const self = this;
    // Used to refresh the UI when the user tabs away.
    let isActiveTab = true;
    // Track if we've loaded the filament or not. Useful for spool managers that are slow to load.
    self.filamentRetryCount = 0;
    self._prusaVersion;
    self._overrideFilament = "";
    // Keep track so we can refresh if needed
    self._toolId = 0;
    self._previousToolId = 0;
    self._toolState = "";
    self._response = "";
    self._responseData = "";
    self._lastError = "";

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
    self.isAdvancedDisplayMode = ko.observable(true);
    self.shouldShowNav = ko.observable(false);

    self.navActionText = ko.observable("Unknown");
    self.navActionIcon = ko.observable("fa-times");

    self.navToolText = ko.observable("");
    self.navToolColor = ko.observable("inherited");
    self.navToolIcon = ko.observable("");
    self.navPreviousToolText = ko.observable("");
    self.navPreviousToolColor = ko.observable("inherited");

    self.navMessageText = ko.observable("");

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
    const getNavActionText = (state, tool, filament, previous) => {
      if (state === "" || state === STATES.NOT_FOUND) {
        return gettext("Unknown"); 
      }

      switch (state) {
        case STATES.STARTING:
          return gettext("Starting...");
        case STATES.OK:
          return gettext("Idle");
        case STATES.UNLOADING:
          if (!!previous && !!filament) {
            return gettext("Changing Filament...");
          }
          return gettext("Unloading...");
        case STATES.LOADING:
          if (!!previous && !!filament) {
            return gettext("Changing Filament...");
          }
          return gettext("Loading...");
        case STATES.ATTENTION:
          return gettext("Needs Attention!");
        case STATES.PAUSED_USER:
          return gettext("Awaiting User Input!");
        case STATES.LOADING_MMU:
          return gettext("Preloading...");
        case STATES.CUTTING:
          return gettext("Cutting...");
        case STATES.EJECTING:
          return gettext("Ejecting...");
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
        case STATES.LOADING_MMU:
          return gettext("Preloading") + " " + getFilamentDisplayName(tool, filament);
        case STATES.CUTTING:
          return gettext("Cutting") + " " + getFilamentDisplayName(tool, filament);
        case STATES.EJECTING:
          return gettext("Ejecting") + " " + getFilamentDisplayName(tool, filament);
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
        [STATES.LOADING_MMU]: "fa-long-arrow-alt-right",
        [STATES.CUTTING]: "fa-cut",
        [STATES.EJECTING]: "fa-eject",
      };
      if (Object.keys(iconStates).indexOf(state) !== -1) {
        return iconStates[state];
      }
      
      return "";
    }

   /**
    * Get formatted text for the navbar message display based on the response code and data
    * 
    * @param {string} response - The single letter response code
    * @param {string} responseData - The hexidecimal response data
    */
    const getNavMessageText = (response, responseData) => {
      switch (response) {
        case RESPONSES.PROCESSING:
          return self.processMmuProgress(responseData);
        case RESPONSES.ERROR:
          return self.processMmuError(responseData).title;
        case RESPONSES.FINISHED:
          // Return blank string if finished. It looks nicer
          return "";
        case RESPONSES.ACCEPTED:
          return gettext("Starting");
        case RESPONSES.REJECTED:
          return gettext("Command Rejected!");
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
    const updateNav = (state, tool, previousTool, response, responseData) => {
      const toolId = parseInt(tool, 10);
      const previousToolId = parseInt(previousTool, 10);
      // Remember these, we may need them again
      self._toolId = toolId;
      self._previousToolId = previousToolId;
      self._toolState = state;
      self._response = response;
      self._responseData = responseData;
      // Fetch filament data from the correct source
      const filamentList = self.getFilamentList();
      const currentFilament = filamentList.find(f => f.index === toolId);
      const previousFilament = filamentList.find(f => f.index === previousToolId);

      // If we didn't load the current filament then simply try again.
      if (!currentFilament) {
        self.delayedRefreshNav(filamentList);
      }

      // global state icon & text
      self.navActionText(getNavActionText(state, toolId, currentFilament, previousFilament));
      self.navActionIcon(getNavActionIcon(state));

      // If response was present in the log we're dealing with an MMU running 3.0.0 so let's show more info.
      if (response) {
        // If there was an error then let's show a popup to the user. But only once.
        if (response === RESPONSES.ERROR && !self._lastError) {
          self._lastError = responseData;
          showErrorPopupNotification(self.processMmuError(responseData));
        } else {
          self._lastError = "";
        }
        self.navMessageText(getNavMessageText(response, responseData));
      } else {
        self.navMessageText("");
      }

      // Filament specific icons & text
      if (
        state === STATES.UNLOADING || state === STATES.LOADING || state === STATES.LOADED ||
        state === STATES.LOADING_MMU || state === STATES.CUTTING || state === STATES.EJECTING
      ) {
        // For Load / Unload, If previousTool exists, then that means this is a filament change.
        // Manually set the states to fix the arrow directions
        if (((state == STATES.LOADING) || (state ==STATES.UNLOADING)) && previousTool) {
            self.navToolColor(getNavToolColor(toolId, currentFilament));
            self.navToolText(getNavToolText(toolId, STATES.LOADING, currentFilament));
            self.navToolIcon(getNavToolIcon(STATES.LOADING));

            self.navPreviousToolColor(getNavToolColor(previousToolId, previousFilament));
            self.navPreviousToolText(getNavToolText(previousToolId, STATES.UNLOADING, previousFilament));
        // If previousTool doesn't exist, or if it's not a load/unload, it's just a normal single display
        } else {
          self.navToolColor(getNavToolColor(toolId, currentFilament));
          self.navToolText(getNavToolText(toolId, state, currentFilament));
          self.navToolIcon(getNavToolIcon(state));

          self.navPreviousToolColor("inherited");
          self.navPreviousToolText("");
        }
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
          "params": {
            "tool": toolId,
            "previousTool": previousToolId,
            "state": state,
            "response": response,
            "responseData": responseData
          },
          "currentFilament": currentFilament,
          "previousFilament": previousFilament,
          "action": { "text": self.navActionText(), "icon": self.navActionIcon() },
          "tool": { "text": self.navToolText(), "icon": self.navActionIcon(), "color": self.navToolColor() },
          "prevTool": { "text": self.navPreviousToolText(), "color": self.navPreviousToolColor() },
          "response": self._response,
          "responseData": self._responseData,
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

    /**
     * Delay a nav refresh and then try again. We're probably waiting for a spool manager. It will
     * wait MAX_FILAMENT_RETRY times and do a slow backoff.
     * 
     * @param {[{id, name, type, color, enabled}, ...]} filamentList - The filament object
     *                                                                 representing the tool
     *                                                                 (see getFilamentList())
     */
    self.delayedRefreshNav = (filamentList) => {
      if (
        self.filamentRetryCount++ >= MAX_FILAMENT_RETRY ||
        (filamentList.length >= 5 && !filamentList.includes(null))
      ) {
        return;
      }
      setTimeout(() => {
        log(
          "delayedRefreshNav", self.filamentRetryCount,
          { 
            "state": self._toolState,
            "tool": self._toolId,
            "prevTool": self._previousToolId,
            "response": self._response,
            "responseData": self._responseData
          }
        );
        updateNav(self._toolState, self._toolId, self._previousToolId, self._response, self._responseData);
      }, 1000 * self.filamentRetryCount);
    };

    // A hacky way to avoid spamming the user with errors.
    let _notifyEle = undefined;

    /**
     * When we get an error, show a popup as well with the link.
     * 
     * This function will rewrite the error the user sees if a new error pops in and they already
     * have one from us. users only really need the last error.
     * 
     * @param {object} mmuError - The error object
     */
    const showErrorPopupNotification = (mmuError) => {
      const title = `Prusa MMU: ${mmuError.title} (#${mmuError.code})`;
      const text = `<p>${mmuError.text}</p>` +
                   `<p><a target="_blank" href="${mmuError.url}">${mmuError.url}</a></p>`;
      if (!_notifyEle) {
        _notifyEle = new PNotify({ title, text, type: "error", hide: false });
        return;
      }
      // Doesn't do anything, for house keeping.
      _notifyEle.options.title = title;
      _notifyEle.options.text = text;
      // Actually sets the values.
      _notifyEle.title_container.text(title);
      _notifyEle.text_container.html(text);
      // If they had closed it show it again.
      if (_notifyEle.state !== "open") {
        _notifyEle.open();
      }
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
      self._overrideFilament = index === "skip" ? "" : index;
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

      // Add the skip option at the bottom.
      if (self._prusaVersion !== "MK3") {
        selections["skip"] = "Skip (No filament override)";
      }

      const opts = {
        title: gettext("Prusa MMU"),
        message: gettext(`Select the filament spool: (From ${self.settings.filamentSource()})`),
        selections: selections,
        maycancel: true,
        onselect: (index) => {
          log("Selection:", index);
          selectCallback(index);
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
          updateNav(data.state, data.tool, data.previousTool, data.response, data.responseData);
          if (data.prusaVersion) {
            self._prusaVersion = data.prusaVersion;
          }
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
      self.isAdvancedDisplayMode(self.settings.advancedDisplayMode() && !self.settings.simpleDisplayMode());
    };

    /**
     * Called per view model before attempting to bind it to its binding targets.
     */
    self.onBeforeBinding = () => {
      self.settings = self.globalSettings.settings.plugins.prusammu;
    };

    /**
     * Called when the user opens the settings menu. This is when we bind the color pickers and 
     * show / hide the printer specific messages.
     */
    self.onSettingsShown = () => {
      bindPickers();
      showError();
      if (self._prusaVersion === "MK3") {
        $("#settings_plugin_prusammu .mk4").addClass("hide");
        $("#settings_plugin_prusammu .mk3").removeClass("hide");
      } else if (self._prusaVersion !== null && self._prusaVersion !== "MK3") {
        $("#settings_plugin_prusammu .mk3").addClass("hide");
        $("#settings_plugin_prusammu .mk4").removeClass("hide");
      }
      $("#settings_plugin_prusammu .prusa-version").text(self._prusaVersion ? self._prusaVersion.replace("_", ".") : "...");
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
      setupRefocusCheck();
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
      log("getFilament internal", filament, "Source Target:", self.settings.filamentSource());

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
          console.error("Create a github issue with the following:", "prusammu Error: getFilament filamentManager failed.", e);
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
          console.error("Create a github issue with the following:", "prusammu Error: getFilament SpoolManager failed.", e);
        }
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
     * Used to watch when the browser tab is focused. This makes a call to check the mmu state to
     * avoid a stale event. If the tab wasn't opened when the new command happened we might have
     * missed it.
     */
    const setupRefocusCheck = () => {
      log("setupRefocusCheck");
      setInterval(() => {
        if (document.hidden) {
          isActiveTab = false;
          return;
        }
        if (!document.hidden && isActiveTab) {
          return;
        }
        log("setupRefocusCheck:", "Refreshing nav");
        isActiveTab = true;
        OctoPrint.simpleApiCommand(PLUGIN_NAME, "getmmu");
      }, 10000);
    };

    /**
     * Binds the color picker to the buttons in the settings menu. We call this every time the
     * settings menu is opened but it will not rebind (see colorPicker.init) unless settings is
     * saved, a settings save seems to destroy the settings view and rebuild it.
     */
    const bindPickers = () => {
      const palette = [
        "#FFFFFF", "#f0f8ff", "#C0C0C0", "#808080", "#000000",
        "#add8e6", "#008080", "#008b8b", "#0000FF", "#00008B",
        "#00FF00", "#008000", "#006400", "#800080", "#9400d3",
        "#fff700", "#daa520", "#d2b48c", "#8e4e24", "#cd7f32",
        "#ffc0cb", "#FF0000", "#8b0000", "#cc5500", "#ff8c00",
        "#ff003f", "#7df9ff", "#66ff00", "#bf00ff", "#ffff00"
      ];
      $("#settings_plugin_prusammu .color-dropdown").each((index, element) => {
        $(element).colorPick({
          initialColor: self.settings.filament()[index].color(),
          paletteLabel: gettext("Filament color:"),
          customLabel: gettext("Custom color:"),
          recentLabel: gettext("Recent color:"),
          allowCustomColor: true,
          drawUp: (index > 2),
          palette: palette,
          onColorSelected: function() {
            const index = this.element.attr("data-index");
            self.settings.filament()[index].color(this.color);
            log("colorPick", index, this.color);
          }
        });
      });
    };

    /**
     * Used when settings are shown, if the MMU is in an error state we impose an alert box in settings with more info.
     */
    const showError = () => {
      const idPrefix = "#settings_plugin_prusammu #prusammu_error_";
      if (!(self._response === RESPONSES.ERROR)) {
        $(`${idPrefix}zone`).addClass("hide");
        return;
      }

      const error = self.processMmuError(self._responseData);
      $(`${idPrefix}title`).text(error.title);
      $(`${idPrefix}code`).text(error.code);
      $(`${idPrefix}text`).text(error.text);
      $(`${idPrefix}url`).text(error.url).attr("href", error.url);
      $(`${idPrefix}zone`).removeClass("hide");
    };

    /**
     * Given the error code it generates an error object with more information.
     * 
     * @param {string} code - The error code hexidecimal value as a string
     * @returns {code, title, text, url}
     */
    self.processMmuError = (code) => {
      const error = getMmuError(code);
      return {
        code: error.code,
        title: error.title,
        text: error.text,
        url: `https://prusa.io/${error.code}`,
      };
    };

   /**
    * Given the progress code it returns a string containing the progress message
    *
    * @param {string} code - The progress code hexidecimal value as a string
    * @returns string
    */
    self.processMmuProgress = (code) => getMmuProgress(code);

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