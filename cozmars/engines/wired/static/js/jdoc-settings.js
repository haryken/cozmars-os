function setJdocStatus(status) {
    const el = document.getElementById("jdocStatus");
    if (el) el.innerHTML = status ? `<p>${status}</p>` : "";
}

function showBotSection(id) {
    document.querySelectorAll(".bot-section").forEach((el) => {
        el.style.display = "none";
    });
    document.querySelectorAll(".bot-nav-item").forEach((el) => el.classList.remove("active"));
    const sec = document.getElementById(id);
    if (sec) sec.style.display = "block";
    document.querySelectorAll(".bot-nav-item").forEach((el) => {
        const oc = el.getAttribute("onclick") || "";
        if (oc.indexOf("'" + id + "'") >= 0) el.classList.add("active");
    });
}

async function setLocation() {
    const v = document.getElementById("location").value;
    setJdocStatus("Đang đặt vị trí...");
    try {
        const res = await fetch(`/api/mods/JdocSettings/setLocation?location=${encodeURIComponent(v)}`);
        if (!res.ok) {
            const e = await res.json().catch(() => ({}));
            setJdocStatus(`${e.status || "error"}: ${e.message || res.status}`);
        } else {
            setJdocStatus("Đã lưu vị trí.");
        }
    } catch (e) {
        setJdocStatus(`Lỗi mạng: ${e.message}`);
    }
}

async function setTimezone() {
    const v = document.getElementById("timezone").value;
    setJdocStatus("Đang đặt múi giờ...");
    try {
        const res = await fetch(`/api/mods/JdocSettings/setTimezone?timezone=${encodeURIComponent(v)}`);
        if (!res.ok) {
            const e = await res.json().catch(() => ({}));
            setJdocStatus(`${e.status || "error"}: ${e.message || res.status}`);
        } else {
            setJdocStatus("Đã lưu múi giờ.");
        }
    } catch (e) {
        setJdocStatus(`Lỗi mạng: ${e.message}`);
    }
}

async function setTempUnits() {
    const v = document.getElementById("tUnits").value;
    setJdocStatus("Đang đặt đơn vị nhiệt...");
    try {
        const res = await fetch(`/api/mods/JdocSettings/setFahrenheit?t=${encodeURIComponent(v)}`);
        if (!res.ok) {
            const e = await res.json().catch(() => ({}));
            setJdocStatus(`${e.status || "error"}: ${e.message || res.status}`);
        } else {
            setJdocStatus("Đã lưu đơn vị nhiệt.");
        }
    } catch (e) {
        setJdocStatus(`Lỗi mạng: ${e.message}`);
    }
}

async function getLocation() {
    try {
        const res = await fetch(`/api/mods/JdocSettings/getLocation`);
        if (res.ok) document.getElementById("location").value = await res.text();
    } catch (_) {}
}

async function getTimezone() {
    try {
        const res = await fetch(`/api/mods/JdocSettings/getTimezone`);
        if (res.ok) {
            const el = document.getElementById("timezone");
            const v = (await res.text()).trim();
            if (el && v) el.value = v;
        }
    } catch (_) {}
}

async function getTempUnits() {
    try {
        const res = await fetch(`/api/mods/JdocSettings/getFahrenheit`);
        if (res.ok) document.getElementById("tUnits").value = (await res.text()).trim() || "c";
    } catch (_) {}
}

async function getMasterVolume() {
    try {
        const res = await fetch(`/api/mods/JdocSettings/getVolume`);
        if (!res.ok) return;
        const v = (await res.text()).trim();
        document.querySelectorAll('input[name="vol"]').forEach((el) => {
            el.checked = el.value === v;
        });
    } catch (_) {}
}

async function setMasterVolumeVal(level) {
    setJdocStatus("Đang đặt âm lượng...");
    try {
        const res = await fetch(`/api/mods/JdocSettings/setVolume?level=${level}`);
        if (!res.ok) {
            const e = await res.json().catch(() => ({}));
            setJdocStatus(`${e.status || "error"}: ${e.message || res.status}`);
        } else {
            setJdocStatus("Đã cập nhật âm lượng.");
            getMasterVolume();
        }
    } catch (e) {
        setJdocStatus(`Lỗi mạng: ${e.message}`);
    }
}

async function getEyePreset() {
    try {
        const res = await fetch(`/api/mods/JdocSettings/getEyeColor`);
        if (!res.ok) return;
        const j = await res.json();
        if (j.iscustom) {
            document.querySelectorAll('input[name="eye"]').forEach((el) => { el.checked = false; });
            const hue = typeof j.hue === "number" ? j.hue : 0.5;
            const sat = typeof j.saturation === "number" ? j.saturation : 1;
            const hueEl = document.getElementById("eyeHue");
            const satEl = document.getElementById("eyeSat");
            if (hueEl) hueEl.value = String(hue);
            if (satEl) satEl.value = String(sat);
            syncEyeCustomUIFromSliders();
        } else if (typeof j.preset === "number") {
            document.querySelectorAll('input[name="eye"]').forEach((el) => {
                el.checked = el.value === String(j.preset);
            });
        }
    } catch (_) {}
}

async function setEyePresetVal(preset) {
    setJdocStatus("Đang đổi màu mắt...");
    try {
        const res = await fetch(`/api/mods/JdocSettings/setEyeColor?preset=${preset}`);
        if (!res.ok) {
            const e = await res.json().catch(() => ({}));
            setJdocStatus(`${e.status || "error"}: ${e.message || res.status}`);
        } else {
            setJdocStatus("Đã đổi màu mắt.");
            getEyePreset();
        }
    } catch (e) {
        setJdocStatus(`Lỗi mạng: ${e.message}`);
    }
}

function hsvToHex(h, s, v) {
    const i = Math.floor(h * 6);
    const f = h * 6 - i;
    const p = v * (1 - s);
    const q = v * (1 - f * s);
    const t = v * (1 - (1 - f) * s);
    let r, g, b;
    switch (i % 6) {
        case 0: r = v; g = t; b = p; break;
        case 1: r = q; g = v; b = p; break;
        case 2: r = p; g = v; b = t; break;
        case 3: r = p; g = q; b = v; break;
        case 4: r = t; g = p; b = v; break;
        default: r = v; g = p; b = q;
    }
    const to = (x) => Math.round(x * 255).toString(16).padStart(2, "0");
    return `#${to(r)}${to(g)}${to(b)}`;
}

function hexToHsv(hex) {
    const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    if (!m) return { h: 0.5, s: 1, v: 1 };
    const r = parseInt(m[1], 16) / 255;
    const g = parseInt(m[2], 16) / 255;
    const b = parseInt(m[3], 16) / 255;
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    const d = max - min;
    let h = 0;
    if (d !== 0) {
        switch (max) {
            case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
            case g: h = ((b - r) / d + 2) / 6; break;
            default: h = ((r - g) / d + 4) / 6; break;
        }
    }
    const s = max === 0 ? 0 : d / max;
    return { h, s, v: max };
}

function syncEyeCustomUIFromSliders() {
    const hue = parseFloat(document.getElementById("eyeHue").value);
    const sat = parseFloat(document.getElementById("eyeSat").value);
    document.getElementById("eyeHueVal").textContent = hue.toFixed(2);
    document.getElementById("eyeSatVal").textContent = sat.toFixed(2);
    const hex = hsvToHex(hue, sat, 1);
    const picker = document.getElementById("eyeColorPicker");
    const swatch = document.getElementById("eyeCustomSwatch");
    if (picker) picker.value = hex;
    if (swatch) swatch.style.background = hex;
}

function onEyeSliderInput() {
    syncEyeCustomUIFromSliders();
}

function onEyePickerInput() {
    const hex = document.getElementById("eyeColorPicker").value;
    const { h, s } = hexToHsv(hex);
    document.getElementById("eyeHue").value = String(h);
    document.getElementById("eyeSat").value = String(Math.max(s, 0.15));
    syncEyeCustomUIFromSliders();
}

async function applyCustomEyeColor() {
    const hue = parseFloat(document.getElementById("eyeHue").value);
    const sat = parseFloat(document.getElementById("eyeSat").value);
    setJdocStatus("Đang áp màu tùy chỉnh...");
    try {
        const qs = new URLSearchParams({ hue: String(hue), saturation: String(sat) });
        const res = await fetch(`/api/mods/JdocSettings/setCustomEyeColor?${qs.toString()}`);
        if (!res.ok) {
            const e = await res.json().catch(() => ({}));
            setJdocStatus(`${e.status || "error"}: ${e.message || res.status}`);
        } else {
            document.querySelectorAll('input[name="eye"]').forEach((el) => { el.checked = false; });
            setJdocStatus("Đã áp màu tùy chỉnh.");
            getEyePreset();
        }
    } catch (e) {
        setJdocStatus(`Lỗi mạng: ${e.message}`);
    }
}

async function setExpr(name) {
    try {
        await fetch("/api/mods/JdocSettings/setExpression?name=" + encodeURIComponent(name));
        setJdocStatus("Biểu cảm · " + name);
    } catch (e) {
        setJdocStatus(`Lỗi: ${e.message}`);
    }
}

async function setCliff(on) {
    try {
        await fetch("/api/mods/JdocSettings/setCliff?on=" + (on ? "1" : "0"));
        setJdocStatus(on ? "Cliff bật." : "Cliff tắt.");
    } catch (e) {
        setJdocStatus(`Lỗi: ${e.message}`);
    }
}

async function getCliff() {
    try {
        const res = await fetch("/api/mods/JdocSettings/getCliff");
        if (!res.ok) return;
        const v = (await res.text()).trim();
        document.querySelectorAll('input[name="cliff"]').forEach((el) => {
            el.checked = el.value === (v === "0" ? "0" : "1");
        });
    } catch (_) {}
}

function stimSliderInput(v) {
    const stim = Number(v) / 100;
    const el = document.getElementById("stimSliderLabel");
    if (el) el.textContent = stim.toFixed(2);
}

async function stimPreset(v) {
    if (v === "auto") {
        await fetch("/api/mods/JdocSettings/setStim?mode=auto");
        document.getElementById("stimModeLabel").textContent = "auto";
        setJdocStatus("Stim auto.");
        return;
    }
    const stim = Number(v);
    document.getElementById("stimSlider").value = String(Math.round(stim * 100));
    stimSliderInput(stim * 100);
    await fetch(`/api/mods/JdocSettings/setStim?mode=hold&value=${stim}`);
    document.getElementById("stimModeLabel").textContent = "hold";
    setJdocStatus("Stim " + stim.toFixed(2));
}

async function stimSliderCommit(v) {
    const stim = Number(v) / 100;
    await fetch(`/api/mods/JdocSettings/setStim?mode=hold&value=${stim}`);
    document.getElementById("stimModeLabel").textContent = "hold";
}

async function loadBotSettings() {
    await Promise.all([
        getLocation(),
        getTimezone(),
        getTempUnits(),
        getMasterVolume(),
        getEyePreset(),
        getCliff(),
    ]);
}

loadBotSettings();
if (document.getElementById("eyeHue")) syncEyeCustomUIFromSliders();
