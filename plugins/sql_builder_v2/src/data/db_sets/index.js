// src/data/db_sets/index.js

import { corporateExamples } from './corporate';
import { cafeExamples } from './cafe';
import { Examples } from './example';
import { schoolExamples } from './school';
import { ecommerceExamples } from './ecommerce';
import { gameGuildExamples } from './game_guild';
import { hospitalExamples } from './hospital';

// 各データセットの default export も必要なら利用可能
export { default as corporate } from './corporate';
export { default as cafe } from './cafe';
export { default as example } from './example';
export { default as school } from './school';
export { default as ecommerce } from './ecommerce';
export { default as gameGuild } from './game_guild';
export { default as hospital } from './hospital';

// SQLサンプルをすべてまとめる
export const allExamples = [
  ...Examples,
  ...corporateExamples,
  ...cafeExamples,
  ...schoolExamples,
  ...ecommerceExamples,
  ...gameGuildExamples,
  ...hospitalExamples
];

// 全データセットを配列化（AI用）
export const allDatasets = [
  corporate,
  cafe,
  example,
  school,
  ecommerce,
  gameGuild,
  hospital
];

// データセットIDで検索しやすいマップ
export const datasetMap = {
  corporate,
  cafe,
  example,
  school,
  ecommerce,
  game_guild: gameGuild,
  hospital
};