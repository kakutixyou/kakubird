/**
 * dog-api-widget.js
 * Widget that fetches a random dog image from the Dog CEO API.
 *
 * Endpoint: https://dog.ceo/api/breeds/image/random
 * Response: { message: "<image url>", status: "success" }
 *
 * To add a new API widget, copy this file, change the config and
 * override render() – then register the new instance in index.html.
 */

'use strict';

class DogApiWidget extends BaseWidget {
  constructor() {
    super({
      id: 'dog-api',
      label: '犬の画像',
      icon: '🐶',
      endpoint: 'https://dog.ceo/api/breeds/image/random',
    });
  }

  /**
   * Parse the Dog CEO API response and return the image URL.
   * @param {{ message: string, status: string }} data
   * @returns {string} image URL
   */
  _parseImageUrl(data) {
    if (!data || !data.message) {
      throw new Error('Dog API から画像 URL を取得できませんでした。');
    }
    return data.message;
  }

  /**
   * Build the DOM element shown inside the page preview.
   * @param {{ message: string, status: string }} data
   * @returns {HTMLElement}
   */
  render(data) {
    const imageUrl = this._parseImageUrl(data);

    const wrapper = document.createElement('div');
    wrapper.className = 'widget-content dog-api-content';

    const img = document.createElement('img');
    img.src = imageUrl;
    img.alt = 'ランダムな犬の画像';
    img.className = 'dog-api-image';
    img.loading = 'lazy';

    // Extract breed name from URL for a caption (e.g. "hound-afghan")
    const breedMatch = imageUrl.match(/breeds\/([^/]+)\//);
    const caption = document.createElement('p');
    caption.className = 'dog-api-caption';
    caption.textContent = breedMatch ? `犬種: ${breedMatch[1]}` : '犬の画像';

    wrapper.appendChild(img);
    wrapper.appendChild(caption);
    return wrapper;
  }
}

// Register the widget so WidgetSystem can discover it
WidgetRegistry.register(new DogApiWidget());
