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
    this._loading = true;
    this._saving = false;
    this._notice = "";
    this._error = "";
    this._timer = null;
    this.shadowRoot.addEventListener("click", (event) => this._onClick(event));
    this.shadowRoot.addEventListener("change", (event) => this._onChange(event));
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
      if (this._view === "overview" && !document.hidden) this._load(false);
    }, 5000);
  }

  async _initialLoad() {
    try {
      const response = await this._hass.callWS({ type: "zeal_dry/list_entries" });
      this._entries = response.entries || [];
      this._entryId = this._entries[0]?.entry_id || null;
      if (!this._entryId) throw new Error("No loaded ZEAL-Dry zone was found.");
      await this._load(true);
    } catch (error) {
      this._loading = false;
      this._error = this._message(error, "ZEAL-Dry could not be loaded.");
      this._render();
    }
  }

  async _load(showSpinner = false) {
    if (!this._entryId || !this._hass) return;
    if (showSpinner) this._loading = true;
    try {
      this._configuration = await this._hass.callWS({
        type: "zeal_dry/get_configuration",
        entry_id: this._entryId,
      });
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

  _countdown(seconds) {
    if (seconds === null || seconds === undefined) return "";
    const safe = Math.max(0, Number(seconds));
    const minutes = Math.floor(safe / 60);
    const remainder = safe % 60;
    return `${minutes}:${String(remainder).padStart(2, "0")} remaining`;
  }

  _header() {
    const options = this._entries
      .map((entry) => `<option value="${this._escape(entry.entry_id)}" ${entry.entry_id === this._entryId ? "selected" : ""}>${this._escape(entry.title)}</option>`)
      .join("");
    return `
      <header>
        <div class="brand"><ha-icon icon="mdi:water-percent-alert"></ha-icon><div><strong>ZEAL-Dry</strong><small>Keep it dry, not warm.</small></div></div>
        ${this._entries.length > 1 ? `<label class="instance">Zone<select data-action="entry">${options}</select></label>` : `<span class="zone-name">${this._escape(this._configuration?.zone_name || "")}</span>`}
      </header>
      <nav>
        <button data-view="overview" class="${this._view === "overview" ? "active" : ""}">Overview</button>
        <button data-view="overrides" class="${this._view === "overrides" ? "active" : ""}">Overrides</button>
        ${this._hass?.user?.is_admin ? `<button data-view="setup" class="${this._view === "setup" ? "active" : ""}">Setup</button>` : ""}
      </nav>`;
  }

  _overview() {
    const config = this._configuration;
    const status = config.status;
    const state = config.controller;
    const countdown = this._countdown(status.remaining_seconds);
    const acus = state.acus.length
      ? state.acus.map((acu) => `
          <div class="acu-row">
            <div><strong>${this._escape(acu.entity_id)}</strong><small>${this._escape(acu.last_result)}</small></div>
            <span class="pill ${acu.available ? "ok" : "bad"}">${acu.available ? this._escape(acu.state) : "Unavailable"}</span>
          </div>`).join("")
      : `<p class="muted">No live ACU is configured.</p>`;
    return `
      <section class="status ${this._escape(status.tone)}">
        <ha-icon icon="${status.tone === "fault" ? "mdi:alert-circle" : status.tone === "drying" ? "mdi:fan" : "mdi:shield-water"}"></ha-icon>
        <div><h2>${this._escape(status.title)}${countdown ? ` — ${countdown}` : ""}</h2><p>${this._escape(status.detail)}</p></div>
      </section>
      <div class="grid metrics">
        ${this._metric("Moisture risk", state.risk, "mdi:water-alert")}
        ${this._metric("Moisture demand", state.demand === null ? "Unknown" : state.demand ? "On" : "Off", "mdi:water-pump")}
        ${this._metric("Temperature", this._number(state.temperature_c, " °C"), "mdi:thermometer")}
        ${this._metric("Humidity", this._number(state.humidity, "%"), "mdi:water-percent")}
        ${this._metric("Dew point", this._number(state.dew_point_c, " °C"), "mdi:weather-fog")}
        ${this._metric("Dew-point spread", this._number(state.dew_point_spread_c, " °C"), "mdi:arrow-expand-vertical")}
      </div>
      <div class="grid two">
        <article><h3>Controller</h3><dl><dt>State</dt><dd>${this._escape(state.state)}</dd><dt>Decision</dt><dd>${this._escape(state.reason)}</dd><dt>Dry target</dt><dd>${this._number(state.proposed_target_c, " °C")}</dd><dt>Fault</dt><dd>${this._escape(state.fault || "None")}</dd></dl></article>
        <article><h3>Air-conditioning units</h3>${acus}</article>
      </div>`;
  }

  _metric(label, value, icon) {
    return `<article class="metric"><ha-icon icon="${icon}"></ha-icon><div><small>${this._escape(label)}</small><strong>${this._escape(value)}</strong></div></article>`;
  }

  _overrides() {
    const profile = this._configuration.setup.settings.profile;
    return `
      <article class="wide">
        <h2>Operating profile</h2>
        <p class="muted">Changes apply immediately. Safety timers and equipment validation always remain active.</p>
        <div class="profile-grid">
          ${this._profile("property_protection", "Property protection", "Automatic moisture protection while the property is unattended.", "mdi:shield-home", profile)}
          ${this._profile("occupied", "Occupied", "Moisture protection while the space is in normal use.", "mdi:home-account", profile)}
          ${this._profile("off", "Off", "Monitor moisture without automatically controlling an ACU.", "mdi:power", profile)}
        </div>
      </article>`;
  }

  _profile(value, label, detail, icon, current) {
    return `<button class="profile ${value === current ? "selected" : ""}" data-profile="${value}" ${this._saving ? "disabled" : ""}><ha-icon icon="${icon}"></ha-icon><strong>${label}</strong><span>${detail}</span></button>`;
  }

  _setup() {
    const setup = this._configuration.setup;
    const catalog = this._configuration.catalog;
    const settings = setup.settings;
    return `
      <article class="wide setup">
        <h2>Zone setup</h2>
        <p class="muted">Select the indoor readings and every Dry-capable ACU controlled by this moisture-protection zone.</p>
        <div class="form-grid">
          ${this._select("temperature_entity", "Indoor temperature sensor", catalog.temperature_sensors, setup.temperature_entity)}
          ${this._select("humidity_entity", "Indoor humidity sensor", catalog.humidity_sensors, setup.humidity_entity)}
        </div>
        <label class="field"><span>Climate entities</span><select name="climate_entities" multiple size="${Math.min(6, Math.max(3, catalog.climate_entities.length))}">${catalog.climate_entities.map((item) => `<option value="${this._escape(item.entity_id)}" ${setup.climate_entities.includes(item.entity_id) ? "selected" : ""}>${this._escape(item.name)} · ${this._escape(item.entity_id)} · ${this._escape(item.state)}</option>`).join("")}</select><small>Use Ctrl/Cmd-click to select more than one ACU.</small></label>
        <h3>Moisture policy</h3>
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

  _select(name, label, items, selected) {
    return `<label class="field"><span>${label}</span><select name="${name}">${items.map((item) => `<option value="${this._escape(item.entity_id)}" ${item.entity_id === selected ? "selected" : ""}>${this._escape(item.name)} · ${this._escape(item.entity_id)}</option>`).join("")}</select></label>`;
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
    if (profile) await this._setProfile(profile);
    if (event.target.closest('[data-action="save-setup"]')) await this._saveSetup();
  }

  async _onChange(event) {
    if (event.target.dataset.action === "entry") {
      this._entryId = event.target.value;
      await this._load(true);
    }
  }

  async _setProfile(profile) {
    this._saving = true;
    this._render();
    try {
      this._configuration = await this._hass.callWS({ type: "zeal_dry/set_profile", entry_id: this._entryId, profile });
      this._notice = "Operating profile updated.";
      this._error = "";
    } catch (error) {
      this._error = this._message(error, "The profile could not be changed.");
    }
    this._saving = false;
    this._render();
  }

  async _saveSetup() {
    const root = this.shadowRoot;
    const value = (name) => root.querySelector(`[name="${name}"]`)?.value;
    const numeric = ["preferred_rh", "maximum_rh", "critical_rh", "offset_c", "safety_margin_c", "fixed_target_c", "persistence_minutes", "minimum_run_minutes", "minimum_rest_minutes", "recovery_minutes", "maximum_run_minutes", "minimum_c", "maximum_c"];
    const settings = { profile: this._configuration.setup.settings.profile, strategy: value("strategy") };
    numeric.forEach((name) => { settings[name] = Number(value(name)); });
    const climate = [...root.querySelector('[name="climate_entities"]').selectedOptions].map((option) => option.value);
    const temperatureEntity = value("temperature_entity");
    const humidityEntity = value("humidity_entity");
    const showInSidebar = root.querySelector('[name="show_in_sidebar"]').checked;
    this._saving = true;
    this._render();
    try {
      await this._hass.callWS({
        type: "zeal_dry/save_setup",
        entry_id: this._entryId,
        temperature_entity: temperatureEntity,
        humidity_entity: humidityEntity,
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
      main{max-width:1180px;margin:0 auto;padding:26px}.status{display:flex;gap:18px;align-items:center;padding:22px 24px;border-radius:16px;background:#eaf8fa;border-left:6px solid #078c9c;margin-bottom:20px}.status ha-icon{width:38px;height:38px}.status h2{margin:0 0 5px}.status p{margin:0}.status.fault{background:#fdecec;border-color:#c62828;color:#8f1d1d}.status.waiting{background:#fff7df;border-color:#e39b00}.status.drying{background:#e6f4ff;border-color:#1976d2}.status.inhibited{background:#f1f1f1;border-color:#777}
      .grid{display:grid;gap:16px}.metrics{grid-template-columns:repeat(3,1fr);margin-bottom:16px}.two{grid-template-columns:1fr 1fr}article,.metric,.wide{background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:14px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,.05)}article h2,article h3{margin-top:0}.metric{display:flex;align-items:center;gap:14px}.metric ha-icon{color:#078c9c}.metric strong{display:block;font-size:22px;margin-top:4px}.metric small{color:var(--secondary-text-color)}
      dl{display:grid;grid-template-columns:130px 1fr;gap:10px;margin:0}dt{color:var(--secondary-text-color)}dd{margin:0;font-weight:600}.acu-row{display:flex;justify-content:space-between;gap:10px;padding:12px 0;border-bottom:1px solid var(--divider-color)}.acu-row:last-child{border-bottom:0}.pill{padding:5px 10px;border-radius:999px;background:#e7f6eb;color:#176a2f;text-transform:capitalize}.pill.bad{background:#fdecec;color:#9a2323}.muted{color:var(--secondary-text-color)}
      .profile-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:15px}.profile{display:flex;flex-direction:column;text-align:left;gap:9px;padding:18px;border:2px solid var(--divider-color);border-radius:12px;background:var(--card-background-color);color:var(--primary-text-color);cursor:pointer}.profile ha-icon{color:#078c9c}.profile.selected{border-color:#078c9c;background:#eaf8fa}.profile span{color:var(--secondary-text-color);line-height:1.4}
      .setup h3{margin-top:28px}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.form-grid.thirds{grid-template-columns:repeat(3,1fr)}.field{display:block;margin:13px 0}.field>span{display:block;font-weight:600;margin-bottom:7px}.field select,.field input,.instance select{width:100%;min-height:44px;padding:9px 11px;border:1px solid var(--divider-color);border-radius:8px;background:var(--card-background-color);color:var(--primary-text-color)}.field select[multiple]{min-height:110px}.unit{display:flex;align-items:center}.unit input{border-radius:8px 0 0 8px}.unit b{height:44px;padding:12px;background:var(--secondary-background-color);border:1px solid var(--divider-color);border-left:0;border-radius:0 8px 8px 0}.checkbox{display:flex;gap:10px;margin-top:28px;align-items:flex-start}.checkbox input{width:20px;height:20px}.actions{text-align:right;margin-top:24px}.primary{border:0;border-radius:9px;padding:12px 20px;background:#078c9c;color:white;font-weight:700;cursor:pointer}.primary:disabled{opacity:.55}
      .message{padding:13px 16px;border-radius:9px;margin-bottom:16px}.notice{background:#e7f6eb;color:#176a2f}.error{background:#fdecec;color:#9a2323}.loading{text-align:center;padding:80px 20px}
      @media(max-width:760px){header{padding:10px 16px}.brand small{display:none}nav{padding:0 10px}main{padding:16px}.metrics{grid-template-columns:1fr 1fr}.two,.profile-grid,.form-grid,.form-grid.thirds{grid-template-columns:1fr}.status h2{font-size:20px}}
      @media(max-width:430px){.metrics{grid-template-columns:1fr}.brand strong{font-size:20px}nav button{padding:13px 12px}}
    `;
  }
}

customElements.define("zeal-dry-panel", ZealDryPanel);
