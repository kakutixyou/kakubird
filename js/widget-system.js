/**
 * widget-system.js
 * Core widget framework: registry, base class, and rendering engine.
 * Add new API widgets by registering them with WidgetRegistry.register().
 */

'use strict';

// ---------------------------------------------------------------------------
// BaseWidget – every widget extends this class
// ---------------------------------------------------------------------------
class BaseWidget {
  /**
   * @param {Object} config
   * @param {string} config.id       - Unique widget type id  (e.g. 'dog-api')
   * @param {string} config.label    - Human-readable label   (e.g. '犬の画像')
   * @param {string} config.icon     - Emoji / icon string    (e.g. '🐶')
   * @param {string} config.endpoint - API endpoint URL
   */
  constructor(config) {
    if (!config.id || !config.endpoint) {
      throw new Error('Widget config requires at least id and endpoint.');
    }
    this.id = config.id;
    this.label = config.label || config.id;
    this.icon = config.icon || '🧩';
    this.endpoint = config.endpoint;
  }

  /**
   * Fetch data from the configured endpoint.
   * Override in subclass for custom response parsing.
   * @returns {Promise<any>}
   */
  async fetchData() {
    const res = await fetch(this.endpoint);
    if (!res.ok) {
      throw new Error(`HTTP ${res.status} – ${this.endpoint}`);
    }
    return res.json();
  }

  /**
   * Build and return a DOM element to display in the page preview.
   * Subclasses MUST override this method.
   * @param {any} _data - Parsed response from fetchData()
   * @returns {HTMLElement}
   */
  // eslint-disable-next-line no-unused-vars
  render(_data) {
    throw new Error(`Widget "${this.id}" must implement render(data).`);
  }

  /**
   * Build the full widget block element (loading state → fetch → render).
   * Called by WidgetSystem when the user clicks "Add widget".
   * @returns {Promise<HTMLElement>}
   */
  async createBlock() {
    const block = document.createElement('div');
    block.className = 'widget-block';
    block.dataset.widgetId = this.id;

    // Loading placeholder
    const loader = document.createElement('div');
    loader.className = 'widget-loader';
    loader.textContent = '読み込み中…';
    block.appendChild(loader);

    // Delete button
    const del = document.createElement('button');
    del.className = 'widget-delete';
    del.title = 'ウィジェットを削除';
    del.textContent = '✕';
    del.addEventListener('click', () => block.remove());
    block.appendChild(del);

    try {
      const data = await this.fetchData();
      const content = this.render(data);
      loader.replaceWith(content);
    } catch (err) {
      loader.className = 'widget-error';
      loader.textContent = `エラー: ${err.message}`;
    }

    return block;
  }
}

// ---------------------------------------------------------------------------
// WidgetRegistry – singleton that maps widget ids to widget instances
// ---------------------------------------------------------------------------
const WidgetRegistry = (() => {
  const _registry = new Map();

  return {
    /**
     * Register a widget instance.
     * @param {BaseWidget} widget
     */
    register(widget) {
      if (!(widget instanceof BaseWidget)) {
        throw new Error('Only BaseWidget subclass instances can be registered.');
      }
      _registry.set(widget.id, widget);
    },

    /**
     * Retrieve a registered widget by id.
     * @param {string} id
     * @returns {BaseWidget|undefined}
     */
    get(id) {
      return _registry.get(id);
    },

    /**
     * Return an array of all registered widgets.
     * @returns {BaseWidget[]}
     */
    all() {
      return Array.from(_registry.values());
    },
  };
})();

// ---------------------------------------------------------------------------
// WidgetSystem – orchestrates the toolbar and inserts widgets into a page
// ---------------------------------------------------------------------------
const WidgetSystem = {
  /**
   * Initialise the widget toolbar inside `toolbarEl` and wire it up so that
   * clicking a button inserts the widget into the active page managed by
   * `pageManager`.
   *
   * @param {HTMLElement} toolbarEl   - Container for widget buttons
   * @param {Object}      pageManager - Instance of PageManager
   */
  init(toolbarEl, pageManager) {
    this._toolbar = toolbarEl;
    this._pageManager = pageManager;
    this._buildToolbar();
  },

  _buildToolbar() {
    this._toolbar.innerHTML = '';
    for (const widget of WidgetRegistry.all()) {
      const btn = document.createElement('button');
      btn.className = 'widget-btn';
      btn.dataset.widgetId = widget.id;
      btn.innerHTML = `<span class="widget-btn-icon">${widget.icon}</span>
                       <span class="widget-btn-label">${widget.label}を追加</span>`;
      btn.addEventListener('click', () => this._insertWidget(widget.id));
      this._toolbar.appendChild(btn);
    }
  },

  async _insertWidget(widgetId) {
    const widget = WidgetRegistry.get(widgetId);
    if (!widget) return;

    const btn = this._toolbar.querySelector(`[data-widget-id="${widgetId}"]`);
    if (btn) {
      btn.disabled = true;
      btn.classList.add('loading');
    }

    try {
      const block = await widget.createBlock();
      this._pageManager.addBlock(block);
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.classList.remove('loading');
      }
    }
  },
};

// Export for module environments; also keep globals for plain script usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { BaseWidget, WidgetRegistry, WidgetSystem };
}
