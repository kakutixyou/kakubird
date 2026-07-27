// frontend/src/components/blocks/TableBlock.jsx
import React from 'react';

interface TableBlockProps {
  block: {
    props: {
      title: string;
      subtitle: string;
      headers: string[];
      rows: {
        cells: string[];
      }[];
    };
  };
}

const TableBlock: React.FC<TableBlockProps> = ({ block }) => {
  const {
    title = 'Table Title',
    subtitle = '',
    headers = [],
    rows = [],
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

      {/* テーブル */}
      <table
        className="
          w-full
          table-auto
          border-collapse
          border
          border-indigo-200
          dark:border-indigo-900/40
        "
      >
        {/* ヘッダー */}
        <thead
          className="
            bg-indigo-100
            dark:bg-indigo-900/40
          "
        >
          <tr>
            {headers.map((header, index) => (
              <th
                key={index}
                className="
                  px-4
                  py-2
                  text-left
                  text-sm
                  font-bold
                  text-gray-600
                  dark:text-gray-200
                "
              >
                {header}
              </th>
            ))}
          </tr>
        </thead>

        {/* ボディー */}
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {row.cells.map((cell, cellIndex) => (
                <td
                  key={cellIndex}
                  className="
                    px-4
                    py-2
                    text-left
                    text-sm
                    text-gray-600
                    dark:text-gray-200
                  "
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default TableBlock;
