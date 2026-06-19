/**
 * Theme bootstrap. Runs synchronously inside <head> before paint so the
 * correct `data-theme` is set on <html> without a flash.
 *
 * Stored value: 'light' | 'dark' | 'auto' (default 'auto').
 * 'auto' resolves to the OS preference via prefers-color-scheme.
 */
(function () {
  try {
    var stored = localStorage.getItem('theme');
    var theme = stored === 'light' || stored === 'dark' || stored === 'auto' ? stored : 'auto';
    var resolved =
      theme === 'auto'
        ? window.matchMedia('(prefers-color-scheme: dark)').matches
          ? 'dark'
          : 'light'
        : theme;
    document.documentElement.setAttribute('data-theme', resolved);
    document.documentElement.setAttribute('data-theme-pref', theme);
  } catch (_) {
    document.documentElement.setAttribute('data-theme', 'light');
    document.documentElement.setAttribute('data-theme-pref', 'auto');
  }
})();
