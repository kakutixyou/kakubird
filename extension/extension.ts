import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

/**
 * extension.ts
 *
 * 機能:
 * - Webview を開くコマンド aiChat.openPanel
 * - webview からのメッセージ: saveScreenshot, deleteScreenshot, saveMemory, requestIndex, insertCode
 * - context.globalStorageUri を使って screenshots/ および memories/ を管理
 *
 * 注意:
 * - frontend のビルド成果物 (index.html, assets) を extension の media フォルダに置いてください。
 *   例: vscode-extension/media/index.html, /media/assets/...
 */

export function activate(context: vscode.ExtensionContext) {
  console.log('ai-chat extension activated');

  const openCmd = vscode.commands.registerCommand('aiChat.openPanel', () => {
    AiChatPanel.createOrShow(context);
  });

  context.subscriptions.push(openCmd);
}

export function deactivate() {
  // no-op
}

class AiChatPanel {
  public static currentPanel: AiChatPanel | undefined;
  private readonly panel: vscode.WebviewPanel;
  private readonly context: vscode.ExtensionContext;
  private disposables: vscode.Disposable[] = [];

  private constructor(context: vscode.ExtensionContext, panel: vscode.WebviewPanel) {
    this.context = context;
    this.panel = panel;

    // Set the webview content
    this.panel.webview.html = this.getWebviewContent();

    // Handle messages from the webview
    this.panel.webview.onDidReceiveMessage(this.onMessage.bind(this), null, this.disposables);

    // Dispose
    this.panel.onDidDispose(() => this.dispose(), null, this.disposables);
  }

  public static createOrShow(context: vscode.ExtensionContext) {
    const column = vscode.window.activeTextEditor ? vscode.window.activeTextEditor.viewColumn : vscode.ViewColumn.One;

    if (AiChatPanel.currentPanel) {
      AiChatPanel.currentPanel.panel.reveal(column);
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      'aiChat',
      'AI Chat',
      column,
      {
        enableScripts: true,
        localResourceRoots: [
          vscode.Uri.joinPath(context.extensionUri, 'media'),
          context.globalStorageUri
        ]
      }
    );

    AiChatPanel.currentPanel = new AiChatPanel(context, panel);
  }

  private dispose() {
    AiChatPanel.currentPanel = undefined;

    // clean up disposables
    while (this.disposables.length) {
      const d = this.disposables.pop();
      if (d) d.dispose();
    }
  }

  // Load the webview index.html from media/index.html and rewrite resource paths to webview URIs
  private getWebviewContent(): string {
    const mediaPath = path.join(this.context.extensionPath, 'media');
    const indexPath = path.join(mediaPath, 'index.html');

    if (!fs.existsSync(indexPath)) {
      // Fallback minimal page
      return `<html><body>
        <h2>AI Chat</h2>
        <p>Place your frontend build into the extension's <code>media/</code> folder.</p>
        <p>Expected: ${indexPath}</p>
      </body></html>`;
    }

    let html = fs.readFileSync(indexPath, 'utf8');

    // Replace static references to be accessible to webview via webview.asWebviewUri
    // We assume index.html references assets relatively (e.g. /assets/main.js). We'll transform a base placeholder __RESOURCE_BASE__
    // To enable this, you can set in your built index.html a placeholder like: <base href="__RESOURCE_BASE__">
    // Here we compute the base URI:
    const baseUri = this.panel.webview.asWebviewUri(vscode.Uri.joinPath(this.context.extensionUri, 'media'));
    // Replace a placeholder if exists
    html = html.replace(/__RESOURCE_BASE__/g, String(baseUri));

    return html;
  }

  // Handle incoming messages from webview
  private async onMessage(msg: any) {
    try {
      switch (msg.command) {
        case 'saveScreenshot':
          await this.handleSaveScreenshot(msg);
          break;
        case 'deleteScreenshot':
          await this.handleDeleteScreenshot(msg);
          break;
        case 'requestIndex':
          await this.handleRequestIndex();
          break;
        case 'saveMemory':
          await this.handleSaveMemory(msg);
          break;
        case 'insertCode':
          await this.handleInsertCode(msg);
          break;
        default:
          console.warn('Unknown command from webview:', msg.command);
      }
    } catch (e) {
      console.error('onMessage error:', e);
      // Optionally reply with failure
      if (msg && msg.tempId) {
        this.panel.webview.postMessage({ command: `${msg.command}Failed`, tempId: msg.tempId, error: String(e) });
      }
    }
  }

  /* ---------- Handlers ---------- */

  private async handleSaveScreenshot(msg: { filename: string, data: string, mime?: string, tempId?: string }) {
    const screenshotsDir = vscode.Uri.joinPath(this.context.globalStorageUri, 'screenshots');
    await vscode.workspace.fs.createDirectory(screenshotsDir);

    // sanitize and ensure unique filename
    const safeName = this.uniqueFilename(msg.filename || `screenshot-${Date.now()}.png`, screenshotsDir);

    const fileUri = vscode.Uri.joinPath(screenshotsDir, safeName);
    const buffer = Buffer.from(msg.data, 'base64');

    await vscode.workspace.fs.writeFile(fileUri, buffer);

    // update index.json
    const indexUri = vscode.Uri.joinPath(screenshotsDir, 'index.json');
    let index: any[] = [];
    try {
      const bytes = await vscode.workspace.fs.readFile(indexUri);
      index = JSON.parse(Buffer.from(bytes).toString('utf8') || '[]');
    } catch (e) {
      index = [];
    }

    const metadata = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2,8)}`,
      filename: safeName,
      uri: fileUri.toString(),
      mime: msg.mime || 'image/png',
      createdAt: new Date().toISOString()
    };

    // prepend newest
    index.unshift(metadata);
    await vscode.workspace.fs.writeFile(indexUri, Buffer.from(JSON.stringify(index, null, 2), 'utf8'));

    // Reply to webview
    this.panel.webview.postMessage({ command: 'screenshotSaved', metadata, tempId: msg.tempId });
  }

  private async handleDeleteScreenshot(msg: { id: string }) {
    const screenshotsDir = vscode.Uri.joinPath(this.context.globalStorageUri, 'screenshots');
    const indexUri = vscode.Uri.joinPath(screenshotsDir, 'index.json');
    try {
      const bytes = await vscode.workspace.fs.readFile(indexUri);
      const index = JSON.parse(Buffer.from(bytes).toString('utf8') || '[]') as any[];
      const item = index.find(i => i.id === msg.id);
      if (item) {
        // delete file if exists
        try {
          const fileUri = vscode.Uri.parse(item.uri);
          await vscode.workspace.fs.delete(fileUri);
        } catch (e) {
          // ignore file delete errors
        }
        // remove from index
        const newIndex = index.filter(i => i.id !== msg.id);
        await vscode.workspace.fs.writeFile(indexUri, Buffer.from(JSON.stringify(newIndex, null, 2), 'utf8'));
      }
      // Optionally inform webview
      this.panel.webview.postMessage({ command: 'screenshotDeleted', id: msg.id });
    } catch (e) {
      // index not found or other error
      this.panel.webview.postMessage({ command: 'screenshotDeleteFailed', id: msg.id, error: String(e) });
    }
  }

  private async handleRequestIndex() {
    // screenshots
    const screenshotsDir = vscode.Uri.joinPath(this.context.globalStorageUri, 'screenshots');
    const indexUri = vscode.Uri.joinPath(screenshotsDir, 'index.json');
    let screenshots: any[] = [];
    try {
      const bytes = await vscode.workspace.fs.readFile(indexUri);
      screenshots = JSON.parse(Buffer.from(bytes).toString('utf8') || '[]');
    } catch (e) {
      screenshots = [];
    }

    // memories: load all files under globalStorageUri/memories/
    const memoriesDir = vscode.Uri.joinPath(this.context.globalStorageUri, 'memories');
    let memoriesMap: Record<string, any> = {};
    try {
      await vscode.workspace.fs.createDirectory(memoriesDir);
      const entries = await vscode.workspace.fs.readDirectory(memoriesDir); // [ [name, FileType], ... ]
      for (const [name, type] of entries) {
        if (type === vscode.FileType.File && name.endsWith('.json')) {
          try {
            const uri = vscode.Uri.joinPath(memoriesDir, name);
            const bytes = await vscode.workspace.fs.readFile(uri);
            const content = JSON.parse(Buffer.from(bytes).toString('utf8') || '{}');
            const key = name.replace(/\.json$/, '');
            memoriesMap[key] = content;
          } catch (e) {
            console.warn('read memory file error', name, e);
          }
        }
      }
    } catch (e) {
      memoriesMap = {};
    }

    // send both
    this.panel.webview.postMessage({ command: 'screenshotIndex', list: screenshots });
    this.panel.webview.postMessage({ command: 'memoryIndex', map: memoriesMap });
  }

  private async handleSaveMemory(msg: { type: string, payload: any, tempId?: string }) {
    const memoriesDir = vscode.Uri.joinPath(this.context.globalStorageUri, 'memories');
    await vscode.workspace.fs.createDirectory(memoriesDir);

    const filename = `${msg.type}.json`;
    const fileUri = vscode.Uri.joinPath(memoriesDir, filename);

    // If file exists, merge or overwrite depending on your policy. Here we overwrite/replace with payload metadata wrapper.
    const metadata = {
      id: `${msg.type}-${Date.now()}`,
      type: msg.type,
      payload: msg.payload,
      createdAt: new Date().toISOString()
    };

    await vscode.workspace.fs.writeFile(fileUri, Buffer.from(JSON.stringify(metadata, null, 2), 'utf8'));
    // reply to webview
    this.panel.webview.postMessage({ command: 'memorySaved', type: msg.type, metadata, tempId: msg.tempId });
  }

  private async handleInsertCode(msg: { code: string }) {
    const editor = vscode.window.activeTextEditor;
    if (editor) {
      await editor.edit(editBuilder => {
        editBuilder.insert(editor.selection.active, msg.code);
      });
      // Optionally move cursor or format
      this.panel.webview.postMessage({ command: 'insertCodeDone' });
    } else {
      // Fallback: copy to clipboard
      await vscode.env.clipboard.writeText(msg.code);
      this.panel.webview.postMessage({ command: 'insertCodeCopied' });
    }
  }

  /* ---------- Utilities ---------- */

  // ensure unique filename within screenshotsDir, returns filename string
  private uniqueFilename(name: string, screenshotsDir: vscode.Uri): string {
    // sanitize: remove path separators
    const base = path.basename(name).replace(/[^a-zA-Z0-9._-]/g, '_');
    // if not present, return base
    // check existing files in dir (sync read)
    try {
      const indexUri = vscode.Uri.joinPath(screenshotsDir, 'index.json');
      const bytes = fs.existsSync(indexUri.fsPath) ? fs.readFileSync(indexUri.fsPath, 'utf8') : null;
      if (!bytes) {
        return base;
      }
      const list = JSON.parse(bytes || '[]') as any[];
      const exists = list.find(i => i.filename === base);
      if (!exists) return base;
      // append counter
      const ext = path.extname(base);
      const nameOnly = base.slice(0, base.length - ext.length);
      let i = 1;
      while (true) {
        const candidate = `${nameOnly}-${i}${ext}`;
        if (!list.find(it => it.filename === candidate)) return candidate;
        i++;
      }
    } catch (e) {
      return base;
    }
  }
}