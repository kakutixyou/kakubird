// frontend/src/components/blocks/CardGridBlock.jsx
import React from 'react';

interface CardGridBlockProps {
  block: {
    props: {
      title: string;
      subtitle: string;
      cards: {
        title: string;
        description: string;
        image: string;
        link: string;
      }[];
    };
  };
}

const CardGridBlock: React.FC<CardGridBlockProps> = ({ block }) => {
  const {
    title = 'Card Grid Title',
    subtitle = '',
    cards = [],
  } = block.props;

  return (
    <div
      className="
        relative
        overflow-hidden
        rounded-2xl
        border
        border-indigo-200
        dark:border-indigo-900/40
        bg-white
        shadow-lg
      "
    >
      {/* タイトル */}
      <h1
        className="
          text-2xl
          md:text-4xl
          font-extrabold
          leading-tight
          p-6
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
            text-gray-600
            font-medium
            p-6
          "
        >
          {subtitle}
        </p>
      )}

      {/* カードグリッド */}
      <div
        className="
          grid
          grid-cols-1
          md:grid-cols-2
          lg:grid-cols-3
          gap-6
          p-6
        "
      >
        {cards.map((card, index) => (
          <div
            key={index}
            className="
              relative
              overflow-hidden
              rounded-2xl
              border
              border-indigo-200
              dark:border-indigo-900/40
              bg-white
              shadow-lg
            "
          >
            {/* カード画像 */}
            {card.image && (
              <img
                src={card.image}
                alt={card.title}
                className="
                  w-full
                  h-48
                  object-cover
                  rounded-t-2xl
                "
              />
            )}

            {/* カードコンテンツ */}
            <div
              className="
                p-6
              "
            >
              {/* カードタイトル */}
              <h2
                className="
                  text-xl
                  font-bold
                  leading-tight
                "
              >
                {card.title}
              </h2>

              {/* カード説明 */}
              {card.description && (
                <p
                  className="
                    mt-3
                    text-sm
                    text-gray-600
                    font-medium
                  "
                >
                  {card.description}
                </p>
              )}

              {/* カードリンク */}
              {card.link && (
                <a
                  href={card.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="
                    inline-flex
                    items-center
                    justify-center
                    rounded-xl
                    bg-indigo-500
                    px-5
                    py-3
                    text-sm
                    font-bold
                    text-white
                    shadow-md
                    transition-all
                    duration-200
                    hover:scale-105
                    hover:shadow-xl
                    active:scale-95
                  "
                >
                  Learn More
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default CardGridBlock;
