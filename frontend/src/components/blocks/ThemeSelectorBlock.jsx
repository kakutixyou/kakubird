// blocks/ThemeSelectorBlock.jsx
export default function ThemeSelectorBlock({
  block,
  onOptionSelect
}) {
  return (
    <div>
      <button>
        近未来
      </button>

      <button>
        ガラス
      </button>

      <button>
        漫画
      </button>
    </div>
  );
}