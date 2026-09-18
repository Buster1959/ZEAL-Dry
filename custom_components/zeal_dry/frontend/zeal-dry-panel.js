class ZealDryPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._started = false;
    this._view = "overview";
    this._entries = [];
    this._entryId = null;
    this._configuration = null;
    this._configurations = [];
    this._showAddZone = false;
    this._expandedZones = new Set();
    this._loading = true;
    this._saving = false;
    this._notice = "";
    this._error = "";
    this._timer = null;
    this._statusReceivedAt = null;
    this._lastRefreshAt = null;
    this.shadowRoot.addEventListener("click", (event) => this._onClick(event));
    this.shadowRoot.addEventListener("change", (event) => this._onChange(event));
    this.shadowRoot.addEventListener("toggle", (event) => this._onToggle(event), true);
  }

  set hass(value) {
    this._hass = value;
    if (!this._started && value) {
      this._started = true;
      this._initialLoad();
    }
  }

  set narrow(_value) {}
  set route(_value) {}
  set panel(_value) {}

  connectedCallback() {
    this._render();
    this._startTimer();
  }

  disconnectedCallback() {
    if (this._timer) window.clearInterval(this._timer);
    this._timer = null;
  }

  _startTimer() {
    if (this._timer) return;
    this._timer = window.setInterval(() => {
      if (this._view !== "overview" || document.hidden) return;
      this._render();
      if (!this._lastRefreshAt || Date.now() - this._lastRefreshAt >= 5000) {
        this._load(false);
      }
    }, 1000);
  }

  async _initialLoad() {
    try {
      await this._refreshEntries(true);
    } catch (error) {
      this._loading = false;
      this._error = this._message(error, "ZEAL-Dry could not be loaded.");
      this._render();
    }
  }

  async _refreshEntries(showSpinner = false, preferredEntryId = null) {
    const response = await this._hass.callWS({ type: "zeal_dry/list_entries" });
    this._entries = response.entries || [];
    this._entryId = preferredEntryId && this._entries.some((entry) => entry.entry_id === preferredEntryId)
      ? preferredEntryId
      : this._entries.some((entry) => entry.entry_id === this._entryId)
        ? this._entryId
        : this._entries[0]?.entry_id || null;
    if (!this._entryId) throw new Error("No loaded ZEAL-Dry zone was found.");
    await this._load(showSpinner);
  }

  async _load(showSpinner = false) {
    if (!this._entries.length || !this._hass) return;
    this._lastRefreshAt = Date.now();
    if (showSpinner) this._loading = true;
    try {
      this._configurations = await Promise.all(this._entries.map((entry) => this._hass.callWS({
        type: "zeal_dry/get_configuration", entry_id: entry.entry_id,
      })));
      this._configuration = this._configurations.find((config) => config.entry_id === this._entryId) || this._configurations[0];
      this._statusReceivedAt = Date.now();
      this._error = "";
    } catch (error) {
      this._error = this._message(error, "Live ZEAL-Dry state could not be loaded.");
    }
    this._loading = false;
    this._render();
  }

  _message(error, fallback) {
    return error?.message || error?.body?.message || fallback;
  }

  _escape(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  _number(value, suffix = "") {
    if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
    return `${Number(value).toFixed(1)}${suffix}`;
  }

  _historyUrl(entityIds) {
    const available = [...new Set((entityIds || []).filter(
      (entityId) => entityId && this._hass?.states?.[entityId]
    ))];
    return available.length
      ? `/history?entity_id=${encodeURIComponent(available.join(","))}`
      : "";
  }

  _historyLink(entityIds, label) {
    const url = this._historyUrl(entityIds);
    return url
      ? `<a class="history-link" href="${this._escape(url)}" title="${this._escape(label)}" aria-label="${this._escape(label)}"><ha-icon icon="mdi:chart-timeline-variant"></ha-icon></a>`
      : "";
  }

  _countdown(seconds) {
    if (seconds === null || seconds === undefined) return "";
    const sinceUpdate = this._statusReceivedAt
      ? Math.floor((Date.now() - this._statusReceivedAt) / 1000)
      : 0;
    const safe = Math.max(0, Math.floor(Number(seconds)) - sinceUpdate);
    const minutes = Math.floor(safe / 60);
    const remainder = safe % 60;
    return `${minutes}:${String(remainder).padStart(2, "0")} remaining`;
  }

  _duration(seconds) {
    if (seconds === null || seconds === undefined) return "";
    const sinceUpdate = this._statusReceivedAt
      ? Math.floor((Date.now() - this._statusReceivedAt) / 1000)
      : 0;
    const safe = Math.max(0, Math.floor(Number(seconds)) + sinceUpdate);
    const hours = Math.floor(safe / 3600);
    const minutes = Math.floor((safe % 3600) / 60);
    const remainder = safe % 60;
    return [hours, minutes, remainder]
      .map((part) => String(part).padStart(2, "0"))
      .join(":");
  }

  _header() {
    return `
      <header>
        <div class="brand"><ha-icon icon="mdi:water-percent-alert"></ha-icon><div><strong>ZEAL-Dry</strong><small>Keep it dry, not warm.</small></div></div>
        <span class="zone-name">${this._entries.length} ${this._entries.length === 1 ? "zone" : "zones"}</span>
      </header>
      <nav>
        <button data-view="overview" class="${this._view === "overview" ? "active" : ""}">Overview</button>
        <button data-view="overrides" class="${this._view === "overrides" ? "active" : ""}">Overrides</button>
        ${this._hass?.user?.is_admin ? `<button data-view="setup" class="${this._view === "setup" ? "active" : ""}">Setup</button>` : ""}
      </nav>`;
  }

  _overview() {
    const counts = this._configurations.reduce((summary, config) => {
      const tone = config.status.tone;
      if (tone === "fault") summary.fault += 1;
      else if (tone === "drying") summary.drying += 1;
      else summary.monitoring += 1;
      return summary;
    }, { drying: 0, monitoring: 0, fault: 0 });
    return `
      <section class="system-summary">
        <div><strong>${this._configurations.length}</strong><span>Zones</span></div>
        <div><strong>${counts.drying}</strong><span>Drying</span></div>
        <div><strong>${counts.monitoring}</strong><span>Monitoring</span></div>
        <div class="${counts.fault ? "has-fault" : ""}"><strong>${counts.fault}</strong><span>Faults</span></div>
      </section>
      <div class="zone-grid">${this._configurations.map((config) => this._zoneOverview(config)).join("")}</div>`;
  }

  _zoneOverview(config) {
    const status = config.status;
    const state = config.controller;
    const external = state.external;
    const outlook = external.outlook;
    const countdown = this._countdown(status.remaining_seconds);
    const elapsed = this._duration(status.elapsed_seconds);
    const timer = elapsed || countdown;
    const acus = state.acus.length
      ? state.acus.map((acu) => `
          <div class="acu-row">
            <div><strong>${this._escape(acu.entity_id)}</strong><small>${this._escape(acu.last_result)}</small></div>
            <span class="pill ${acu.available ? "ok" : "bad"}">${acu.available ? this._escape(acu.state) : "Unavailable"}</span>
          </div>`).join("")
      : `<p class="muted">No live ACU is configured.</p>`;
    const sensors = state.sensor_health.map((sensor) => `<div class="acu-row"><div><strong>${this._escape(sensor.entity_id)}</strong><small>${this._escape(sensor.power_source)} power · node ${this._escape(sensor.node_status)}</small></div><span class="pill ${sensor.fresh_for_control ? "ok" : "bad"}">${sensor.report_age_minutes === null ? "No report" : `${sensor.report_age_minutes} min ago`}</span></div>`).join("");
    return `
      <article class="zone-card ${this._escape(status.tone)}">
      <div class="zone-title"><div><h2>${this._escape(config.zone_name)}</h2><span>${this._escape(status.title)}${timer ? ` — ${timer}` : ""}</span></div><span class="risk ${this._escape(state.risk)}">${this._escape(state.risk)}</span></div>
      <section class="status ${this._escape(status.tone)}">
        <ha-icon icon="${status.tone === "fault" ? "mdi:alert-circle" : status.tone === "drying" ? "mdi:fan" : "mdi:shield-water"}"></ha-icon>
        <div><h2>${this._escape(status.title)}${timer ? ` — ${timer}` : ""}</h2><p>${this._escape(status.detail)}</p></div>
      </section>
      <div class="grid metrics compact">
        ${this._metric("Moisture risk", state.risk, "mdi:water-alert")}
        ${this._metric("Moisture demand", state.demand === null ? "Unknown" : state.demand ? "On" : "Off", "mdi:water-pump")}
        ${this._metric("Temperature", this._number(state.temperature_c, " °C"), "mdi:thermometer", [config.setup.temperature_entity])}
        ${this._metric("Humidity", this._number(state.humidity, "%"), "mdi:water-percent", [config.setup.humidity_entity])}
        ${this._metric("Dew point", this._number(state.dew_point_c, " °C"), "mdi:weather-fog", [config.setup.temperature_entity, config.setup.humidity_entity])}
        ${this._metric("Dew-point spread", this._number(state.dew_point_spread_c, " °C"), "mdi:arrow-expand-vertical")}
      </div>
      <details data-zone-details="${this._escape(config.entry_id)}" ${this._expandedZones.has(config.entry_id) ? "open" : ""}><summary>Zone details</summary><div class="grid two details-grid">
        <article><h3>Controller</h3><dl><dt>State</dt><dd>${this._escape(state.state)}</dd><dt>Decision</dt><dd>${this._escape(state.reason)}</dd><dt>Drying response</dt><dd>${this._escape(config.setup.settings.response_profile.replaceAll("_", " "))}</dd><dt>Dry target</dt><dd>${this._number(state.proposed_target_c, " °C")}</dd><dt>Fault</dt><dd>${this._escape(state.fault || "None")}</dd></dl></article>
        <article><h3>Air-conditioning units</h3>${acus}</article>
        <article><h3>Sensor health</h3>${sensors}</article>
        <article><h3>External environment ${this._historyLink([external.entity_id], "Open outdoor weather history")}</h3>${external.entity_id ? `<dl><dt>Source</dt><dd>${this._escape(external.entity_id)}</dd><dt>Temperature</dt><dd>${this._number(external.temperature_c, " °C")}</dd><dt>Humidity</dt><dd>${this._number(external.humidity, "%")}</dd><dt>Dew point</dt><dd>${this._number(external.dew_point_c, " °C")}</dd><dt>Indoor minus outdoor DP</dt><dd>${this._number(external.dew_point_difference_c, " °C")}</dd></dl>${external.error ? `<p class="muted">${this._escape(external.error)}</p>` : ""}` : `<p class="muted">No external weather entity is configured.</p>`}</article>
        <article class="outlook ${this._escape(outlook.level)}"><h3>Outdoor dew-point outlook</h3><strong>${this._escape(outlook.level)}</strong><p>${this._escape(outlook.explanation)}</p><small>Forecast outlook informs preparedness; current indoor readings remain responsible for Dry demand.</small></article>
      </div></details></article>`;
  }

  _metric(label, value, icon, historyEntities = []) {
    return `<article class="metric"><ha-icon icon="${icon}"></ha-icon><div><small>${this._escape(label)}</small><strong>${this._escape(value)}</strong></div>${this._historyLink(historyEntities, `Open ${label} history`)}</article>`;
  }

  _overrides() {
    return `<p class="muted page-intro">Changes apply immediately to the selected zone. Safety timers and equipment validation always remain active.</p>
      <div class="zone-grid">${this._configurations.map((config) => {
        const profile = config.setup.settings.profile;
        return `<article class="zone-card"><div class="zone-title"><h2>${this._escape(config.zone_name)}</h2><span>${this._escape(config.status.title)}</span></div>
        <div class="profile-grid">
          ${this._profile(config.entry_id, "property_protection", "Property protection", "Automatic moisture protection while unattended.", "mdi:shield-home", profile)}
          ${this._profile(config.entry_id, "occupied", "Occupied", "Protection while the space is in normal use.", "mdi:home-account", profile)}
          ${this._profile(config.entry_id, "off", "Off", "Monitor without automatically controlling an ACU.", "mdi:power", profile)}
        </div>
      </article>`; }).join("")}</div>`;
  }

  _profile(entryId, value, label, detail, icon, current) {
    return `<button class="profile ${value === current ? "selected" : ""}" data-entry-id="${this._escape(entryId)}" data-profile="${value}" ${this._saving ? "disabled" : ""}><ha-icon icon="${icon}"></ha-icon><strong>${label}</strong><span>${detail}</span></button>`;
  }

  _setup() {
    const setup = this._configuration.setup;
    const catalog = this._configuration.catalog;
    const settings = setup.settings;
    const zoneButtons = this._configurations.map((config) => `<button class="zone-tab ${config.entry_id === this._entryId ? "active" : ""}" data-edit-zone="${this._escape(config.entry_id)}"><strong>${this._escape(config.zone_name)}</strong><span>${this._escape(config.status.title)}</span></button>`).join("");
    if (this._showAddZone) return this._addZone(catalog, zoneButtons);
    return `
      <div class="setup-toolbar"><div class="zone-tabs">${zoneButtons}</div><button class="primary" data-action="show-add-zone"><ha-icon icon="mdi:plus"></ha-icon> Add zone</button></div>
      <article class="wide setup">
        <div class="setup-heading"><div><h2>${this._escape(this._configuration.zone_name)}</h2><p class="muted">Configure this zone's sensors, moisture policy and exclusively owned ACUs.</p></div>${this._entries.length > 1 ? `<button class="danger" data-action="remove-zone" data-entry-id="${this._escape(this._entryId)}">Remove zone</button>` : ""}</div>
        <div class="form-grid">
          ${this._select("temperature_entity", "Indoor temperature sensor", catalog.temperature_sensors, setup.temperature_entity)}
          ${this._select("humidity_entity", "Indoor humidity sensor", catalog.humidity_sensors, setup.humidity_entity)}
          ${this._optionalSelect("weather_entity", "External weather entity", catalog.weather_entities, setup.weather_entity)}
        </div>
        <label class="field"><span>Climate entities</span><select name="climate_entities" multiple size="${Math.min(6, Math.max(3, catalog.climate_entities.length))}">${catalog.climate_entities.map((item) => `<option value="${this._escape(item.entity_id)}" ${setup.climate_entities.includes(item.entity_id) ? "selected" : ""} ${item.assigned_zone ? "disabled" : ""}>${this._escape(item.name)} · ${this._escape(item.entity_id)} · ${item.assigned_zone ? `assigned to ${this._escape(item.assigned_zone)}` : this._escape(item.state)}</option>`).join("")}</select><small>Use Ctrl/Cmd-click to select more than one ACU. An ACU assigned to another ZEAL-Dry zone is unavailable here.</small></label>
        <h3>Moisture policy</h3>
        <label class="field"><span>Drying response</span><select name="response_profile"><option value="early_protection" ${settings.response_profile === "early_protection" ? "selected" : ""}>Early protection — act from Elevated risk</option><option value="balanced" ${settings.response_profile === "balanced" ? "selected" : ""}>Balanced — act from High risk</option><option value="economy" ${settings.response_profile === "economy" ? "selected" : ""}>Economy — act at Critical risk</option></select><small>Critical RH or absolute dew point always demands protection. This choice controls the normal response to the highest risk indicated by humidity, dew point or dew-point spread.</small></label>
        <div class="risk-guide" role="img" aria-label="Dew-point spread risk scale: Critical at 2 degrees Celsius or less, High from 2 to 4, Elevated from 4 to 6, and Normal above 6."><span class="critical"><strong>Critical</strong>≤2 °C</span><span class="high"><strong>High</strong>2–4 °C</span><span class="elevated"><strong>Elevated</strong>4–6 °C</span><span class="normal"><strong>Normal</strong>&gt;6 °C</span></div>
        <div class="form-grid thirds">
          ${this._input("preferred_rh", "Preferred RH", settings.preferred_rh, "%")}
          ${this._input("maximum_rh", "Maximum RH", settings.maximum_rh, "%")}
          ${this._input("critical_rh", "Critical RH", settings.critical_rh, "%")}
          ${this._input("persistence_minutes", "High RH persistence", settings.persistence_minutes, "min")}
          ${this._input("minimum_run_minutes", "Minimum Dry runtime", settings.minimum_run_minutes, "min")}
          ${this._input("minimum_rest_minutes", "Minimum rest", settings.minimum_rest_minutes, "min")}
          ${this._input("recovery_minutes", "Recovery observation", settings.recovery_minutes, "min")}
          ${this._input("maximum_run_minutes", "Maximum continuous runtime", settings.maximum_run_minutes, "min")}
          ${this._input("safety_margin_c", "Dew-point safety margin", settings.safety_margin_c, "°C", "0.1")}
        </div>
        <h3>Dry temperature</h3>
        <div class="form-grid thirds">
          <label class="field"><span>Strategy</span><select name="strategy"><option value="room_offset" ${settings.strategy === "room_offset" ? "selected" : ""}>Room offset</option><option value="fixed" ${settings.strategy === "fixed" ? "selected" : ""}>Fixed</option></select></label>
          ${this._input("offset_c", "Room offset", settings.offset_c, "°C", "0.1")}
          ${this._input("fixed_target_c", "Fixed target", settings.fixed_target_c, "°C", "0.5")}
          ${this._input("minimum_c", "Minimum target", settings.minimum_c, "°C", "0.5")}
          ${this._input("maximum_c", "Maximum target", settings.maximum_c, "°C", "0.5")}
        </div>
        <label class="checkbox"><input type="checkbox" name="show_in_sidebar" ${setup.show_in_sidebar ? "checked" : ""}> <span><strong>Show ZEAL-Dry in the Home Assistant sidebar</strong><small>If hidden, restore it from Settings → Devices & Services → ZEAL-Dry → Configure.</small></span></label>
        <div class="actions"><button class="primary" data-action="save-setup" ${this._saving ? "disabled" : ""}>${this._saving ? "Saving…" : "Save setup"}</button></div>
      </article>`;
  }

  _addZone(catalog, zoneButtons) {
    return `
      <div class="setup-toolbar"><div class="zone-tabs">${zoneButtons}</div><button data-action="cancel-add-zone">Cancel</button></div>
      <article class="wide setup">
        <h2>Add zone</h2>
        <p class="muted">Create an independently controlled drying zone. Sensors may be shared, but each ACU can belong to only one zone.</p>
        <div class="form-grid">
          <label class="field"><span>Zone name</span><input name="new_zone_name" type="text" placeholder="For example, Bedroom 1"></label>
          ${this._select("new_temperature_entity", "Indoor temperature sensor", catalog.temperature_sensors, "")}
          ${this._select("new_humidity_entity", "Indoor humidity sensor", catalog.humidity_sensors, "")}
          ${this._optionalSelect("new_weather_entity", "External weather entity", catalog.weather_entities, "")}
        </div>
        <label class="field"><span>Air-conditioning units</span><select name="new_climate_entities" multiple size="${Math.min(6, Math.max(3, catalog.climate_entities.length))}">${catalog.climate_entities.map((item) => `<option value="${this._escape(item.entity_id)}" ${item.assigned_zone ? "disabled" : ""}>${this._escape(item.name)} · ${this._escape(item.entity_id)} · ${item.assigned_zone ? `assigned to ${this._escape(item.assigned_zone)}` : this._escape(item.state)}</option>`).join("")}</select><small>Select one or more ACUs. ACUs owned by another zone cannot be selected.</small></label>
        <div class="actions"><button class="primary" data-action="create-zone" ${this._saving ? "disabled" : ""}>${this._saving ? "Creating…" : "Create zone"}</button></div>
      </article>`;
  }

  _select(name, label, items, selected) {
    return `<label class="field"><span>${label}</span><select name="${name}">${items.map((item) => `<option value="${this._escape(item.entity_id)}" ${item.entity_id === selected ? "selected" : ""}>${this._escape(item.name)} · ${this._escape(item.entity_id)}</option>`).join("")}</select></label>`;
  }

  _optionalSelect(name, label, items, selected) {
    return `<label class="field"><span>${label}</span><select name="${name}"><option value="">Not configured</option>${items.map((item) => `<option value="${this._escape(item.entity_id)}" ${item.entity_id === selected ? "selected" : ""}>${this._escape(item.name)} · ${this._escape(item.entity_id)}</option>`).join("")}</select><small>Used for outdoor comparison only; indoor readings control Dry demand.</small></label>`;
  }

  _input(name, label, value, unit, step = "1") {
    return `<label class="field"><span>${label}</span><div class="unit"><input name="${name}" type="number" step="${step}" value="${this._escape(value)}"><b>${unit}</b></div></label>`;
  }

  async _onClick(event) {
    const view = event.target.closest("[data-view]")?.dataset.view;
    if (view) {
      this._view = view;
      this._notice = "";
      this._error = "";
      this._render();
      return;
    }
    const profile = event.target.closest("[data-profile]")?.dataset.profile;
    const profileEntry = event.target.closest("[data-profile]")?.dataset.entryId;
    if (profile) await this._setProfile(profileEntry, profile);
    const editZone = event.target.closest("[data-edit-zone]")?.dataset.editZone;
    if (editZone) {
      this._entryId = editZone;
      this._configuration = this._configurations.find((config) => config.entry_id === editZone);
      this._showAddZone = false;
      this._render();
    }
    if (event.target.closest('[data-action="show-add-zone"]')) { this._showAddZone = true; this._render(); }
    if (event.target.closest('[data-action="cancel-add-zone"]')) { this._showAddZone = false; this._render(); }
    if (event.target.closest('[data-action="create-zone"]')) await this._createZone();
    const remove = event.target.closest('[data-action="remove-zone"]');
    if (remove) await this._removeZone(remove.dataset.entryId);
    if (event.target.closest('[data-action="save-setup"]')) await this._saveSetup();
  }

  async _onChange(event) {
    if (event.target.dataset.action === "entry") {
      this._entryId = event.target.value;
      await this._load(true);
    }
  }

  _onToggle(event) {
    const entryId = event.target?.dataset?.zoneDetails;
    if (!entryId) return;
    if (event.target.open) this._expandedZones.add(entryId);
    else this._expandedZones.delete(entryId);
  }

  async _setProfile(entryId, profile) {
    this._saving = true;
    this._render();
    try {
      await this._hass.callWS({ type: "zeal_dry/set_profile", entry_id: entryId, profile });
      await this._load(false);
      const zone = this._configurations.find((config) => config.entry_id === entryId)?.zone_name || "Zone";
      this._notice = `${zone} operating profile updated.`;
      this._error = "";
    } catch (error) {
      this._error = this._message(error, "The profile could not be changed.");
    }
    this._saving = false;
    this._render();
  }

  async _createZone() {
    const root = this.shadowRoot;
    const value = (name) => root.querySelector(`[name="${name}"]`)?.value || "";
    const climates = [...root.querySelector('[name="new_climate_entities"]').selectedOptions].map((option) => option.value);
    const payload = {
      type: "zeal_dry/create_zone",
      zone_name: value("new_zone_name"),
      temperature_entity: value("new_temperature_entity"),
      humidity_entity: value("new_humidity_entity"),
      weather_entity: value("new_weather_entity"),
      climate_entities: climates,
    };
    this._saving = true;
    this._render();
    try {
      const result = await this._hass.callWS(payload);
      this._showAddZone = false;
      this._notice = "Zone created.";
      this._error = "";
      await new Promise((resolve) => window.setTimeout(resolve, 750));
      await this._refreshEntries(false, result.entry_id);
    } catch (error) {
      this._error = this._message(error, "The zone could not be created.");
    }
    this._saving = false;
    this._render();
  }

  async _removeZone(entryId) {
    const zone = this._configurations.find((config) => config.entry_id === entryId)?.zone_name || "this zone";
    if (!window.confirm(`Remove ${zone}? ZEAL-Dry will stop its owned ACUs before removing the zone.`)) return;
    this._saving = true;
    this._render();
    try {
      await this._hass.callWS({ type: "zeal_dry/remove_zone", entry_id: entryId });
      this._entryId = null;
      this._notice = `${zone} removed.`;
      this._error = "";
      await this._refreshEntries(false);
    } catch (error) {
      this._error = this._message(error, "The zone could not be removed.");
    }
    this._saving = false;
    this._render();
  }

  async _saveSetup() {
    const root = this.shadowRoot;
    const value = (name) => root.querySelector(`[name="${name}"]`)?.value;
    const numeric = ["preferred_rh", "maximum_rh", "critical_rh", "offset_c", "safety_margin_c", "fixed_target_c", "persistence_minutes", "minimum_run_minutes", "minimum_rest_minutes", "recovery_minutes", "maximum_run_minutes", "minimum_c", "maximum_c"];
    const settings = { profile: this._configuration.setup.settings.profile, response_profile: value("response_profile"), strategy: value("strategy") };
    numeric.forEach((name) => { settings[name] = Number(value(name)); });
    const climate = [...root.querySelector('[name="climate_entities"]').selectedOptions].map((option) => option.value);
    const temperatureEntity = value("temperature_entity");
    const humidityEntity = value("humidity_entity");
    const weatherEntity = value("weather_entity");
    const showInSidebar = root.querySelector('[name="show_in_sidebar"]').checked;
    this._saving = true;
    this._render();
    try {
      await this._hass.callWS({
        type: "zeal_dry/save_setup",
        entry_id: this._entryId,
        temperature_entity: temperatureEntity,
        humidity_entity: humidityEntity,
        weather_entity: weatherEntity,
        climate_entities: climate,
        show_in_sidebar: showInSidebar,
        settings,
      });
      this._notice = "Setup saved. ZEAL-Dry is reloading the zone safely.";
      this._error = "";
      await new Promise((resolve) => window.setTimeout(resolve, 1500));
      await this._load(false);
    } catch (error) {
      this._error = this._message(error, "Setup could not be saved.");
    }
    this._saving = false;
    this._render();
  }

  _content() {
    if (this._loading) return `<div class="loading"><ha-circular-progress active></ha-circular-progress><p>Loading ZEAL-Dry…</p></div>`;
    if (!this._configuration) return "";
    if (this._view === "overrides") return this._overrides();
    if (this._view === "setup" && this._hass?.user?.is_admin) return this._setup();
    return this._overview();
  }

  _render() {
    if (!this.shadowRoot) return;
    this.shadowRoot.innerHTML = `<style>${this._styles()}</style>${this._header()}<main>${this._notice ? `<div class="message notice">${this._escape(this._notice)}</div>` : ""}${this._error ? `<div class="message error">${this._escape(this._error)}</div>` : ""}${this._content()}</main>`;
  }

  _styles() {
    return `
      :host{display:block;min-height:100%;background:var(--primary-background-color);color:var(--primary-text-color);font-family:var(--paper-font-body1_-_font-family,system-ui,sans-serif)}
      *{box-sizing:border-box} header{height:76px;padding:12px 28px;display:flex;align-items:center;justify-content:space-between;background:var(--card-background-color);border-bottom:1px solid var(--divider-color)}
      .brand{display:flex;align-items:center;gap:13px}.brand ha-icon{color:#0696a7;width:38px;height:38px}.brand strong{font-size:24px}.brand small,.field small,.checkbox small,.acu-row small{display:block;color:var(--secondary-text-color);margin-top:3px}.zone-name{font-weight:600}.instance select{margin-left:8px}
      nav{display:flex;gap:4px;padding:0 28px;background:var(--card-background-color);border-bottom:1px solid var(--divider-color)}nav button{border:0;background:none;padding:15px 20px;color:var(--secondary-text-color);font-weight:600;cursor:pointer;border-bottom:3px solid transparent}nav button.active{color:#078c9c;border-color:#078c9c}
      main{max-width:1380px;margin:0 auto;padding:26px}.system-summary{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}.system-summary div{display:flex;align-items:baseline;gap:9px;padding:14px 18px;border-radius:12px;background:var(--card-background-color);border:1px solid var(--divider-color)}.system-summary strong{font-size:24px}.system-summary span{color:var(--secondary-text-color)}.system-summary .has-fault{border-color:#c62828;color:#9a2323}.zone-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(480px,1fr));gap:18px}.zone-card{border-top:5px solid #078c9c}.zone-card.fault{border-top-color:#c62828}.zone-card.drying{border-top-color:#1976d2}.zone-title,.setup-heading,.setup-toolbar{display:flex;justify-content:space-between;align-items:center;gap:16px}.zone-title{margin-bottom:16px}.zone-title h2{margin:0}.zone-title>div>span,.zone-title>span:not(.risk){color:var(--secondary-text-color)}.risk{padding:6px 10px;border-radius:999px;background:var(--secondary-background-color);text-transform:capitalize;font-weight:700}.status{display:flex;gap:14px;align-items:center;padding:14px 16px;border-radius:12px;background:#eaf8fa;border-left:5px solid #078c9c;margin-bottom:16px}.status ha-icon{width:30px;height:30px}.status h2{font-size:17px;margin:0 0 3px}.status p{margin:0}.status.fault{background:#fdecec;border-color:#c62828;color:#8f1d1d}.status.waiting{background:#fff7df;border-color:#e39b00}.status.drying{background:#e6f4ff;border-color:#1976d2}.status.inhibited{background:#f1f1f1;border-color:#777}
      .grid{display:grid;gap:16px}.metrics{grid-template-columns:repeat(3,1fr);margin-bottom:16px}.two{grid-template-columns:1fr 1fr}article,.metric,.wide{background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:14px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,.05)}article h2,article h3{margin-top:0}.metric{display:flex;align-items:center;gap:14px}.metric ha-icon{color:#078c9c}.metric strong{display:block;font-size:22px;margin-top:4px}.metric small{color:var(--secondary-text-color)}
      .metric .history-link{margin-left:auto}.history-link{display:inline-flex;align-items:center;justify-content:center;vertical-align:middle;width:34px;height:34px;border-radius:50%;color:var(--primary-color);text-decoration:none}.history-link:hover,.history-link:focus-visible{background:var(--secondary-background-color);outline:2px solid var(--primary-color);outline-offset:1px}.history-link ha-icon{--mdc-icon-size:22px}.outlook{border-left:6px solid #2e7d32}.outlook>strong{text-transform:capitalize;font-size:22px}.outlook.medium{border-left-color:#ef9b00}.outlook.critical{border-left-color:#c62828}.outlook.unavailable{border-left-color:#777}.outlook small{color:var(--secondary-text-color)}
      dl{display:grid;grid-template-columns:130px 1fr;gap:10px;margin:0}dt{color:var(--secondary-text-color)}dd{margin:0;font-weight:600}.acu-row{display:flex;justify-content:space-between;gap:10px;padding:12px 0;border-bottom:1px solid var(--divider-color)}.acu-row:last-child{border-bottom:0}.pill{padding:5px 10px;border-radius:999px;background:#e7f6eb;color:#176a2f;text-transform:capitalize}.pill.bad{background:#fdecec;color:#9a2323}.muted{color:var(--secondary-text-color)}
      .profile-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.profile{display:flex;flex-direction:column;text-align:left;gap:9px;padding:15px;border:2px solid var(--divider-color);border-radius:12px;background:var(--card-background-color);color:var(--primary-text-color);cursor:pointer}.profile ha-icon{color:#078c9c}.profile.selected{border-color:#078c9c;background:#eaf8fa}.profile span{color:var(--secondary-text-color);line-height:1.4}.page-intro{margin-top:0}
      .setup-toolbar{margin-bottom:18px}.zone-tabs{display:flex;flex-wrap:wrap;gap:8px}.zone-tab{display:flex;flex-direction:column;align-items:flex-start;padding:10px 14px;border:1px solid var(--divider-color);border-radius:9px;background:var(--card-background-color);color:var(--primary-text-color);cursor:pointer}.zone-tab span{font-size:12px;color:var(--secondary-text-color)}.zone-tab.active{border:2px solid #078c9c}.setup-heading h2,.setup-heading p{margin-top:0}.setup h3{margin-top:28px}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.form-grid.thirds{grid-template-columns:repeat(3,1fr)}.field{display:block;margin:13px 0}.field>span{display:block;font-weight:600;margin-bottom:7px}.field select,.field input,.instance select{width:100%;min-height:44px;padding:9px 11px;border:1px solid var(--divider-color);border-radius:8px;background:var(--card-background-color);color:var(--primary-text-color)}.field select[multiple]{min-height:110px}.unit{display:flex;align-items:center}.unit input{border-radius:8px 0 0 8px}.unit b{height:44px;padding:12px;background:var(--secondary-background-color);border:1px solid var(--divider-color);border-left:0;border-radius:0 8px 8px 0}.checkbox{display:flex;gap:10px;margin-top:28px;align-items:flex-start}.checkbox input{width:20px;height:20px}.actions{text-align:right;margin-top:24px}.primary,.danger,.setup-toolbar>button{border:0;border-radius:9px;padding:12px 20px;font-weight:700;cursor:pointer}.primary{background:#078c9c;color:white}.primary ha-icon{vertical-align:middle}.danger{background:#fdecec;color:#9a2323}.primary:disabled{opacity:.55}details{margin-top:14px}summary{cursor:pointer;font-weight:700;padding:8px 0}.details-grid{margin-top:12px}.compact{grid-template-columns:repeat(3,1fr)}
      .risk-guide{display:grid;grid-template-columns:repeat(4,1fr);margin:12px 0 20px;border-radius:9px;overflow:hidden}.risk-guide span{display:flex;flex-direction:column;gap:3px;padding:12px;text-align:center}.risk-guide .critical{background:#f8d7da;color:#842029}.risk-guide .high{background:#ffe5cc;color:#7a3e00}.risk-guide .elevated{background:#fff3cd;color:#664d03}.risk-guide .normal{background:#d1e7dd;color:#0f5132}
      .message{padding:13px 16px;border-radius:9px;margin-bottom:16px}.notice{background:#e7f6eb;color:#176a2f}.error{background:#fdecec;color:#9a2323}.loading{text-align:center;padding:80px 20px}
      @media(max-width:760px){header{padding:10px 16px}.brand small{display:none}nav{padding:0 10px}main{padding:16px}.system-summary{grid-template-columns:1fr 1fr}.zone-grid{grid-template-columns:1fr}.metrics{grid-template-columns:1fr 1fr}.two,.profile-grid,.form-grid,.form-grid.thirds{grid-template-columns:1fr}.risk-guide{grid-template-columns:1fr 1fr}.setup-toolbar,.setup-heading{align-items:stretch;flex-direction:column}.status h2{font-size:18px}}
      @media(max-width:430px){.metrics{grid-template-columns:1fr}.brand strong{font-size:20px}nav button{padding:13px 12px}}
    `;
  }
}

if (!customElements.get("zeal-dry-panel")) {
  customElements.define("zeal-dry-panel", ZealDryPanel);
}
