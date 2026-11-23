import React from 'react';

interface ElevatorFloorMeta {
  label?: string;
  title?: string;
  summary?: string;
}

export interface ElevatorFloorItem extends ElevatorFloorMeta {
  floor: number;
}

export interface ElevatorData {
  topic?: string;
  title?: string;
  knowledge_id?: string;
  mode?: string;
  current_floor?: number;
  current_floor_label?: string;
  max_floor?: number;
  max_floor_label?: string;
  has_next?: boolean;
  has_prev?: boolean;
  floors?: ElevatorFloorItem[] | Record<string, ElevatorFloorMeta>;
}

export interface ElevatorNavigatorBlockProps {
  elevator: ElevatorData;
  onOptionSelect?: (payload: unknown) => void;
}

function isFloorNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 1;
}

function getFloors(elevator: ElevatorData): ElevatorFloorItem[] {
  const raw = elevator.floors;
  const items = Array.isArray(raw)
    ? raw
    : Object.entries(raw ?? {}).map(([key, info]) => ({
        ...info,
        floor: Number(key),
      }));

  const byFloor = new Map<number, ElevatorFloorItem>();
  for (const item of items) {
    if (item && isFloorNumber(item.floor)) byFloor.set(item.floor, item);
  }

  if (byFloor.size > 0) {
    return [...byFloor.values()].sort((a, b) => a.floor - b.floor);
  }

  const max = isFloorNumber(elevator.max_floor) ? elevator.max_floor : 1;
  return Array.from({ length: max }, (_, index) => ({
    floor: index + 1,
    title: `ステップ ${index + 1}`,
  }));
}

export function ElevatorNavigatorBlock({
  elevator,
  onOptionSelect,
}: ElevatorNavigatorBlockProps): React.ReactElement | null {
  if (!elevator) return null;

  const floors = getFloors(elevator);
  const currentIndex = Math.max(
    0,
    floors.findIndex(item => item.floor === elevator.current_floor),
  );
  const current = floors[currentIndex];
  const previous = elevator.has_prev === false ? undefined : floors[currentIndex - 1];
  const next = elevator.has_next === false ? undefined : floors[currentIndex + 1];
  const lastFloor = floors[floors.length - 1].floor;
  const maxFloor = isFloorNumber(elevator.max_floor)
    ? Math.max(elevator.max_floor, lastFloor)
    : lastFloor;
  const topic = elevator.topic || elevator.title || elevator.knowledge_id || '知識エレベーター';

  const labelFor = (item: ElevatorFloorItem) =>
    item.label
    || (item.floor === elevator.current_floor ? elevator.current_floor_label : undefined)
    || `${item.floor}F`;

  const sendFloor = (item: ElevatorFloorItem) => {
    onOptionSelect?.({
      action: 'send_chat',
      text: `${item.floor}F`,
      knowledge_id: elevator.knowledge_id,
      floor: item.floor,
    });
  };

  return (
    <div className="mt-2.5 rounded-xl border border-indigo-200 bg-indigo-50/60 p-3 text-xs dark:border-indigo-800 dark:bg-indigo-950/40">
      <div className="flex flex-wrap items-center gap-2 font-semibold text-indigo-900 dark:text-indigo-200">
        <span aria-hidden="true">🛗</span>
        <span>{topic}</span>
        <span className="rounded-md bg-indigo-600 px-1.5 py-0.5 text-white">
          {labelFor(current)} / {elevator.max_floor_label || `${maxFloor}F`}
        </span>
      </div>

      <div role="group" aria-label="階を選ぶ" className="mt-2 flex flex-wrap gap-1.5">
        {floors.map(item => {
          const active = item.floor === current.floor;
          const label = labelFor(item);
          return (
            <button
              key={item.floor}
              type="button"
              disabled={active || !onOptionSelect}
              aria-current={active ? 'step' : undefined}
              title={item.summary || item.title || label}
              onClick={() => sendFloor(item)}
              className={`rounded-lg border px-2.5 py-1 font-medium ${
                active
                  ? 'border-indigo-600 bg-indigo-600 text-white'
                  : 'border-indigo-200 bg-white text-indigo-700 hover:bg-indigo-100 dark:border-indigo-700 dark:bg-slate-900 dark:text-indigo-200'
              }`}
            >
              {label}
              {item.title && item.title !== label ? ` ${item.title}` : ''}
            </button>
          );
        })}
      </div>

      {current.summary && (
        <p className="mt-2 text-slate-700 dark:text-slate-300">{current.summary}</p>
      )}

      {(previous || next) && (
        <div className="mt-2 flex flex-wrap gap-2 border-t border-indigo-200 pt-2 dark:border-indigo-800">
          {previous && (
            <button
              type="button"
              disabled={!onOptionSelect}
              onClick={() => sendFloor(previous)}
              className="rounded-md border border-indigo-300 px-2 py-1 disabled:opacity-50"
            >
              前の階（{labelFor(previous)}）
            </button>
          )}
          {next && (
            <button
              type="button"
              disabled={!onOptionSelect}
              onClick={() => sendFloor(next)}
              className="rounded-md bg-indigo-600 px-2 py-1 text-white disabled:opacity-50"
            >
              次の階（{labelFor(next)}）
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default ElevatorNavigatorBlock;
