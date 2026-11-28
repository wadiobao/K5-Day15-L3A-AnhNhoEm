/**
 * ReviewShield Manifest V3 Service Worker.
 * Chỉ mở Side Panel khi người dùng chủ động bấm biểu tượng Extension.
 * Không chạy ngầm tự động cào dữ liệu.
 */

async function configureSidePanel() {
  if (chrome.sidePanel && chrome.sidePanel.setPanelBehavior) {
    try {
      await chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
    } catch (err) {
      console.warn("[ReviewShield] setPanelBehavior error:", err);
    }
  }
}

chrome.runtime.onInstalled.addListener(() => {
  configureSidePanel();
});

chrome.runtime.onStartup.addListener(() => {
  configureSidePanel();
});
