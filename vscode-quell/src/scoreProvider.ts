import * as vscode from 'vscode';
import { execFile } from 'child_process';
import { promisify } from 'util';
import * as path from 'path';

const execFileAsync = promisify(execFile);

export interface FileScore {
  path: string;
  score: number;
  percentage: number;
  grade: string;
  total: number;
  killed: number;
  survived: number;
}

export interface ProjectScore {
  total_score: number;
  percentage: number;
  total_mutants: number;
  killed_mutants: number;
  survived_mutants: number;
  files: FileScore[];
}

export class ScoreProvider {
  private _cache: Map<string, ProjectScore> = new Map();

  async getProjectScore(workspaceRoot: string): Promise<ProjectScore | null> {
    const cached = this._cache.get(workspaceRoot);
    if (cached) return cached;
    return this.refreshScore(workspaceRoot);
  }

  async refreshScore(workspaceRoot: string): Promise<ProjectScore | null> {
    const config = vscode.workspace.getConfiguration('quell');
    const pythonPath = config.get<string>('pythonPath') || await this._detectPython();

    try {
      const { stdout } = await execFileAsync(
        pythonPath,
        ['-m', 'quell', 'score', '--format', 'json'],
        { cwd: workspaceRoot, timeout: 30_000 }
      );
      const score: ProjectScore = JSON.parse(stdout);
      this._cache.set(workspaceRoot, score);
      return score;
    } catch {
      // .mutmut-cache not found or quell not installed — fail silently
      return null;
    }
  }

  getFileScore(projectScore: ProjectScore, filePath: string): FileScore | undefined {
    const rel = this._normalise(filePath);
    return projectScore.files.find(f => this._normalise(f.path) === rel);
  }

  invalidate(workspaceRoot: string): void {
    this._cache.delete(workspaceRoot);
  }

  private _normalise(p: string): string {
    return p.replace(/\\/g, '/').toLowerCase();
  }

  private async _detectPython(): Promise<string> {
    const ext = vscode.extensions.getExtension('ms-python.python');
    if (ext) {
      const api = ext.exports;
      const env = api?.environments?.getActiveEnvironmentPath?.();
      if (env?.path) return env.path;
    }
    return 'python';
  }
}
