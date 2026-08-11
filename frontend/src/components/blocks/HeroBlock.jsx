// frontend/src/components/blocks/HeroBlock.jsx
import React from 'react';

const HeroBlock = ({ block }) => {
  // block.propsが存在しない場合のエラーを防ぐため、空オブジェクトでフォールバック
  const props = block?.props || {};

  const {
    title = 'Hero Title',
    subtitle = '',
    description = '',
    badge = '',
    buttonText = '',
    buttonLink = '#',
    align = 'center',
  } = props;

  const alignmentClass = align === 'left' ? 'items-start text-left' : 'items-center text-center';

  return (
    <div
      className="
        relative
        overflow-hidden
        rounded-2xl
        border
        border-indigo-200
        dark:border-indigo-900/40
        bg-gradient-to-br
        from-indigo-500
        via-purple-500
        to-pink-500
        text-white
        shadow-lg
      "
    >
      {/* 背景エフェクト */}
      <div
        className="
          absolute
          inset-0
          opacity-20
          pointer-events-none
        "
      >
        <div
          className="
            absolute
            -top-16
            -right-16
            w-48
            h-48
            rounded-full
            bg-white
            blur-3xl
          "
        />
        <div
          className="
            absolute
            -bottom-20
            -left-20
            w-56
            h-56
            rounded-full
            bg-purple-200
            blur-3xl
          "
        />
      </div>

      {/* メインコンテンツ */}
      <div
        className={`
          relative
          z-10
          flex
          flex-col
          ${alignmentClass}
          px-6
          py-10
          md:px-10
          md:py-14
        `}
      >
        {/* バッジ */}
        {badge && (
          <span
            className="
              mb-4
              inline-flex
              items-center
              rounded-full
              bg-white/20
              px-3
              py-1
              text-xs
              font-semibold
              tracking-wide
              backdrop-blur-sm
            "
          >
            {badge}
          </span>
        )}

        {/* タイトル */}
        <h1
          className="
            text-2xl
            md:text-4xl
            font-extrabold
            leading-tight
            drop-shadow-sm
          "
        >
          {title}
        </h1>

        {/* サブタイトル */}
        {subtitle && (
          <p
            className="
              mt-3
              text-lg
              md:text-xl
              text-white/90
              font-medium
            "
          >
            {subtitle}
          </p>
        )}

        {/* 説明 */}
        {description && (
          <p
            className="
              mt-5
              max-w-2xl
              text-sm
              md:text-base
              leading-relaxed
              text-white/80
            "
          >
            {description}
          </p>
        )}

        {/* ボタン */}
        {buttonText && (
          <div className="mt-7">
            <a
              href={buttonLink}
              target="_blank"
              rel="noopener noreferrer"
              className="
                inline-flex
                items-center
                justify-center
                rounded-xl
                bg-white
                px-5
                py-3
                text-sm
                font-bold
                text-indigo-700
                shadow-md
                transition-all
                duration-200
                hover:scale-105
                hover:shadow-xl
                active:scale-95
              "
            >
              {buttonText}
            </a>
          </div>
        )}
      </div>
    </div>
  );
};

export default HeroBlock;