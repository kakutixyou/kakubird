import React, { useState } from 'react';
import {
  Combobox,
  ComboboxInput,
  ComboboxButton,
  ComboboxOptions,
  ComboboxOption,
} from './ui/combobox'; // さきほど作ったファイルをインポート

const people = ['Wade Cooper', 'Arlene Mccoy', 'Devon Webb'];

export function Example() {
  const [selectedPerson, setSelectedPerson] = useState(people[0]);
  const [query, setQuery] = useState('');

  const filteredPeople = query === ''
    ? people
    : people.filter((person) => person.toLowerCase().includes(query.toLowerCase()));

  return (
    <div className="relative w-64">
      <Combobox value={selectedPerson} onChange={setSelectedPerson}>
        <div className="relative">
          {/* デザイン済みのInput */}
          <ComboboxInput 
            displayValue={(person: string) => person} 
            onChange={(e) => setQuery(e.target.value)} 
          />
          {/* デザイン済みのButton */}
          <ComboboxButton />
        </div>

        {/* デザイン済みのドロップダウン */}
        <ComboboxOptions>
          {filteredPeople.map((person) => (
            <ComboboxOption key={person} value={person}>
              {/* data-[selected]を使って、選択中のアイテムにチェックマークを出すなど、柔軟な内部実装も可能です */}
              {({ selected }) => (
                <span className={selected ? 'font-bold' : 'font-normal'}>
                  {person}
                </span>
              )}
            </ComboboxOption>
          ))}
        </ComboboxOptions>
      </Combobox>
    </div>
  );
}