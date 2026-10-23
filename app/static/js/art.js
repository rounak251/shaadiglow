// Vector "packshots" for the sample catalogue: no third-party product photos, no brands.
const shade = (hex, k) => {
  const n = parseInt(hex.slice(1), 16);
  let r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
  const f = (c) => Math.max(0, Math.min(255, Math.round(k > 0 ? c + (255 - c) * k : c * (1 + k))));
  return `rgb(${f(r)},${f(g)},${f(b)})`;
};

let uid = 0;
export function productArt(art = {}, size = 64) {
  const id = `a${++uid}`;
  const c = art.color || "#E8DCCF", a = art.accent || shade(c, -0.45);
  const grad = `<defs><linearGradient id="${id}" x1="0" x2="1"><stop offset="0" stop-color="${shade(c, 0.25)}"/>
    <stop offset="0.55" stop-color="${c}"/><stop offset="1" stop-color="${shade(c, -0.18)}"/></linearGradient>
    <linearGradient id="${id}m" x1="0" x2="1"><stop offset="0" stop-color="#f7e3a3"/><stop offset=".5" stop-color="#c9a04b"/>
    <stop offset="1" stop-color="#8c6a1d"/></linearGradient></defs>`;
  const label = (x, y, w) => `<rect x="${x}" y="${y}" width="${w}" height="9" rx="2" fill="#fff" opacity=".85"/>
    <rect x="${x + 3}" y="${y + 3}" width="${w * 0.55}" height="3" rx="1.5" fill="${a}"/>`;
  let body = "";
  switch (art.shape) {
    case "tube":
      body = `<path d="M22 10h20l4 36H18z" fill="url(#${id})"/><rect x="24" y="46" width="16" height="9" rx="2" fill="${a}"/>
        ${label(23, 22, 18)}`; break;
    case "dropper":
      body = `<rect x="20" y="24" width="24" height="32" rx="6" fill="url(#${id})"/><rect x="26" y="14" width="12" height="11" rx="2" fill="${a}"/>
        <ellipse cx="32" cy="12" rx="5" ry="4" fill="${shade(a, -0.2)}"/>${label(23, 36, 18)}`; break;
    case "pump":
      body = `<rect x="20" y="22" width="24" height="34" rx="5" fill="url(#${id})"/><rect x="27" y="14" width="10" height="9" fill="${a}"/>
        <path d="M27 14h14v4H27z" fill="${a}"/>${label(23, 34, 18)}`; break;
    case "bottle":
      body = `<rect x="19" y="20" width="26" height="36" rx="7" fill="url(#${id})"/><rect x="26" y="11" width="12" height="10" rx="2" fill="${a}"/>
        ${label(23, 34, 18)}`; break;
    case "jar":
      body = `<rect x="14" y="30" width="36" height="24" rx="6" fill="url(#${id})"/><rect x="13" y="22" width="38" height="10" rx="4" fill="${a}"/>
        ${label(20, 38, 24)}`; break;
    case "roller":
      body = `<rect x="23" y="18" width="18" height="38" rx="6" fill="url(#${id})"/><circle cx="32" cy="15" r="5" fill="#dfe6ee" stroke="${a}"/>
        ${label(25, 34, 14)}`; break;
    case "stick":
      body = `<rect x="24" y="18" width="16" height="38" rx="4" fill="${a}"/><rect x="25" y="10" width="14" height="10" rx="3" fill="url(#${id})"/>`; break;
    case "lipstick":
      body = `<rect x="22" y="36" width="20" height="20" rx="2" fill="url(#${id}m)"/><rect x="24" y="26" width="16" height="11" fill="#d9b25e"/>
        <path d="M25 26V14l14-6v18z" fill="${c}"/><path d="M25 14l14-6v4l-14 6z" fill="${shade(c, 0.25)}" opacity=".6"/>`; break;
    case "compact":
      body = `<circle cx="32" cy="34" r="20" fill="url(#${id}m)"/><circle cx="32" cy="34" r="15" fill="${c}"/>
        <path d="M22 28a12 12 0 0 1 14-6" stroke="#fff" stroke-width="2" opacity=".5" fill="none"/>`; break;
    case "palette": {
      const cs = art.colors || [c, c, c];
      body = `<rect x="8" y="20" width="48" height="28" rx="5" fill="#2b1d1d"/>` +
        cs.map((x, i) => `<rect x="${12 + i * 15}" y="25" width="12" height="18" rx="3" fill="${x}"/>`).join(""); break;
    }
    case "pencil":
      body = `<rect x="29" y="12" width="6" height="40" rx="2" fill="#3a2a2a"/><path d="M29 52h6l-3 6z" fill="${c}"/>
        <rect x="29" y="12" width="6" height="6" fill="url(#${id}m)"/>`; break;
    case "mascara":
      body = `<rect x="27" y="22" width="10" height="34" rx="3" fill="#1d1d1d"/><rect x="28" y="10" width="8" height="13" rx="2" fill="url(#${id}m)"/>`; break;
    case "wand":
      body = `<rect x="25" y="20" width="14" height="36" rx="4" fill="url(#${id})"/><rect x="26" y="9" width="12" height="12" rx="3" fill="${a}"/>`; break;
    case "sachet":
      body = `<path d="M14 16h36v36H14z" fill="url(#${id})"/><path d="M14 16h36l-2 4H16z" fill="${a}" opacity=".6"/>${label(20, 30, 24)}`; break;
    case "box":
      body = `<rect x="14" y="16" width="36" height="38" rx="3" fill="url(#${id})"/><rect x="14" y="16" width="36" height="7" fill="${a}"/>
        ${label(20, 34, 24)}`; break;
    case "image":
      return `<img src="${art.src}" alt="" width="${size}" height="${size}" style="object-fit:contain">`;
    default:
      body = `<rect x="18" y="16" width="28" height="38" rx="6" fill="url(#${id})"/>`;
  }
  return `<svg viewBox="0 0 64 64" width="${size}" height="${size}" aria-hidden="true">${grad}
    <ellipse cx="32" cy="58" rx="18" ry="3" fill="#000" opacity=".08"/>${body}</svg>`;
}
