(function () {
  "use strict";

  function byId(id) {
    return document.getElementById(id);
  }

  function toInt(value) {
    var parsed = parseInt(value, 10);
    return Number.isNaN(parsed) ? value : parsed;
  }

  function containerFor(field) {
    if (!field) {
      return null;
    }
    return (
      field.closest("tr") ||
      field.closest(".form-group") ||
      field.closest(".control-group") ||
      field.parentElement
    );
  }

  function setFieldVisibility(field, visible) {
    if (!field) {
      return;
    }

    var container = containerFor(field);
    if (container) {
      container.style.display = visible ? "" : "none";
    }
  }

  function convertPythonReplacementToJs(replacement) {
    return replacement.replace(/\\([1-9][0-9]*)/g, "$$$1");
  }

  function injectPreviewRow(anchorField) {
    var existing = byId("identifier-map-preview-root");
    if (existing) {
      return existing;
    }

    var anchorContainer = containerFor(anchorField);
    if (!anchorContainer) {
      return null;
    }

    if (anchorContainer.tagName === "TR") {
      var tr = document.createElement("tr");
      tr.id = "identifier-map-preview-root";
      tr.innerHTML =
        '<td><label for="identifier_preview_input">Vista previa Regex</label></td>' +
        '<td>' +
        '<div class="well well-sm" style="margin-bottom: 0;">' +
        '<input id="identifier_preview_input" class="form-control" type="text" placeholder="Identificador de ejemplo (ej. oai:sedici.unlp.edu.ar:10915/108063)">' +
        '<span class="help-block" style="margin-top: 8px;">Prueba el Patron/Reemplazo regex actual. Se soportan referencias \\1, \\2 en la vista previa.</span>' +
        '<div id="identifier_preview_result" class="alert alert-info" style="margin-top: 8px; margin-bottom: 0;">Esperando entrada.</div>' +
        "</div>" +
        "</td>";
      anchorContainer.insertAdjacentElement("afterend", tr);
      return tr;
    }

    var wrapper = document.createElement("div");
    wrapper.id = "identifier-map-preview-root";
    wrapper.className = "form-group";
    wrapper.innerHTML =
      '<label for="identifier_preview_input" class="control-label">Vista previa Regex</label>' +
      '<div class="well well-sm">' +
      '<input id="identifier_preview_input" class="form-control" type="text" placeholder="Identificador de ejemplo (ej. oai:sedici.unlp.edu.ar:10915/108063)">' +
      '<span class="help-block" style="margin-top: 8px;">Prueba el Patron/Reemplazo regex actual. Se soportan referencias \\1, \\2 en la vista previa.</span>' +
      '<div id="identifier_preview_result" class="alert alert-info" style="margin-top: 8px; margin-bottom: 0;">Esperando entrada.</div>' +
      "</div>";
    anchorContainer.insertAdjacentElement("afterend", wrapper);
    return wrapper;
  }

  function setPreviewMessage(element, message, type) {
    if (!element) {
      return;
    }

    element.classList.remove("alert-info", "alert-danger", "alert-success", "alert-warning");
    element.classList.add(type || "alert-info");
    element.textContent = message;
  }

  function initSourceMappingUi() {
    var modeField = byId("identifier_map_type");
    var regexField = byId("identifier_map_regex");
    var replaceField = byId("identifier_map_replace");
    var filenameField = byId("identifier_map_filename");

    if (!modeField || !regexField || !replaceField || !filenameField) {
      return;
    }

    var previewRoot = injectPreviewRow(replaceField);
    var previewInput = byId("identifier_preview_input");
    var previewResult = byId("identifier_preview_result");

    function updatePreview() {
      var mode = toInt(modeField.value);
      if (!previewRoot) {
        return;
      }

      previewRoot.style.display = mode === 1 ? "" : "none";
      if (mode !== 1) {
        return;
      }

      var sample = previewInput ? previewInput.value : "";
      var regexPattern = (regexField.value || "").trim();
      var replacement = replaceField.value || "";

      if (!sample) {
        setPreviewMessage(previewResult, "Ingresa un identificador de ejemplo para previsualizar.", "alert-info");
        return;
      }

      if (!regexPattern) {
        setPreviewMessage(previewResult, "El Patron Regex esta vacio.", "alert-warning");
        return;
      }

      var regex;
      try {
        regex = new RegExp(regexPattern);
      } catch (error) {
        setPreviewMessage(previewResult, "Patron regex invalido: " + error.message, "alert-danger");
        return;
      }

      try {
        var jsReplacement = convertPythonReplacementToJs(replacement);
        var transformed = sample.replace(regex, jsReplacement);
        if (transformed === sample) {
          setPreviewMessage(previewResult, "Sin cambios: " + transformed, "alert-warning");
          return;
        }
        setPreviewMessage(previewResult, "Resultado: " + transformed, "alert-success");
      } catch (error) {
        setPreviewMessage(previewResult, "Expresion de reemplazo invalida: " + error.message, "alert-danger");
      }
    }

    function applyModeVisibility() {
      var mode = toInt(modeField.value);
      setFieldVisibility(regexField, mode === 1);
      setFieldVisibility(replaceField, mode === 1);
      setFieldVisibility(filenameField, mode === 2);
      updatePreview();
    }

    modeField.addEventListener("change", applyModeVisibility);
    regexField.addEventListener("input", updatePreview);
    replaceField.addEventListener("input", updatePreview);
    if (previewInput) {
      previewInput.addEventListener("input", updatePreview);
    }

    applyModeVisibility();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initSourceMappingUi);
  } else {
    initSourceMappingUi();
  }
})();
