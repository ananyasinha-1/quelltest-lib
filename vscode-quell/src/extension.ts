import * as vscode from 'vscode';
import * as path from 'path';
import { ScoreProvider } from './scoreProvider';
import { DecorationManager } from './decorations';

let statusBar: vscode.StatusBarItem;
const scoreProvider = new ScoreProvider();
const decorations = new DecorationManager();

export function activate(context: vscode.ExtensionContext): void {
  // Status bar item — right side, shows current file's mutation score
  statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBar.command = 'quell.showScore';
  statusBar.tooltip = 'Quell Mutation Score — click to refresh';
  context.subscriptions.push(statusBar);

  // ── Commands ──────────────────────────────────────────────────────────────

  context.subscriptions.push(
    vscode.commands.registerCommand('quell.showScore', async () => {
      await _refreshAndDecorate();
    }),

    vscode.commands.registerCommand('quell.repairFile', async () => {
      const root = _workspaceRoot();
      if (!root) return;
      const terminal = vscode.window.createTerminal({ name: 'Quell Repair', cwd: root });
      terminal.sendText('quell repair tests/');
      terminal.show();
    }),

    vscode.commands.registerCommand('quell.fixAll', async () => {
      const root = _workspaceRoot();
      if (!root) return;
      const terminal = vscode.window.createTerminal({ name: 'Quell Fix', cwd: root });
      terminal.sendText('quell auto');
      terminal.show();
    }),

    vscode.commands.registerCommand('quell.runScan', async () => {
      const root = _workspaceRoot();
      if (!root) return;
      const terminal = vscode.window.createTerminal({ name: 'Quell Scan', cwd: root });
      terminal.sendText('quell scan');
      terminal.show();
    })
  );

  // ── Auto-refresh on save ──────────────────────────────────────────────────
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument(async (doc) => {
      const config = vscode.workspace.getConfiguration('quell');
      if (!config.get<boolean>('autoRefresh', true)) return;
      if (doc.languageId !== 'python') return;

      const root = _workspaceRoot();
      if (!root) return;
      scoreProvider.invalidate(root);
      await _refreshAndDecorate();
    }),

    // Re-decorate when switching editors
    vscode.window.onDidChangeActiveTextEditor(async (editor) => {
      if (editor?.document.languageId === 'python') {
        await _refreshAndDecorate(editor);
      } else {
        statusBar.hide();
      }
    })
  );

  // Initial load if a Python file is already open
  if (vscode.window.activeTextEditor?.document.languageId === 'python') {
    _refreshAndDecorate().catch(() => void 0);
  }
}

export function deactivate(): void {
  statusBar?.dispose();
}

// ── Helpers ───────────────────────────────────────────────────────────────

async function _refreshAndDecorate(
  editor?: vscode.TextEditor
): Promise<void> {
  const activeEditor = editor ?? vscode.window.activeTextEditor;
  if (!activeEditor || activeEditor.document.languageId !== 'python') return;

  const root = _workspaceRoot();
  if (!root) return;

  const projectScore = await scoreProvider.getProjectScore(root);
  if (!projectScore) {
    statusBar.text = '$(testing-skipped-icon) Quell: no data';
    statusBar.show();
    return;
  }

  const filePath = activeEditor.document.uri.fsPath;
  const fileScore = scoreProvider.getFileScore(projectScore, filePath);
  const config = vscode.workspace.getConfiguration('quell');
  const threshold = config.get<number>('threshold', 0.6);

  if (fileScore) {
    const icon = fileScore.score >= threshold
      ? '$(testing-passed-icon)'
      : '$(testing-failed-icon)';
    statusBar.text = `${icon} Quell ${fileScore.percentage}% (${fileScore.grade})`;
    statusBar.backgroundColor =
      fileScore.score < threshold
        ? new vscode.ThemeColor('statusBarItem.warningBackground')
        : undefined;
    decorations.apply(activeEditor, fileScore, threshold);
  } else {
    const pct = projectScore.percentage;
    const icon = pct >= threshold * 100
      ? '$(testing-passed-icon)'
      : '$(testing-failed-icon)';
    statusBar.text = `${icon} Quell ${pct}%`;
    statusBar.backgroundColor = undefined;
    decorations.clear(activeEditor);
  }

  statusBar.show();
}

function _workspaceRoot(): string | undefined {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
}
