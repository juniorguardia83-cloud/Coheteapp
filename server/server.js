// Puente TikTok Live -> app Cohete Live.
// Se ejecuta en Termux (mismo celular). La app se conecta por WebSocket a ws://127.0.0.1:8765
// y recibe: status (live si/no), viewers, join, follow, gift, chat.
// No usa tu contraseña: solo necesita tu @usuario mientras estás en vivo.

'use strict';

const { WebSocketServer } = require('ws');
const tiktok = require('tiktok-live-connector');

// Compatible con versiones nuevas (TikTokLiveConnection) y antiguas (WebcastPushConnection)
const Connection = tiktok.TikTokLiveConnection || tiktok.WebcastPushConnection;
if (!Connection) {
  console.error('No encontré la clase de conexión en tiktok-live-connector. Prueba: npm install tiktok-live-connector@latest');
  process.exit(1);
}

const PORT = parseInt(process.env.PORT || '8765', 10);
const HOST = process.env.HOST || '127.0.0.1'; // solo este celular. Usa HOST=0.0.0.0 para otros dispositivos de tu red.
const RETRY_NOT_LIVE_MS = 20000;
const RETRY_DROPPED_MS = 10000;

process.on('unhandledRejection', (e) => console.error('[aviso] promesa rechazada:', e && e.message ? e.message : e));
process.on('uncaughtException', (e) => console.error('[aviso] error no controlado:', e && e.message ? e.message : e));

/* ---------- WebSocket hacia la app ---------- */
const wss = new WebSocketServer({ host: HOST, port: PORT });
let lastStatus = { type: 'status', live: false, username: '', message: 'Servidor listo. Falta el @usuario.' };

function broadcast(obj) {
  const data = JSON.stringify(obj);
  for (const c of wss.clients) {
    if (c.readyState === 1) { try { c.send(data); } catch (e) { /* cliente caído */ } }
  }
}
function setStatus(live, username, message) {
  lastStatus = { type: 'status', live, username: username || '', message: message || '' };
  broadcast(lastStatus);
  console.log(live ? '🔴 EN VIVO @' + username : '⚪ ' + (message || 'sin live'));
}

wss.on('listening', () => {
  console.log('Cohete Live server escuchando en ws://' + HOST + ':' + PORT);
  console.log('Abre la app, toca ⚙️ y pon tu @usuario de TikTok.');
});
wss.on('error', (e) => {
  console.error('No pude abrir el puerto ' + PORT + ':', e.message);
  console.error('¿Ya hay otro servidor abierto? Ciérralo o usa: PORT=8766 node server.js');
  process.exit(1);
});

wss.on('connection', (ws) => {
  ws.send(JSON.stringify(lastStatus));
  ws.on('message', (raw) => {
    let m;
    try { m = JSON.parse(String(raw)); } catch (e) { return; }
    if (m && m.type === 'connect' && m.username) startSession(String(m.username).replace(/^@/, '').trim());
  });
  ws.on('error', () => {});
});

/* ---------- datos del usuario ---------- */
function firstUrl(v) {
  if (!v) return '';
  if (typeof v === 'string') return v;
  if (Array.isArray(v)) return firstUrl(v[0]);
  if (typeof v === 'object') return firstUrl(v.url || v.urlList || v.urls || v.profilePictureUrl);
  return '';
}
function pickUser(d) {
  d = d || {};
  const u = d.user || d;
  const uid = u.uniqueId || d.uniqueId || '';
  return {
    id: uid || String(u.userId || d.userId || u.id || ''),
    name: u.nickname || d.nickname || uid || 'Anónimo',
    avatar: firstUrl(u.profilePictureUrl || d.profilePictureUrl || u.profilePicture || d.profilePicture || u.avatarThumb || u.avatar)
  };
}

/* ---------- sesion con TikTok ---------- */
let session = null;       // { username, conn, timer, stopped }

function stopSession() {
  if (!session) return;
  session.stopped = true;
  clearTimeout(session.timer);
  try { session.conn.disconnect(); } catch (e) { /* nada */ }
  session = null;
}

function startSession(username) {
  if (!username) return;
  if (session && session.username.toLowerCase() === username.toLowerCase()) {
    broadcast(lastStatus); // misma cuenta: solo reenviar estado
    return;
  }
  stopSession();
  console.log('Conectando a @' + username + ' ...');
  const s = { username, conn: null, timer: null, stopped: false, live: false };
  session = s;
  setStatus(false, username, 'Buscando tu live…');
  attempt(s);
}

function scheduleRetry(s, ms, msg) {
  if (s.stopped) return;
  setStatus(false, s.username, msg);
  clearTimeout(s.timer);
  s.timer = setTimeout(() => attempt(s), ms);
}

function attempt(s) {
  if (s.stopped) return;
  let conn;
  try {
    conn = new Connection(s.username);
  } catch (e) {
    scheduleRetry(s, RETRY_NOT_LIVE_MS, 'Error al preparar la conexión: ' + e.message);
    return;
  }
  s.conn = conn;
  let dropped = false;
  const onDrop = (why) => {
    if (dropped || s.stopped) return;
    dropped = true;
    s.live = false;
    scheduleRetry(s, RETRY_DROPPED_MS, why);
  };

  conn.on('connected', () => {});
  conn.on('disconnected', () => onDrop('Se cortó la conexión con el live. Reintentando…'));
  conn.on('streamEnd', () => onDrop('Tu live terminó. Esperando el siguiente…'));
  conn.on('error', (e) => console.error('[tiktok] error:', e && e.message ? e.message : e));

  conn.on('member', (d) => broadcast({ type: 'join', user: pickUser(d) }));
  conn.on('chat', (d) => broadcast({ type: 'chat', user: pickUser(d), text: d.comment || d.content || '' }));
  conn.on('gift', (d) => {
    const g = d.giftName || (d.giftDetails && d.giftDetails.giftName) || (d.gift && d.gift.name) || 'un regalo';
    broadcast({ type: 'gift', user: pickUser(d), gift: g });
  });
  conn.on('follow', (d) => broadcast({ type: 'follow', user: pickUser(d) }));
  conn.on('social', (d) => {
    const t = String(d.displayType || d.label || '').toLowerCase();
    if (t.indexOf('follow') !== -1) broadcast({ type: 'follow', user: pickUser(d) });
  });
  conn.on('roomUser', (d) => {
    const n = d.viewerCount != null ? d.viewerCount : d.totalUser;
    if (n != null) broadcast({ type: 'viewers', count: n });
  });

  Promise.resolve()
    .then(() => conn.connect())
    .then(() => {
      if (s.stopped) { try { conn.disconnect(); } catch (e) { /* nada */ } return; }
      s.live = true;
      setStatus(true, s.username, '');
    })
    .catch((err) => {
      const msg = err && err.message ? err.message : String(err);
      console.error('[tiktok] no se pudo conectar:', msg);
      const notLive = /offline|not.*live|LIVE has ended|not found|room id|UserOfflineError/i.test(msg);
      scheduleRetry(s, RETRY_NOT_LIVE_MS, notLive
        ? '@' + s.username + ' no está en vivo todavía. Reintento cada 20 s…'
        : 'No pude conectar (' + msg.slice(0, 80) + '). Reintento…');
    });
}

/* ---------- arranque opcional por linea de comandos: node server.js tuusuario ---------- */
const argUser = process.argv[2];
if (argUser) startSession(String(argUser).replace(/^@/, '').trim());

process.on('SIGINT', () => { stopSession(); process.exit(0); });
