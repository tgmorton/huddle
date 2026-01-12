/**
 * SettingsPanel - User preferences and settings content for left sideview
 *
 * Provides:
 * - Appearance settings (theme toggle)
 * - Future: Notification preferences
 * - Future: Gameplay preferences
 */

import React, { useState, useEffect } from 'react';
import { Sun, Moon, Monitor, Palette } from 'lucide-react';

type ThemeMode = 'dark' | 'light' | 'system';

export const SettingsPanel: React.FC = () => {
  // Theme state
  const [themeMode, setThemeMode] = useState<ThemeMode>(() => {
    const stored = localStorage.getItem('sepia-mode');
    if (stored === 'true') return 'light';
    if (stored === 'false') return 'dark';
    const systemPref = localStorage.getItem('theme-mode');
    if (systemPref === 'system') return 'system';
    return 'dark';
  });

  // Apply theme on mount and when changed
  useEffect(() => {
    applyTheme(themeMode);
  }, [themeMode]);

  // Listen for system theme changes if in system mode
  useEffect(() => {
    if (themeMode !== 'system') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: light)');
    const handleChange = () => applyTheme('system');

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [themeMode]);

  const applyTheme = (mode: ThemeMode) => {
    let shouldBeLight = false;

    if (mode === 'light') {
      shouldBeLight = true;
    } else if (mode === 'system') {
      shouldBeLight = window.matchMedia('(prefers-color-scheme: light)').matches;
    }

    if (shouldBeLight) {
      document.documentElement.classList.add('sepia-mode');
    } else {
      document.documentElement.classList.remove('sepia-mode');
    }

    localStorage.setItem('sepia-mode', String(shouldBeLight));
    localStorage.setItem('theme-mode', mode);
  };

  const handleThemeChange = (mode: ThemeMode) => {
    setThemeMode(mode);
  };

  return (
    <div className="settings-content">
      {/* Header */}
      <header className="settings-content__header">
        <h2>Settings</h2>
      </header>

      {/* Content */}
      <div className="settings-content__body">
        {/* Appearance Section */}
        <section className="settings-content__section">
          <h3>
            <Palette size={14} />
            <span>Appearance</span>
          </h3>

          {/* Theme Selector */}
          <div className="settings-content__setting">
            <label className="settings-content__label">Theme</label>
            <div className="settings-content__theme-options">
              <button
                className={`settings-content__theme-btn ${themeMode === 'dark' ? 'settings-content__theme-btn--active' : ''}`}
                onClick={() => handleThemeChange('dark')}
                title="Dark theme"
              >
                <Moon size={16} />
                <span>Dark</span>
              </button>
              <button
                className={`settings-content__theme-btn ${themeMode === 'light' ? 'settings-content__theme-btn--active' : ''}`}
                onClick={() => handleThemeChange('light')}
                title="Light theme"
              >
                <Sun size={16} />
                <span>Light</span>
              </button>
              <button
                className={`settings-content__theme-btn ${themeMode === 'system' ? 'settings-content__theme-btn--active' : ''}`}
                onClick={() => handleThemeChange('system')}
                title="Follow system preference"
              >
                <Monitor size={16} />
                <span>Auto</span>
              </button>
            </div>
            <p className="settings-content__hint">
              {themeMode === 'system'
                ? 'Follows your operating system preference'
                : themeMode === 'light'
                ? 'Clean light mode with darkened amber accents'
                : 'Default dark ops-center aesthetic'
              }
            </p>
          </div>
        </section>

        {/* Future sections can be added here */}
      </div>
    </div>
  );
};
