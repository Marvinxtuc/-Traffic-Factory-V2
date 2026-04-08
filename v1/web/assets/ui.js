(function () {
  function getDictionary() {
    return window.TF_I18N_ZH || {};
  }

  function getByPath(path) {
    if (!path) return undefined;
    const parts = String(path).split(".");
    let cursor = getDictionary();
    for (const part of parts) {
      if (cursor == null || typeof cursor !== "object" || !(part in cursor)) {
        return undefined;
      }
      cursor = cursor[part];
    }
    return cursor;
  }

  function formatTemplate(template, params) {
    const safeTemplate = String(template ?? "");
    const safeParams = params && typeof params === "object" ? params : {};
    return safeTemplate.replace(/\{\s*([a-zA-Z0-9_]+)\s*\}/g, (_m, key) => {
      if (key in safeParams) {
        return String(safeParams[key]);
      }
      return "";
    });
  }

  function t(path, params) {
    const raw = getByPath(path);
    if (typeof raw === "string") {
      return formatTemplate(raw, params);
    }
    if (raw === undefined || raw === null) {
      return "";
    }
    return raw;
  }

  function applyI18n(root) {
    const host = root || document;

    host.querySelectorAll("[data-i18n]").forEach((node) => {
      const key = node.getAttribute("data-i18n");
      node.textContent = t(key);
    });

    host.querySelectorAll("[data-i18n-placeholder]").forEach((node) => {
      const key = node.getAttribute("data-i18n-placeholder");
      node.setAttribute("placeholder", t(key));
    });

    host.querySelectorAll("[data-i18n-value]").forEach((node) => {
      const key = node.getAttribute("data-i18n-value");
      node.value = t(key);
    });

    host.querySelectorAll("[data-i18n-title]").forEach((node) => {
      const key = node.getAttribute("data-i18n-title");
      node.setAttribute("title", t(key));
    });
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function prettyJSON(value) {
    if (value === null || value === undefined) {
      return "{}";
    }
    try {
      return JSON.stringify(value, null, 2);
    } catch (_error) {
      return String(value);
    }
  }

  function normalizeErrorMessage(error) {
    const unknown = t("ERROR.UNKNOWN");
    if (!error) return unknown;

    const rawMessage = typeof error === "string"
      ? error
      : error.message
        ? String(error.message)
        : String(error);
    const normalized = rawMessage.trim();
    const lowered = normalized.toLowerCase();

    if (lowered === "topic not found") return t("ERROR.TOPIC_NOT_FOUND");
    if (lowered === "signal not found") return t("ERROR.SIGNAL_NOT_FOUND");
    if (lowered.includes("not found")) return t("ERROR.NOT_FOUND");
    if (lowered.includes("failed to fetch")) return t("ERROR.NETWORK_FAILED");

    if (error && typeof error === "object" && typeof error.status === "number") {
      return t("ERROR.STATUS_CODE_TEMPLATE", { code: error.status });
    }

    if (lowered === "unknown error") return unknown;
    if (/[A-Za-z]{2,}/.test(normalized) && !/[\u4e00-\u9fff]/.test(normalized)) {
      return t("ERROR.REQUEST_FAILED_RETRY");
    }

    return normalized || unknown;
  }

  async function requestJSON(url, options) {
    const requestOptions = {
      method: "GET",
      ...options,
    };

    if (!requestOptions.headers) {
      requestOptions.headers = {};
    }

    if (requestOptions.body && typeof requestOptions.body !== "string") {
      requestOptions.body = JSON.stringify(requestOptions.body);
      requestOptions.headers["Content-Type"] = "application/json";
    }

    const response = await fetch(url, requestOptions);
    const raw = await response.text();
    let payload = {};

    if (raw) {
      try {
        payload = JSON.parse(raw);
      } catch (_error) {
        payload = { raw };
      }
    }

    if (!response.ok) {
      const detail = payload.detail || payload.error || response.statusText || "";
      const error = new Error(detail || t("ERROR.REQUEST_FAILED_RETRY"));
      error.status = response.status;
      error.payload = payload;
      throw error;
    }

    return payload;
  }

  function statusBadgeHtml(status, domain) {
    const safeStatus = String(status || "unknown");
    const signalMap = t("STATUS.SIGNAL") || {};
    const topicMap = t("STATUS.TOPIC") || {};
    const jobMap = t("STATUS.JOB") || {};
    const mapping = domain === "topic"
      ? topicMap
      : domain === "job"
        ? jobMap
        : signalMap;
    const label = mapping[safeStatus] || t("STATE.UNKNOWN_STATUS");
    return `<span class="tf-status-badge is-${escapeHtml(safeStatus)}" data-status="${escapeHtml(safeStatus)}">${escapeHtml(label)}</span>`;
  }

  function tagHtml(value) {
    if (!value) return "";
    return `<span class="tf-tag">${escapeHtml(value)}</span>`;
  }

  function setState(host, type, title, description, opts) {
    if (!host) return;
    const config = opts || {};
    const actionHtml = config.actionLabel
      ? `<div class="tf-state-actions"><button class="tf-button is-soft" type="button" data-role="state-action">${escapeHtml(config.actionLabel)}</button></div>`
      : "";

    host.innerHTML = `
      <div class="tf-state tf-state-${escapeHtml(type)}">
        <p class="tf-state-title">${escapeHtml(title)}</p>
        <p class="tf-state-desc">${escapeHtml(description || "")}</p>
        ${actionHtml}
      </div>
    `;

    const actionButton = host.querySelector('[data-role="state-action"]');
    if (actionButton && typeof config.onAction === "function") {
      actionButton.addEventListener("click", config.onAction);
    }
  }

  function clearState(host) {
    if (!host) return;
    host.innerHTML = "";
  }

  function toggleHidden(element, hidden) {
    if (!element) return;
    element.classList.toggle("is-hidden", hidden);
  }

  function openDrawer(drawer, backdrop) {
    if (drawer) drawer.classList.add("is-open");
    if (backdrop) backdrop.classList.add("is-open");
  }

  function closeDrawer(drawer, backdrop) {
    if (drawer) drawer.classList.remove("is-open");
    if (backdrop) backdrop.classList.remove("is-open");
  }

  function bindDrawer(drawer, backdrop) {
    if (!drawer) return;

    drawer.querySelectorAll("[data-drawer-close]").forEach((button) => {
      button.addEventListener("click", () => closeDrawer(drawer, backdrop));
    });

    if (backdrop) {
      backdrop.addEventListener("click", () => closeDrawer(drawer, backdrop));
    }
  }

  window.TFUI = {
    applyI18n,
    clearState,
    closeDrawer,
    escapeHtml,
    formatTemplate,
    normalizeErrorMessage,
    openDrawer,
    prettyJSON,
    requestJSON,
    setState,
    statusBadgeHtml,
    t,
    tagHtml,
    toggleHidden,
    bindDrawer,
  };
})();
