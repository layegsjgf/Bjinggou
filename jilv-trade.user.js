// ==UserScript==
// @name         纪律面板 (jilv-trade)
// @namespace    https://github.com/layegsjgf/jilv-trade
// @version      0.3.0
// @description  debot.ai 悬浮迷你纪律面板
// @author       layegsjgf
// @match        https://debot.ai/*
// @match        https://*.debot.ai/*
// @grant        GM_setValue
// @grant        GM_getValue
// @run-at       document-end
// ==/UserScript==

(function () {
    'use strict';

    const STORAGE_KEY = 'jilv_trade_v2';

    function todayStr() {
        const d = new Date();
        return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
    }

    function loadState() {
        const raw = GM_getValue(STORAGE_KEY, null);
        let s = raw ? (typeof raw === 'string' ? JSON.parse(raw) : raw) : null;
        if (!s) {
            s = { todayOk: 0, todayErr: 0, totalOk: 0, totalErr: 0, date: todayStr(), checks: [false,false,false], pos: null };
        }
        if (s.date !== todayStr()) {
            s.todayOk = 0;
            s.todayErr = 0;
            s.date = todayStr();
        }
        if (!Array.isArray(s.checks) || s.checks.length !== 3) s.checks = [false,false,false];
        return s;
    }

    function save() { GM_setValue(STORAGE_KEY, JSON.stringify(state)); }
    let state = loadState();

    // --- CSS ---
    const css = document.createElement('style');
    css.textContent = `
#jilv-panel{position:fixed;z-index:2147483647;font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;font-size:14.4px;background:transparent;color:#ddd;border:1px solid rgba(255,255,255,.12);border-radius:10px;box-shadow:none;padding:10px 12px;user-select:none;min-width:0;width:max-content;}
#jilv-panel *{box-sizing:border-box;}
.jl-row{display:flex;align-items:center;gap:7px;white-space:nowrap;}
.jl-row.stats{margin-bottom:7px;padding-bottom:7px;border-bottom:1px solid rgba(255,255,255,.06);}
.jl-lbl{color:#999;font-size:13px;}
.jl-num{color:#4ade80;font-weight:700;font-size:15.5px;min-width:14px;text-align:center;}
.jl-num.err{color:#f87171;}
.jl-sep{color:rgba(255,255,255,.15);margin:0 3px;}
.jl-stepper{display:inline-flex;flex-direction:column;justify-content:center;align-items:center;width:12px;height:22px;cursor:pointer;margin-left:2px;}
.jl-stepper .arrow{display:block;width:0;height:0;border-left:5px solid transparent;border-right:5px solid transparent;}
.jl-stepper .up{border-bottom:6px solid #888;margin-bottom:3px;}
.jl-stepper .down{border-top:6px solid #888;}
.jl-stepper .up:hover{border-bottom-color:#4ade80;}
.jl-stepper .down:hover{border-top-color:#f87171;}
.jl-step{display:flex;align-items:center;padding:4px 0;cursor:pointer;border-radius:4px;gap:5px;}
.jl-step:hover{background:rgba(255,255,255,.04);}
.jl-step .txt{color:#ddd;font-size:14.4px;transition:all .15s;}
.jl-step.done .txt{color:#666;text-decoration:line-through;}
.jl-step .ck{width:16px;height:16px;border:1.5px solid #555;border-radius:3px;display:flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0;}
.jl-step.done .ck{border-color:#4ade80;background:#4ade80;color:#000;font-weight:bold;}
.jl-grip{position:absolute;bottom:4px;right:6px;color:#555;font-size:13px;cursor:move;line-height:1;}
.jl-grip:hover{color:#999;}
.jl-total-num{color:#888;font-weight:600;font-size:13px;min-width:12px;text-align:center;}
`;
    document.documentElement.appendChild(css);

    // --- DOM ---
    const panel = document.createElement('div');
    panel.id = 'jilv-panel';
    panel.innerHTML = `
<div class="jl-row stats">
  <span class="jl-lbl">纪律交易</span><span class="jl-num" id="jl-ok">0</span><span class="jl-stepper" id="jl-ok-s"><span class="arrow up"></span><span class="arrow down"></span></span>
  <span class="jl-lbl" style="margin-left:4px;">错</span><span class="jl-num err" id="jl-err">0</span><span class="jl-stepper" id="jl-err-s"><span class="arrow up"></span><span class="arrow down"></span></span>
  <span class="jl-sep">┃</span>
  <span class="jl-lbl">总</span><span class="jl-total-num" id="jl-tok">0</span><span class="jl-total-num" id="jl-terr" style="color:#666;">0</span>
</div>
<div class="jl-step" data-i="0"><span class="txt">1. 4h 位置</span><span class="ck"></span></div>
<div class="jl-step" data-i="1"><span class="txt">2. 入场画像</span><span class="ck"></span></div>
<div class="jl-step" data-i="2"><span class="txt">3. 挂单不追高</span><span class="ck"></span></div>
<span class="jl-grip" id="jl-grip">⠿</span>
`;
    document.body.appendChild(panel);

    // --- 渲染 ---
    function render() {
        panel.querySelector('#jl-ok').textContent = state.todayOk;
        panel.querySelector('#jl-err').textContent = state.todayErr;
        panel.querySelector('#jl-tok').textContent = state.totalOk;
        panel.querySelector('#jl-terr').textContent = state.totalErr;
        panel.querySelectorAll('.jl-step').forEach((el, i) => {
            el.classList.toggle('done', !!state.checks[i]);
            el.querySelector('.ck').textContent = state.checks[i] ? '✓' : '';
        });
    }

    // --- 计数 ---
    function bindStepper(id, keyToday, keyTotal) {
        const el = panel.querySelector(id);
        el.querySelector('.up').addEventListener('click', (e) => {
            e.stopPropagation();
            state[keyToday]++;
            state[keyTotal]++;
            state.checks = [false, false, false];
            save(); render();
        });
        el.querySelector('.down').addEventListener('click', (e) => {
            e.stopPropagation();
            if (state[keyToday] > 0) { state[keyToday]--; state[keyTotal] = Math.max(0, state[keyTotal]-1); }
            state.checks = [false, false, false];
            save(); render();
        });
    }
    bindStepper('#jl-ok-s', 'todayOk', 'totalOk');
    bindStepper('#jl-err-s', 'todayErr', 'totalErr');

    // --- 打勾 ---
    panel.querySelectorAll('.jl-step').forEach(el => {
        el.addEventListener('click', () => {
            if (dragged) return;
            const i = Number(el.dataset.i);
            state.checks[i] = !state.checks[i];
            save(); render();
        });
    });

    // --- 拖动 ---
    let dragging = false, dragged = false, dx = 0, dy = 0;
    const grip = panel.querySelector('#jl-grip');

    grip.addEventListener('mousedown', (e) => {
        dragging = true; dragged = false;
        dx = e.clientX - panel.offsetLeft;
        dy = e.clientY - panel.offsetTop;
        e.preventDefault();
    });

    document.addEventListener('mousemove', (e) => {
        if (!dragging) return;
        dragged = true;
        let x = Math.max(0, Math.min(window.innerWidth - panel.offsetWidth, e.clientX - dx));
        let y = Math.max(0, Math.min(window.innerHeight - panel.offsetHeight, e.clientY - dy));
        panel.style.left = x + 'px';
        panel.style.top = y + 'px';
    });

    document.addEventListener('mouseup', () => {
        if (!dragging) return;
        dragging = false;
        state.pos = { x: panel.offsetLeft, y: panel.offsetTop };
        save();
        setTimeout(() => { dragged = false; }, 0);
    });

    // --- 初始位置 ---
    function initPos() {
        if (state.pos) {
            panel.style.left = Math.min(state.pos.x, window.innerWidth - panel.offsetWidth) + 'px';
            panel.style.top = Math.min(state.pos.y, window.innerHeight - panel.offsetHeight) + 'px';
        } else {
            panel.style.left = '576px';
            panel.style.top = '350px';
        }
    }

    // 跨天检测
    setInterval(() => {
        if (state.date !== todayStr()) {
            state.todayOk = 0; state.todayErr = 0;
            state.date = todayStr();
            state.checks = [false,false,false];
            save(); render();
        }
    }, 60000);

    initPos();
    render();
})();
