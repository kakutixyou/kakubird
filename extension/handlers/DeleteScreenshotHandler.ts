// handlers/DeleteScreenshotHandler.ts

import * as vscode from "vscode";
import { ScreenshotService } from "../services/ScreenshotService";

export class DeleteScreenshotHandler {
  constructor(
    private readonly context: vscode.ExtensionContext,
    private readonly webview: vscode.Webview
  ) {}

  async execute(message: { id: string }) {
    try {
      await ScreenshotService.delete(
        this.context.globalStorageUri,
        message.id
      );

      this.webview.postMessage({
        command: "screenshotDeleted",
        id: message.id,
      });
    } catch (error) {
      this.webview.postMessage({
        command: "screenshotDeleteFailed",
        id: message.id,
        error: error instanceof Error ? error.message : String(error),
      });
    }
  }
}