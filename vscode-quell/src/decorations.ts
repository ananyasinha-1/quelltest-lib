import * as vscode from 'vscode';
import { FileScore } from './scoreProvider';

/** Inline text appended to function definition lines. */
const _gradeColor: Record<string, string> = {
  A: '#4c1',
  B: '#dfb317',
  C: '#e05d44',
  F: '#e05d44',
};

function _makeDecorationType(color: string) {
  return vscode.window.createTextEditorDecorationType({
    after: {
      color,
      fontStyle: 'italic',
      margin: '0 0 0 2em',
    },
  });
}

const _decorationTypes: Record<string, vscode.TextEditorDecorationType> = {
  A: _makeDecorationType('#4c166e'),
  B: _makeDecorationType('#dfb31799'),
  C: _makeDecorationType('#e05d4499'),
  F: _makeDecorationType('#e05d44'),
};

export class DecorationManager {
  private _activeDecorations: vscode.TextEditorDecorationType[] = [];

  apply(
    editor: vscode.TextEditor | undefined,
    fileScore: FileScore,
    threshold: number
  ): void {
    if (!editor) return;
    this.clear(editor);

    const config = vscode.workspace.getConfiguration('quell');
    if (!config.get<boolean>('showInlineDecorations', true)) return;

    const grade = fileScore.grade as keyof typeof _decorationTypes;
    const decorationType = _decorationTypes[grade] ?? _decorationTypes['F'];
    const score = fileScore.percentage;
    const label = ` quell ${score}% (${grade})`;

    const decorations: vscode.DecorationOptions[] = [];
    const doc = editor.document;

    for (let i = 0; i < doc.lineCount; i++) {
      const line = doc.lineAt(i);
      const text = line.text;
      // Match Python function and class definitions
      if (/^\s*(?:async\s+)?def\s+\w+|^\s*class\s+\w+/.test(text)) {
        const pos = new vscode.Position(i, text.length);
        decorations.push({
          range: new vscode.Range(pos, pos),
          renderOptions: { after: { contentText: label } },
        });
      }
    }

    editor.setDecorations(decorationType, decorations);
    this._activeDecorations.push(decorationType);
  }

  clear(editor: vscode.TextEditor): void {
    for (const dt of this._activeDecorations) {
      editor.setDecorations(dt, []);
    }
    this._activeDecorations = [];
  }
}
