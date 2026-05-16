<template>
  <router-view v-slot="{ Component }">
    <transition name="fade-slide" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<script setup lang="ts">
</script>

<style>
:root {
  --primary: #5B7FFF;
  --primary-light: #7A96FF;
  --primary-dark: #3B5FFF;
  --primary-gradient: linear-gradient(135deg, #5B7FFF 0%, #3B5FFF 100%);
  --success: #52C41A;
  --warning: #FAAD14;
  --danger: #FF4D4F;
  --danger-light: #FF7875;
  --bg-body: #F0F2F5;
  --bg-card: #FFFFFF;
  --bg-sidebar: #1A1A2E;
  --bg-sidebar-hover: #16213E;
  --text-primary: #1D2129;
  --text-secondary: #4E5969;
  --text-tertiary: #86909C;
  --text-placeholder: #C9CDD4;
  --border: #E5E6EB;
  --border-light: #F2F3F5;
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.06);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.08);
  --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.12);
  --shadow-xl: 0 16px 48px rgba(0, 0, 0, 0.16);
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --radius-xl: 20px;
  --transition-fast: 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  --transition-normal: 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  --transition-slow: 0.45s cubic-bezier(0.4, 0, 0.2, 1);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif;
  background-color: var(--bg-body);
  color: var(--text-primary);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

a {
  text-decoration: none;
  color: var(--primary);
  transition: color var(--transition-fast);
}

a:hover {
  color: var(--primary-light);
}

/* ===== Element Plus Overrides ===== */
.el-card {
  border: none !important;
  border-radius: var(--radius-md) !important;
  box-shadow: var(--shadow-sm) !important;
  transition: box-shadow var(--transition-normal) !important;
}

.el-card:hover {
  box-shadow: var(--shadow-md) !important;
}

.el-card__header {
  padding: 16px 18px !important;
  border-bottom: 1px solid var(--border-light) !important;
}

@media (min-width: 768px) {
  .el-card__header {
    padding: 18px 24px !important;
  }
}

.el-button--primary {
  --el-button-primary-bg-color: var(--primary);
  --el-button-primary-border-color: var(--primary);
  --el-button-primary-hover-bg-color: var(--primary-light);
  --el-button-primary-hover-border-color: var(--primary-light);
  --el-button-primary-active-bg-color: var(--primary-dark);
  --el-button-primary-active-border-color: var(--primary-dark);
  border-radius: var(--radius-sm) !important;
  font-weight: 500 !important;
  transition: all var(--transition-fast) !important;
}

.el-button--primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(91, 127, 255, 0.4);
}

.el-button--primary:active {
  transform: translateY(0);
}

.el-button--default {
  border-radius: var(--radius-sm) !important;
  transition: all var(--transition-fast) !important;
}

.el-input__wrapper,
.el-select__wrapper,
.el-date-editor .el-input__wrapper {
  border-radius: var(--radius-sm) !important;
  box-shadow: 0 0 0 1px var(--border) inset !important;
  transition: box-shadow var(--transition-fast) !important;
}

.el-input__wrapper:hover,
.el-select__wrapper:hover,
.el-date-editor .el-input__wrapper:hover {
  box-shadow: 0 0 0 1px var(--primary-light) inset !important;
}

.el-input__wrapper.is-focus,
.el-select__wrapper.is-focus {
  box-shadow: 0 0 0 2px rgba(91, 127, 255, 0.2) inset !important;
}

.el-input-number__increase,
.el-input-number__decrease {
  border-radius: var(--radius-sm) !important;
}

.el-table {
  border-radius: var(--radius-sm) !important;
  overflow: hidden !important;
}

.el-table th.el-table__cell {
  background-color: #F7F8FA !important;
  color: var(--text-secondary) !important;
  font-weight: 600 !important;
}

.el-table--striped .el-table__body tr.el-table__row--striped td.el-table__cell {
  background-color: #FAFBFC !important;
}

.el-table__body tr:hover > td {
  background-color: #F0F5FF !important;
}

.el-tag {
  border-radius: 4px !important;
  font-weight: 500 !important;
}

.el-dialog {
  border-radius: var(--radius-lg) !important;
  overflow: hidden !important;
}

.el-dialog__header {
  padding: 20px 24px 0 !important;
  font-weight: 600 !important;
}

.el-dialog__body {
  padding: 24px !important;
}

.el-dialog__footer {
  padding: 0 24px 20px !important;
}

.el-pagination {
  --el-pagination-button-bg-color: transparent;
}

.el-pagination .el-pager li {
  border-radius: var(--radius-sm) !important;
  transition: all var(--transition-fast) !important;
}

.el-pagination .el-pager li:not(.is-disabled).is-active {
  background: var(--primary-gradient) !important;
  color: #fff !important;
}

.el-pagination .el-pager li:not(.is-disabled):hover {
  color: var(--primary) !important;
}

.el-pagination .el-pager li:not(.is-disabled).is-active:hover {
  color: #fff !important;
}

.el-progress-bar__outer {
  border-radius: 4px !important;
  background-color: #F0F0F0 !important;
}

.el-progress-bar__inner {
  border-radius: 4px !important;
  transition: width 0.6s ease !important;
}

.el-dropdown-menu__item:hover {
  background-color: #F0F5FF !important;
  color: var(--primary) !important;
}

.el-statistic {
  --el-statistic-content-font-size: 26px !important;
}

/* Scrollbar */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: #D0D5DD;
  border-radius: 3px;
  transition: background var(--transition-fast);
}

::-webkit-scrollbar-thumb:hover {
  background: #B0B5BD;
}

/* Transition */
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all var(--transition-normal);
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}

/* ===== Mobile Overrides ===== */
@media (max-width: 767px) {
  /* Dialog - bottom sheet style */
  .el-overlay-dialog {
    display: flex !important;
    align-items: flex-end !important;
    justify-content: center !important;
  }

  .el-dialog {
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 !important;
    border-radius: 20px 20px 0 0 !important;
    position: fixed !important;
    bottom: 0 !important;
    left: 0 !important;
    right: 0 !important;
    max-height: 90vh !important;
    overflow-y: auto !important;
    animation: slide-up 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
  }

  @keyframes slide-up {
    from { transform: translateY(100%); }
    to { transform: translateY(0); }
  }

  .el-dialog__header {
    padding: 20px 24px 0 !important;
    font-size: 17px !important;
  }

  .el-dialog__body {
    padding: 20px 24px !important;
  }

  .el-dialog__footer {
    padding: 0 24px 24px !important;
    display: flex !important;
    gap: 12px !important;
  }

  .el-dialog__footer .el-button {
    flex: 1 !important;
    min-width: 0 !important;
    height: 48px !important;
    font-size: 15px !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
  }

  .el-dialog .el-form-item {
    margin-bottom: 20px !important;
  }

  .el-dialog .el-form-item__label {
    padding-bottom: 6px !important;
    font-size: 14px !important;
    font-weight: 500 !important;
  }

  /* Form inputs - larger touch targets */
  .el-dialog .el-input__wrapper,
  .el-dialog .el-select__wrapper {
    height: 48px !important;
    padding: 0 16px !important;
    border-radius: 12px !important;
  }

  .el-dialog .el-input-number {
    width: 100% !important;
  }

  .el-dialog .el-input-number .el-input-number__decrease,
  .el-dialog .el-input-number .el-input-number__increase {
    width: 40px !important;
    border-radius: 12px !important;
  }

  .el-dialog .el-textarea__inner {
    border-radius: 12px !important;
    padding: 12px 16px !important;
    font-size: 15px !important;
  }

  .el-dialog .el-radio-button__inner {
    height: 44px !important;
    line-height: 44px !important;
    padding: 0 20px !important;
    font-size: 14px !important;
  }

  /* Buttons - flat touch feedback */
  .el-button--primary {
    --el-button-primary-hover-bg-color: var(--primary);
    --el-button-primary-hover-border-color: var(--primary);
  }

  .el-button--primary:hover {
    transform: none;
    box-shadow: none;
  }

  .el-button--default:hover {
    transform: none;
  }

  /* Select dropdown larger touch targets */
  .el-select-dropdown__item {
    min-height: 44px !important;
    padding: 8px 16px !important;
    font-size: 15px !important;
  }

  .el-select-dropdown {
    border-radius: 14px !important;
  }

  /* Date picker panel fit screen */
  .el-picker-panel {
    left: 4px !important;
    right: 4px !important;
    max-width: calc(100vw - 8px) !important;
    border-radius: 14px !important;
  }

  /* Message box - full width on mobile */
  .el-message-box {
    width: 88% !important;
    max-width: 360px !important;
    border-radius: 16px !important;
  }

  .el-message-box .el-button {
    height: 44px !important;
    border-radius: 10px !important;
    font-size: 14px !important;
  }

  /* Message - top positioned */
  .el-message {
    min-width: 80% !important;
    border-radius: 12px !important;
  }

  /* Global touch feedback */
  button:active {
    transform: scale(0.96);
  }

  ::-webkit-scrollbar {
    width: 3px;
    height: 3px;
  }

  /* Card adjustments */
  .el-card {
    border-radius: 14px !important;
  }

  /* Table adjustments */
  .el-table th.el-table__cell {
    font-size: 12px !important;
  }
}
</style>
