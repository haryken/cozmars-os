async function defj(u, opt) {
    const r = await fetch(u, opt);
    const t = await r.text();
    try {
        return JSON.parse(t);
    } catch {
        throw new Error(t || r.statusText);
    }
}

function activateSection(target) {
    if (!target) return;
    document.querySelectorAll(".tabs button").forEach((b) => {
        b.classList.toggle("active", b.dataset.target === target);
    });
    document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
    const panel = document.querySelector(target);
    if (panel) panel.classList.add("active");
    const sel = document.getElementById("navSelect");
    if (sel && sel.value !== target) sel.value = target;
    syncDrawerActive(target);
    try {
        history.replaceState(null, "", target);
    } catch (_) {}
}

document.querySelectorAll(".tabs button").forEach((btn) => {
    btn.addEventListener("click", () => activateSection(btn.dataset.target));
});
const navSelect = document.getElementById("navSelect");
if (navSelect) {
    navSelect.addEventListener("change", () => activateSection(navSelect.value));
}

const navBurger = document.getElementById("navBurger");
const navDrawer = document.getElementById("navDrawer");
const navBackdrop = document.getElementById("navBackdrop");
const navDrawerClose = document.getElementById("navDrawerClose");
const navDrawerList = document.getElementById("navDrawerList");

function isMobileNav() {
    return window.matchMedia("(max-width: 768px)").matches;
}

function syncDrawerActive(target) {
    if (!navDrawerList) return;
    navDrawerList.querySelectorAll("button").forEach((b) => {
        b.classList.toggle("active", b.dataset.target === target);
    });
}

function buildNavDrawer() {
    if (!navDrawerList) return;
    navDrawerList.innerHTML = "";
    document.querySelectorAll(".tabs button").forEach((src) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.dataset.target = src.dataset.target;
        btn.textContent = src.textContent.trim();
        btn.addEventListener("click", () => {
            activateSection(btn.dataset.target);
            closeNavDrawer();
        });
        navDrawerList.appendChild(btn);
    });
    const active = document.querySelector(".tabs button.active");
    syncDrawerActive(active ? active.dataset.target : "#about");
}

function openNavDrawer() {
    if (!navDrawer || !isMobileNav()) return;
    navDrawer.classList.add("is-open");
    navDrawer.setAttribute("aria-hidden", "false");
    if (navBackdrop) {
        navBackdrop.hidden = false;
        void navBackdrop.offsetWidth;
        navBackdrop.classList.add("is-open");
    }
    if (navBurger) navBurger.setAttribute("aria-expanded", "true");
    document.body.classList.add("nav-drawer-open");
}

function closeNavDrawer() {
    if (!navDrawer) return;
    navDrawer.classList.remove("is-open");
    navDrawer.setAttribute("aria-hidden", "true");
    if (navBackdrop) {
        navBackdrop.classList.remove("is-open");
        window.setTimeout(() => {
            if (!navBackdrop.classList.contains("is-open")) navBackdrop.hidden = true;
        }, 220);
    }
    if (navBurger) navBurger.setAttribute("aria-expanded", "false");
    document.body.classList.remove("nav-drawer-open");
}

function toggleNavDrawer() {
    if (navDrawer && navDrawer.classList.contains("is-open")) closeNavDrawer();
    else openNavDrawer();
}

buildNavDrawer();
if (navBurger) navBurger.addEventListener("click", toggleNavDrawer);
if (navDrawerClose) navDrawerClose.addEventListener("click", closeNavDrawer);
if (navBackdrop) navBackdrop.addEventListener("click", closeNavDrawer);
document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeNavDrawer();
});
window.addEventListener("resize", () => {
    if (!isMobileNav()) closeNavDrawer();
});

if (location.hash && document.querySelector(location.hash)) {
    activateSection(location.hash);
} else {
    activateSection("#about");
}

function xzSetStatus(elId, msg, isError) {
    const el = document.getElementById(elId);
    if (!el) return;
    el.textContent = msg || "";
    el.style.color = isError ? "#f87171" : "#4ade80";
    el.style.display = msg ? "block" : "none";
}

function xzSelectedMode() {
    const on = document.querySelector('input[name="xzListenMode"]:checked');
    return on ? on.value : "xiaozhi";
}

function xzSelectedPreset() {
    const on = document.querySelector('input[name="xzPreset"]:checked');
    return on ? on.value : "custom";
}

function xzShowPresetUI(preset) {
    const pool = document.getElementById("xzPoolHelp");
    const custom = document.getElementById("xzCustomFields");
    const isPool = preset === "vi_pool";
    if (pool) pool.style.display = isPool ? "block" : "none";
    if (custom) custom.style.display = isPool ? "none" : "block";
    const vi = document.getElementById("xzPresetVi");
    const cu = document.getElementById("xzPresetCustom");
    if (vi) vi.checked = isPool;
    if (cu) cu.checked = !isPool;
}

function xzShowConfigForMode(mode) {
    const block = document.getElementById("xzConfigBlock");
    if (block) block.style.display = mode === "xiaozhi" ? "block" : "none";
    const xz = document.getElementById("xzModeXiaozhi");
    const vosk = document.getElementById("xzModeVosk");
    const off = document.getElementById("xzModeOff");
    if (xz) xz.checked = mode === "xiaozhi";
    if (vosk) vosk.checked = mode === "vosk";
    if (off) off.checked = mode === "off";
}

function xzApplyCfg(cfg) {
    if (!cfg) return;
    const ota = document.getElementById("xzOTABaseURL");
    const ep = document.getElementById("xzEndpoint");
    const did = document.getElementById("xzDeviceID");
    const cid = document.getElementById("xzClientID");
    if (ota) ota.value = cfg.ota_base_url || "https://api.tenclass.net/";
    if (ep) ep.value = cfg.endpoint || "";
    if (did) did.value = cfg.device_id || "";
    if (cid) cid.value = cfg.client_id || "";
    const macEl = document.getElementById("xzPoolMac");
    const cidEl = document.getElementById("xzPoolClient");
    if (macEl) macEl.textContent = cfg.device_id || "—";
    if (cidEl) cidEl.textContent = cfg.client_id || "—";
    xzShowPresetUI(cfg.identity_mode === "vi_pool" ? "vi_pool" : "custom");
    const mode = cfg.voice_mode || (cfg.enabled ? "xiaozhi" : "vosk");
    xzShowConfigForMode(mode);
    if (cfg.activation_code) {
        document.getElementById("xzCode").textContent = cfg.activation_code;
        document.getElementById("xzCodeBox").style.display = "block";
    }
}

async function xzLoad() {
    try {
        const cfg = await defj("/api/xiaozhi");
        xzApplyCfg(cfg);
    } catch (e) {
        xzSetStatus("xiaozhiStatus", "Không tải được cấu hình: " + e.message, true);
    }
}

async function xzOnModeRadio() {
    const mode = xzSelectedMode();
    xzShowConfigForMode(mode);
    xzSetStatus("xiaozhiStatus", "Đang lưu chế độ…", false);
    try {
        await defj("/api/voice", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mode, identity_mode: xzSelectedPreset() }),
        });
        xzSetStatus(
            "xiaozhiStatus",
            mode === "xiaozhi"
                ? "Đã chuyển sang Xiaozhi. Đánh thức (hey cozmars) là nói được."
                : mode === "vosk"
                  ? "Đã chuyển sang Vosk."
                  : "Đã tắt giọng.",
            false
        );
    } catch (e) {
        xzSetStatus("xiaozhiStatus", "Lỗi: " + e.message, true);
        await xzLoad();
    }
}

function xzOnPresetRadio() {
    xzShowPresetUI(xzSelectedPreset());
}

function xzShowResult(j) {
    const box = document.getElementById("xzCodeBox");
    if (j.code) {
        document.getElementById("xzCode").textContent = j.code;
        box.style.display = "block";
    } else {
        box.style.display = "none";
    }
    xzSetStatus("xzConfigStatus", j.message || "", j.status === "error");
    if (j.config) xzApplyCfg(j.config);
}

async function xzSaveAndActivate(newDevice) {
    const btn = document.getElementById("xzSaveActivateBtn");
    if (btn) btn.disabled = true;
    document.getElementById("xzCodeBox").style.display = "none";
    xzSetStatus("xzConfigStatus", "Đang gửi OTA lên máy chủ Xiaozhi…", false);
    try {
        const ident = xzSelectedPreset();
        const ota = document.getElementById("xzOTABaseURL").value;
        await defj("/api/voice", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                mode: "xiaozhi",
                ota_base_url: ota,
                identity_mode: ident,
            }),
        });
        const j = await defj("/api/xiaozhi/generate_code", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ identity_mode: ident, new_device: !!newDevice }),
        });
        xzShowResult(j);
    } catch (e) {
        xzSetStatus("xzConfigStatus", "Lỗi: " + e.message, true);
    } finally {
        if (btn) btn.disabled = false;
    }
}

function xzNewCode() {
    return xzSaveAndActivate(true);
}

async function ota() {
    const url = document.getElementById("otaurl").value;
    const j = await defj("/api/update", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
    });
    document.getElementById("otalog").textContent = JSON.stringify(j, null, 2);
}

async function gnew(n) {
    const j = await defj("/api/mods/" + n + "/new", { method: "POST" });
    document.getElementById("gst").textContent = JSON.stringify(j, null, 2);
}

async function intent(name) {
    await defj("/api/intent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
    });
}

defj("/about").then((j) => {
    const pill = document.getElementById("verPill");
    if (pill) pill.textContent = "Cozmars OS " + (j.version || "");
    document.getElementById("aboutj").textContent = JSON.stringify(j, null, 2);
});
xzLoad();
