(function (global, factory) {
  if (typeof define === "function" && define.amd) {
    define(["OctoPrintClient"], factory);
  } else {
    factory(global.OctoPrintClient);
  }
})(this, function(OctoPrintClient) {
  var OctoPrintPrusaMMU = function(base) {
    this.base = base;
  };

  OctoPrintPrusaMMU.prototype.select = function(index, opts) {
    var data = {
      choice: index
    };
    return this.base.simpleApiCommand("prusammu", "select", data, opts);
  };

  OctoPrintClient.registerPluginComponent("prusammu", OctoPrintPrusaMMU);
  return OctoPrintPrusaMMU;
});

$(function() {
  function PrusaMMU2ViewModel(parameters) {
    var self = this;

    self.settings = parameters[0];
    self.loginState = parameters[1];

    // ===== Nav =====

    self.mmu = {
      state: "UNKNOWN",
      text: "None",
      color: "inherited",
      tool: false
    };

    self._update_nav = function(tool, state) {
      console.log("plugin_prusammu: _update_nav", tool, state);

      self.mmu.tool = tool ? tool : false;
      self.mmu.state = state;
      self.mmu.text = self._get_tool_name(tool, state);
      self.mmu.color = self._get_tool_color(tool);
      self._set_nav();
    }

    self._get_tool_color = function(tool) {
      if (tool === "") {
        return "inherited";
      }
      var color = self.settings.settings.plugins.prusammu.filament()[tool].color();
      if (!color) {
        return "inherited";
      }
      return color;
    }

    self._get_tool_name = function (tool, state) {
      if (state === "OK") {
        return gettext("Ready");
      }
      if (state === "UNLOADING") {
        return gettext("Unloading...");
      }
      if (state === "LOADING") {
        return gettext("Loading...");
      }
      if (state === "ATTENTION") {
        return gettext("Needs Attention!");
      }
      if (state === "PAUSED_USER") {
        return gettext("Awaiting User Input!");
      }
      if (tool === "") {
        return "None";
      }
      return gettext("Filament ") +
             (tool + 1) +
             ": " +
             self.settings.settings.plugins.prusammu.filament()[tool.replace("T", "")].name();
    }

    self._set_nav = function() {
      $("#navbar_plugin_prusammu_icon").toggleClass("fa-pen-fancy", self.mmu.state === "LOADED");
      $("#navbar_plugin_prusammu_icon").toggleClass("fa-long-arrow-alt-up", self.mmu.state === "UNLOADING");
      $("#navbar_plugin_prusammu_icon").toggleClass("fa-long-arrow-alt-down", self.mmu.state === "LOADING");
      $("#navbar_plugin_prusammu_icon").toggleClass("fa-fingerprint", self.mmu.state === "PAUSED_USER");
      $("#navbar_plugin_prusammu_icon").toggleClass("fa-exclamation-triangle", self.mmu.state === "ATTENTION");
      if (
        self.mmu.state === "LOADED" ||
        self.mmu.state === "UNLOADING" ||
        self.mmu.state === "LOADING" ||
        self.mmu.state === "PAUSED_USER"
      ) {
        $("#navbar_plugin_prusammu_icon").show();
      } else {
        $("#navbar_plugin_prusammu_icon").hide();
      }

      $("#navbar_plugin_prusammu_icon").css({color: self.mmu.color});
      $("#navbar_plugin_prusammu_text").html(self.mmu.text);
    }

    // ===== Modal =====

    self._modal = undefined;

    self._draw_selection = function(filament) {
      var color = "inherited";
      if (filament.color()) {
        color = filament.color();
      }
      return '<i class="fas fa-pen-fancy" style="color: ' + color + '"></i> ' +
      gettext("Filament " + filament.id() + ": ") + filament.name();
    }

    self._showPrompt = function() {
      var filament = self.settings.settings.plugins.prusammu.filament();
      var opts = {
        title: gettext("Prusa MMU"),
        message: gettext("Select the filament spool:"),
        selections: {
          0: self._draw_selection(filament[0]),
          1: self._draw_selection(filament[1]),
          2: self._draw_selection(filament[2]),
          3: self._draw_selection(filament[3]),
          4: self._draw_selection(filament[4])
        },
        onselect: function(index) {
          if (index > -1) {
            self._select(index);
          }
        },
        onclose: function() {
          self._modal = undefined;
        }
      };

      self._modal = showSelectionDialog(opts)
      setTimeout(self._closePrompt, self.settings.settings.plugins.prusammu.timeout() * 1000);
    };

    self._select = function(index) {
      OctoPrint.plugins.prusammu.select(index);
    };

    self._closePrompt = function() {
      if (self._modal) {
        self._modal.modal("hide");
      }
    };

    // ===== Get Updates from backend =====

    self.onDataUpdaterPluginMessage = function(plugin, data) {
      if (!self.loginState.isUser()) return;
      if (plugin !== "prusammu") {
        return;
      }

      switch (data.action) {
        case "show":
          self._showPrompt();
          break;
        case "close":
          self._closePrompt();
          break;
        case "nav":
          self._update_nav(data.tool, data.state);
          break;
      }
    }
  }

  OCTOPRINT_VIEWMODELS.push([
      PrusaMMU2ViewModel,
      ["settingsViewModel","loginStateViewModel", "printerStateViewModel"],
      ["#navbar_plugin_prusammu"]
  ]);
});