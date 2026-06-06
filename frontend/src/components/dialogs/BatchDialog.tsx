import { useState } from 'react';
import { api } from '@/api/client';
import { Button } from '@/components/common/Button';
import { useQueryClient } from '@tanstack/react-query';
import { X, FileSpreadsheet, List as ListIcon, FileJson, Hash } from 'lucide-react';

interface BatchDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

type BatchMode = 'lines' | 'numbered' | 'json_array' | 'json_lines' | 'csv';

export function BatchDialog({ isOpen, onClose }: BatchDialogProps) {
  const [text, setText] = useState("");
  const [mode, setMode] = useState<BatchMode>('lines');
  const [promptField, setPromptField] = useState("prompt");
  const [csvColumn, setCsvColumn] = useState("prompt");
  const [preview, setPreview] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  
  const queryClient = useQueryClient();

  if (!isOpen) return null;

  const parse = () => {
    setError(null);
    const lines = text.split('\n').filter(l => l.trim());
    let prompts: string[] = [];

    try {
      if (mode === 'lines') {
        prompts = lines;
      } else if (mode === 'numbered') {
        prompts = lines.map(l => l.replace(/^\s*\d+\s*[\.\)\-]\s*/, '')).filter(Boolean);
      } else if (mode === 'json_array') {
        const data = JSON.parse(text);
        if (Array.isArray(data)) {
          prompts = data.map((item: any) => typeof item === 'string' ? item : item[promptField]);
        } else {
          throw new Error("Not a JSON array");
        }
      } else if (mode === 'json_lines') {
        prompts = lines.map(l => JSON.parse(l)[promptField]);
      } else if (mode === 'csv') {
        const colIndex = parseInt(csvColumn, 10);
        const useIndex = !isNaN(colIndex);
        
        prompts = lines.map((l) => {
            const cols = l.split(',');
            if (useIndex) return cols[colIndex];
            return cols[0];
        });
      }
      setPreview(prompts.filter(Boolean));
    } catch (e: any) {
      setError(e.message || "Parse error");
      setPreview([]);
    }
  };

  const handleImport = async () => {
    if (preview.length === 0) parse();
    const finalPrompts = preview.length > 0 ? preview : text.split('\n'); 
    
    await api.addRows(finalPrompts);
    queryClient.invalidateQueries({ queryKey: ['state'] });
    setText("");
    setPreview([]);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm animate-in fade-in">
      <div className="w-full max-w-4xl bg-surface border border-white/10 rounded-xl shadow-2xl flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between p-4 border-b border-white/10 bg-white/5">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <FileSpreadsheet size={18} className="text-primary" /> 
            Batch Input
          </h2>
          <button onClick={onClose}><X size={20} className="text-text-muted hover:text-white" /></button>
        </div>

        <div className="flex-1 flex overflow-hidden">
            <div className="w-64 border-r border-white/10 p-4 space-y-6 bg-black/20 overflow-y-auto">
                <div className="space-y-2">
                    <label className="text-xs text-text-muted font-bold uppercase">Parse Mode</label>
                    <div className="flex flex-col gap-1">
                        {[
                            { id: 'lines', label: 'One per line', icon: ListIcon },
                            { id: 'numbered', label: 'Numbered List', icon: Hash },
                            { id: 'json_array', label: 'JSON Array', icon: FileJson },
                            { id: 'json_lines', label: 'JSON Lines', icon: FileJson },
                            { id: 'csv', label: 'CSV', icon: FileSpreadsheet },
                        ].map((m) => (
                            <button
                                key={m.id}
                                onClick={() => setMode(m.id as BatchMode)}
                                className={`flex items-center gap-2 px-3 py-2 rounded text-sm text-left transition-colors ${mode === m.id ? 'bg-primary/20 text-primary border border-primary/20' : 'hover:bg-white/5 text-text-muted'}`}
                            >
                                <m.icon size={14} /> {m.label}
                            </button>
                        ))}
                    </div>
                </div>

                {(mode === 'json_array' || mode === 'json_lines') && (
                    <div className="space-y-1">
                        <label className="text-xs text-text-muted">Field Name</label>
                        <input className="w-full bg-surface border border-white/10 rounded p-2 text-sm" value={promptField} onChange={e => setPromptField(e.target.value)} />
                    </div>
                )}

                {mode === 'csv' && (
                    <div className="space-y-1">
                        <label className="text-xs text-text-muted">Column (Name or Index)</label>
                        <input className="w-full bg-surface border border-white/10 rounded p-2 text-sm" value={csvColumn} onChange={e => setCsvColumn(e.target.value)} />
                    </div>
                )}

                <Button variant="secondary" onClick={parse} className="w-full">Update Preview</Button>
            </div>

            <div className="flex-1 flex flex-col min-w-0">
                <div className="flex-1 p-4 flex flex-col gap-4 overflow-hidden">
                    <div className="flex-1 flex flex-col gap-2 min-h-0">
                        <label className="text-xs text-text-muted">Input Data</label>
                        <textarea 
                            value={text}
                            onChange={e => setText(e.target.value)}
                            className="flex-1 bg-black/30 border border-white/10 rounded p-3 font-mono text-sm resize-none focus:ring-1 focus:ring-primary outline-none"
                            placeholder="Paste text here..."
                        />
                    </div>
                    
                    <div className="h-1/3 flex flex-col gap-2 min-h-0">
                        <div className="flex justify-between items-center">
                            <label className="text-xs text-text-muted">Preview ({preview.length} prompts)</label>
                            {error && <span className="text-xs text-red-400">{error}</span>}
                        </div>
                        <div className="flex-1 bg-black/50 border border-white/10 rounded p-2 overflow-y-auto font-mono text-xs text-text-muted">
                            {preview.length === 0 ? (
                                <div className="h-full flex items-center justify-center opacity-30">No preview generated</div>
                            ) : (
                                <ul className="space-y-1">
                                    {preview.map((p, i) => (
                                        <li key={i} className="flex gap-2">
                                            <span className="opacity-30 w-6 text-right">{i+1}.</span>
                                            <span className="text-text-main">{p}</span>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div className="p-4 border-t border-white/10 bg-white/5 flex justify-end gap-3">
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button onClick={handleImport} disabled={preview.length === 0}>
            Import {preview.length} Rows
          </Button>
        </div>
      </div>
    </div>
  );
}
