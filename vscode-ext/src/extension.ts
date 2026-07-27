import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';

export function activate(context: vscode.ExtensionContext) {
    const provider = new MyAiSidebarProvider(context);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('my-ai-sidebar.view', provider)
    );

    let disposable = vscode.commands.registerCommand('my-ai-sidebar.open', () => {
        vscode.commands.executeCommand('my-ai-sidebar.view.focus');
    });
    context.subscriptions.push(disposable);
}

class MyAiSidebarProvider implements vscode.WebviewViewProvider {
    // contextを受け取るようにコンストラクタを追加
    constructor(private readonly _context: vscode.ExtensionContext) {}

    resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken,
    ) {
        // Webviewのセキュリティ設定（distフォルダの中身だけ読み込み許可）
        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [vscode.Uri.file(path.join(this._context.extensionPath, 'dist'))]
        };

        // 配置した dist/index.html を読み込む
        const htmlPath = path.join(this._context.extensionPath, 'dist', 'index.html');
        let html = fs.readFileSync(htmlPath, 'utf-8');

        // Viteが書き出した相対パス(./assets/...)を、VS Code専用のパスに変換する
        const distUri = webviewView.webview.asWebviewUri(vscode.Uri.file(path.join(this._context.extensionPath, 'dist')));
        html = html.replace(/(href|src)=".\//g, `$1="${distUri}/`);

        webviewView.webview.html = html;
    }
}

export function deactivate() {}