// TO(と)/frontend/src/components/Builder/Canvas.tsx
import { Droppable, Draggable } from '@hello-pangea/dnd';
import { useBuilderStore } from '../../store/builderStore';
import { PageComponent } from '../../types';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import clsx from 'clsx';
import React from 'react';
export default function Canvas() {
  const { components, selectedComponentId, selectComponent, removeComponent } = useBuilderStore();

  return (
    <div className="flex-1 bg-gray-100 overflow-auto p-6">
      <div className="max-w-4xl mx-auto">
        <Droppable droppableId="canvas">
          {(provided, snapshot) => (
            <div
              ref={provided.innerRef}
              {...provided.droppableProps}
              className={clsx(
                'min-h-96 bg-white rounded-lg shadow-sm border-2 border-dashed transition-colors',
                snapshot.isDraggingOver ? 'border-blue-400 bg-blue-50' : 'border-gray-200'
              )}
            >
              {components.length === 0 && !snapshot.isDraggingOver && (
                <div className="flex items-center justify-center h-96 text-gray-400">
                  <div className="text-center">
                    <div className="text-4xl mb-2">🎨</div>
                    <p className="text-lg">Drag components here to build your page</p>
                  </div>
                </div>
              )}
              {components.map((component, index) => (
                <Draggable key={component.id} draggableId={component.id} index={index}>
                  {(provided, snapshot) => (
                    <div
                      ref={provided.innerRef}
                      {...provided.draggableProps}
                      className={clsx(
                        'relative group border-2 transition-all',
                        selectedComponentId === component.id ? 'border-blue-500' : 'border-transparent hover:border-blue-300',
                        snapshot.isDragging ? 'shadow-lg opacity-80' : ''
                      )}
                      onClick={() => selectComponent(component.id)}
                    >
                      {/* Drag handle + delete */}
                      <div className="absolute top-1 right-1 hidden group-hover:flex gap-1 z-10">
                        <span
                          {...provided.dragHandleProps}
                          className="bg-blue-500 text-white px-2 py-1 rounded text-xs cursor-grab"
                        >
                          ⠿
                        </span>
                        <button
                          onClick={(e) => { e.stopPropagation(); removeComponent(component.id); }}
                          className="bg-red-500 text-white px-2 py-1 rounded text-xs"
                        >
                          ✕
                        </button>
                      </div>
                      <ComponentRenderer component={component} />
                    </div>
                  )}
                </Draggable>
              ))}
              {provided.placeholder}
            </div>
          )}
        </Droppable>
      </div>
    </div>
  );
}

function ComponentRenderer({ component }: { component: PageComponent }) {
  const { type, props } = component;

  switch (type) {
    case 'header':
      const Tag = (props.level || 'h1') as any;
      return (
        <div className="p-6" style={{ textAlign: props.align || 'left' }}>
          <Tag className={clsx('font-bold', props.level === 'h1' ? 'text-4xl' : props.level === 'h2' ? 'text-3xl' : 'text-2xl')}>
            {props.text || 'Header'}
          </Tag>
        </div>
      );

    case 'text':
      return (
        <div className="p-6" style={{ textAlign: props.align || 'left' }}>
          <p className="text-gray-700">{props.content || 'Text content'}</p>
        </div>
      );

    case 'image':
      return (
        <div className="p-4">
          <img src={props.src} alt={props.alt} style={{ width: props.width || '100%' }} className="rounded" />
        </div>
      );

    case 'button':
      return (
        <div className="p-4" style={{ textAlign: props.align || 'left' }}>
          <a
            href={props.href || '#'}
            className={clsx(
              'inline-block px-6 py-2 rounded font-medium',
              props.variant === 'primary' ? 'bg-blue-600 text-white' : 'border border-blue-600 text-blue-600'
            )}
          >
            {props.label || 'Button'}
          </a>
        </div>
      );

    case 'hero':
      return (
        <div
          className="p-16 text-center text-white"
          style={{ backgroundColor: props.bgColor || '#1d4ed8' }}
        >
          <h1 className="text-5xl font-bold mb-4">{props.title}</h1>
          <p className="text-xl mb-8 opacity-90">{props.subtitle}</p>
          <button className="bg-white text-blue-700 px-8 py-3 rounded-full font-semibold">
            {props.ctaText || 'Get Started'}
          </button>
        </div>
      );

    case 'card':
      return (
        <div className="p-4">
          <div className="border rounded-lg p-6 shadow-sm">
            {props.imageUrl && <img src={props.imageUrl} alt="" className="w-full h-40 object-cover rounded mb-4" />}
            <h3 className="text-xl font-semibold mb-2">{props.title}</h3>
            <p className="text-gray-600">{props.content}</p>
          </div>
        </div>
      );

    case 'table':
      return (
        <div className="p-4 overflow-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr>
                {(props.headers || []).map((h: string, i: number) => (
                  <th key={i} className="border border-gray-200 bg-gray-50 px-4 py-2 text-left text-sm font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(props.rows || []).map((row: string[], ri: number) => (
                <tr key={ri}>
                  {row.map((cell, ci) => (
                    <td key={ci} className="border border-gray-200 px-4 py-2 text-sm">{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );

    case 'form':
      return (
        <div className="p-6">
          <form className="space-y-4">
            {(props.fields || []).map((field: any, i: number) => (
              <div key={i}>
                <label className="block text-sm font-medium text-gray-700 mb-1">{field.label}</label>
                <input type={field.type || 'text'} className="w-full border border-gray-300 rounded px-3 py-2" />
              </div>
            ))}
            <button type="button" className="bg-blue-600 text-white px-6 py-2 rounded">
              {props.submitLabel || 'Submit'}
            </button>
          </form>
        </div>
      );

    case 'chart':
      return (
        <div className="p-4">
          {props.title && <h4 className="font-medium mb-2">{props.title}</h4>}
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={props.data || []}>
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      );

    case 'divider':
      return (
        <div className="px-6 py-2">
          <hr style={{ borderStyle: props.style || 'solid', borderColor: props.color || '#e5e7eb' }} />
        </div>
      );

    case 'spacer':
      return <div style={{ height: `${props.height || 40}px` }} />;

    case 'testimonial':
      return (
        <div className="p-8 bg-gray-50">
          <blockquote className="text-lg italic text-gray-700 mb-4">"{props.quote}"</blockquote>
          <div className="font-semibold">{props.author}</div>
          <div className="text-sm text-gray-500">{props.role}</div>
        </div>
      );

    case 'video':
      return (
        <div className="p-4">
          <div className="relative pt-[56.25%]">
            <iframe
              src={props.url}
              title={props.title}
              className="absolute top-0 left-0 w-full h-full rounded"
              allowFullScreen
            />
          </div>
        </div>
      );

    default:
      return <div className="p-4 text-gray-400">Unknown component: {type}</div>;
  }
}
