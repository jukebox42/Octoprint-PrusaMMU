/*!
 *
 * ColorPick jQuery plugin
 * https://github.com/philzet/ColorPick.js
 *
 * Copyright (c) 2017-2019 Phil Zet (a.k.a. Phil Zakharchenko)
 * Licensed under the MIT License
 *
 * NOTE: This is not the initial version, has been heavily modified to support octoprint and cleaned up.
 */
(function( $ ) {
  const PLUGIN_ID = "colorPick";
  const PLUGIN_SELECTOR = `#${PLUGIN_ID}`;
  const PICKER_CLASS = "__picker__";
  $.fn.colorPick = function(config) {
    return this.each(function() {
      new $.colorPick(this, config || {});
    });
  };

  $.colorPick = function (element, options) {
    options = options || {};
    this.settings = $.extend({}, $.fn.colorPick.defaults, options);
    this.settings.palette = this.settings.palette.map(x => x.toUpperCase());

    this.color   = this.settings.initialColor.toUpperCase();
    this.element = $(element);

    return this.element.hasClass(PICKER_CLASS) ? this : this.init();
  };

  $.fn.colorPick.defaults = {
    initialColor: "#808080",
    paletteLabel: "Default palette:",
    customLabel: "Custom color:",
    allowRecent: true,
    recentMax: 5,
    recentLabel: "Recent:",
    allowCustomColor: false,
    drawUp: false, 
    palette: [
      "#1abc9c", "#16a085", "#2ecc71", "#27ae60", "#3498db",
      "#2980b9", "#9b59b6", "#8e44ad", "#34495e", "#2c3e50",
      "#f1c40f", "#f39c12", "#e67e22", "#d35400", "#e74c3c",
      "#c0392b", "#ecf0f1", "#bdc3c7", "#95a5a6", "#7f8c8d"],
    onColorSelected: function() {
      this.element.css({ backgroundColor: this.color, color: this.color });
    }
  };

  $.colorPick.prototype = {
    init: function() {
      const self = this;
      $.proxy(this.settings.onColorSelected, this)();

      this.element
        .addClass(PICKER_CLASS)
        .click(function(event) {
          event.preventDefault();
          self.show();

          $(`${PLUGIN_SELECTOR} .customColorHash`).val(self.color);

          $(`${PLUGIN_SELECTOR} .colorPickButton`).click(function(event) {
            self.color = $(event.target).attr("data-hex");
            self.hide();
            $.proxy(self.settings.onColorSelected, self)();
            return false;
          });
          $(`${PLUGIN_SELECTOR} .customColorHash`).on("blur", function (_) {
            const hash = $(this).val();
            self.color = hash;
            self.appendToStorage(hash);
            $.proxy(self.settings.onColorSelected, self)();
          });

          return false;
        });

      $(document).on("mouseup", function(event)  {
        const container = $(PLUGIN_SELECTOR);
        // if the target of the click isn't the container nor a descendant of the container
        if (!container.is(event.target) && container.has(event.target).length === 0) {
          self.hide();
        }
      });

      return this;
    },

    appendToStorage: function(color) {
      color = color.toUpperCase();
      if (
        this.settings.allowRecent === false ||
        this.settings.palette.find(c => c === color)
      ) {
        return;
      }
      let storedColors = JSON.parse(localStorage.getItem("colorPickRecentItems"));
      if (storedColors == null) {
        storedColors = [];
      }
      if ($.inArray(color, storedColors) == -1) {
        storedColors.unshift(color);
        storedColors = storedColors.slice(0, this.settings.recentMax)
        localStorage.setItem("colorPickRecentItems", JSON.stringify(storedColors));
      }
    },

    show: function() {
      const drawColorButton = (item) => `<div class="colorPickButton" data-hex="${item}" style="background:${item}"></div>`;
      const drawLabel = (label, padd) => `<span style="${padd ? "margin-top:5px" : ""}">${label}</span>`;
      $(PLUGIN_SELECTOR).remove();
      // Draw color pallete
      const directionStyle = this.settings.drawUp ? "bottom:100%;top:unset;" : "top:100%;bottom:unset;";
      const markupDropdown = `
        <div id="${PLUGIN_ID}" class="dropdown-menu" style="display:none;${directionStyle}">
          ${drawLabel(this.settings.paletteLabel)}
          <div class="colorWrap"></div>
        </div>`;
      $(this.element.parent()).append(markupDropdown);
      this.settings.palette.forEach(item => {
        $(`${PLUGIN_SELECTOR} .colorWrap`).append(drawColorButton(item));
      });
      // Draw custom color input
      if (this.settings.allowCustomColor === true) {
        const markupCustomColor = `
          ${drawLabel(this.settings.customLabel, true)}
          <input type="color" class="customColorHash" />`;
        $(PLUGIN_SELECTOR).append(markupCustomColor);
      }
      // Draw recent colors
      if (this.settings.allowRecent === true) {
        $(PLUGIN_SELECTOR).append(drawLabel(this.settings.recentLabel, true));
        const recentItems = JSON.parse(localStorage.getItem("colorPickRecentItems"));
        if ( recentItems == null || recentItems == []) {
          $(PLUGIN_SELECTOR).append(`<div class="colorPickButton colorPickDummy"></div>`);
        } else {
          recentItems.forEach((item, index) => {
            if (index > this.settings.recentMax - 1) {
              return false;
            }
            $(PLUGIN_SELECTOR).append(drawColorButton(item));
          });
        }
      }
      $(PLUGIN_SELECTOR).fadeIn(200);
    },

    hide: function() {
      $(PLUGIN_SELECTOR).fadeOut(200, function() {
        $(PLUGIN_SELECTOR).remove();
        return this;
      });
    },
  };
}( jQuery ));
