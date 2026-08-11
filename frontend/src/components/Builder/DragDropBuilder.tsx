// DragDropBuilder.tsx
import { DragDropContext, Droppable, Draggable, DropResult } from '@hello-pangea/dnd';
import { useBuilderStore } from '../../store/builderStore';
import ComponentPalette from './ComponentPalette';
import Canvas from './Canvas';
import PropertyPanel from './PropertyPanel';
import React from 'react';
export default function DragDropBuilder() {
  const { reorderComponents, addComponent, selectedComponentId } = useBuilderStore();

  function onDragEnd(result: DropResult) {
    if (!result.destination) return;

    // Dragging from palette to canvas
    if (result.source.droppableId === 'palette' && result.destination.droppableId === 'canvas') {
      const type = result.draggableId as any;
      addComponent(type);
      return;
    }

    // Reordering within canvas
    if (result.source.droppableId === 'canvas' && result.destination.droppableId === 'canvas') {
      reorderComponents(result.source.index, result.destination.index);
    }
  }

  return (
    <DragDropContext onDragEnd={onDragEnd}>
      <div className="flex h-full">
        <ComponentPalette />
        <Canvas />
        {selectedComponentId && <PropertyPanel />}
      </div>
    </DragDropContext>
  );
}
