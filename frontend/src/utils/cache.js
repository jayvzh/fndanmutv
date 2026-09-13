// 浏览器本地缓存（localStorage）：目录列表 / 当前 tab / 清理页扫描结果的持久化
const PREFIX = 'fndanmutv_cache_';

export const BROWSE_CACHE_KEY = PREFIX + 'browse';        // 目录浏览文件列表（按路径分条目）
export const BROWSE_LAST_PATH_KEY = PREFIX + 'browse_path'; // 上次浏览到的目录
export const CLEANUP_CACHE_KEY = PREFIX + 'cleanup';      // 清理页扫描结果
export const DASHBOARD_CACHE_KEY = PREFIX + 'dashboard';  // 仪表盘状态/最近运行/下次运行
export const TAB_KEY = 'fndanmutv_cache_tab';             // 当前所在 tab

// 目录浏览缓存过期时间（可设定）：超过该时长未更新，首次访问时自动重新拉取
export const BROWSE_CACHE_TTL_MS = 30 * 60 * 1000;

export function readCache(key, { ttl = 0 } = {}) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const entry = JSON.parse(raw);
    if (ttl > 0 && Date.now() - (entry.ts || 0) > ttl) return null;
    return entry.value;
  } catch {
    return null;
  }
}

export function writeCache(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify({ ts: Date.now(), value }));
  } catch {
    // 配额满等异常静默忽略，不影响功能
  }
}

export function clearCache(key) {
  try {
    localStorage.removeItem(key);
  } catch {
    // 忽略
  }
}
