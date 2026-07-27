// blockRegistry.js

import DatabaseSchemaBlock from '../components/blocks/DatabaseSchemaBlock';
import FileDownloadBlock from '../components/blocks/FileDownloadBlock';

export const blockRegistry = {
  DatabaseSchema: DatabaseSchemaBlock,
  FileDownload: FileDownloadBlock,
};