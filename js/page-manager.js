/**
 * page-manager.js
 * Manages the "book" pages: creation, navigation (prev/next), and
 * inserting widget blocks into the currently visible page.
 */

'use strict';

const PageManager = (() => {
  let _pages = [];      // Array of page data objects { id, blocks: [] }
  let _currentIndex = 0;
  let _previewContainer = null;  // The DOM element that shows pages
  let _pageCounter = 0;

  // -------------------------------------------------------------------------
  // Internal helpers
  // -------------------------------------------------------------------------
  function _createPageData() {
    _pageCounter += 1;
    return { id: `page-${_pageCounter}`, blocks: [] };
  }

  function _renderPage(pageData) {
    const el = document.createElement('div');
    el.className = 'book-page';
    el.dataset.pageId = pageData.id;

    const pageHeader = document.createElement('div');
    pageHeader.className = 'page-header';
    pageHeader.textContent = `ページ ${_pages.indexOf(pageData) + 1}`;
    el.appendChild(pageHeader);

    const content = document.createElement('div');
    content.className = 'page-content';
    el.appendChild(content);

    for (const block of pageData.blocks) {
      content.appendChild(block);
    }

    return el;
  }

  function _showPage(index) {
    if (!_previewContainer) return;
    const pageData = _pages[index];
    if (!pageData) return;

    _previewContainer.innerHTML = '';
    const pageEl = _renderPage(pageData);

    // Animate page turn
    pageEl.classList.add('page-enter');
    _previewContainer.appendChild(pageEl);
    requestAnimationFrame(() => pageEl.classList.add('page-enter-active'));

    _updateNav();
  }

  function _updateNav() {
    const prevBtn = document.getElementById('prev-page-btn');
    const nextBtn = document.getElementById('next-page-btn');
    const indicator = document.getElementById('page-indicator');

    if (prevBtn) prevBtn.disabled = _currentIndex <= 0;
    if (nextBtn) nextBtn.disabled = _currentIndex >= _pages.length - 1;
    if (indicator) {
      indicator.textContent = `${_currentIndex + 1} / ${_pages.length}`;
    }
  }

  // -------------------------------------------------------------------------
  // Public API
  // -------------------------------------------------------------------------
  return {
    /**
     * Initialise PageManager.
     * @param {HTMLElement} previewContainer - The book preview area
     */
    init(previewContainer) {
      _previewContainer = previewContainer;
      _pages = [_createPageData()]; // Start with one blank page
      _currentIndex = 0;
      _showPage(_currentIndex);
    },

    /** Add a new blank page and navigate to it. */
    addPage() {
      _pages.push(_createPageData());
      _currentIndex = _pages.length - 1;
      _showPage(_currentIndex);
    },

    /** Navigate to the previous page. */
    prevPage() {
      if (_currentIndex > 0) {
        _currentIndex -= 1;
        _showPage(_currentIndex);
      }
    },

    /** Navigate to the next page. */
    nextPage() {
      if (_currentIndex < _pages.length - 1) {
        _currentIndex += 1;
        _showPage(_currentIndex);
      }
    },

    /**
     * Append a widget block DOM element to the current page.
     * @param {HTMLElement} blockEl
     */
    addBlock(blockEl) {
      const pageData = _pages[_currentIndex];
      if (!pageData) return;

      pageData.blocks.push(blockEl);

      // Append directly to the live DOM (no full re-render needed)
      const pageContent = _previewContainer.querySelector('.page-content');
      if (pageContent) {
        blockEl.classList.add('block-enter');
        pageContent.appendChild(blockEl);
        requestAnimationFrame(() => blockEl.classList.add('block-enter-active'));
      }
    },

    /** Return the current page data (read-only snapshot). */
    getCurrentPage() {
      return { ..._pages[_currentIndex] };
    },

    /** Return total number of pages. */
    get pageCount() {
      return _pages.length;
    },
  };
})();

// Export for module environments
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { PageManager };
}
