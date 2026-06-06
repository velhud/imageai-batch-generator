import { BackendState } from '@/api/types';
import { api } from '@/api/client';
import { Button } from '@/components/common/Button';
import { useQueryClient } from '@tanstack/react-query';
import { CheckSquare, Square, Trash2, Play, Download, PlusSquare, StopCircle } from 'lucide-react';

export function Footer({ state }: { state: BackendState }) {
  const queryClient = useQueryClient();
  const rows = state.session.rows;
  const selectedRows = rows.filter(r => r.selected);
  const selectedIds = selectedRows.map(r => r.id);
  const isGenerating = rows.some(r => r.status === 'Generating' || r.status === 'Queued');

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['state'] });

  const handleSelectAll = async () => {
    for (const r of rows) await api.updateRow(r.id, { selected: true });
    refresh();
  };

  const handleClearSelection = async () => {
    for (const r of rows) await api.updateRow(r.id, { selected: false });
    refresh();
  };

  const handleSelectPending = async () => {
    for (const r of rows) await api.updateRow(r.id, { selected: r.status !== 'Completed' });
    refresh();
  };

  const handleSelectNoImage = async () => {
    for (const r of rows) await api.updateRow(r.id, { selected: r.images.length === 0 });
    refresh();
  };

  const handleDeleteSelected = async () => {
    if (selectedIds.length && confirm(`Delete ${selectedIds.length} rows?`)) {
        await api.deleteRows(selectedIds);
        refresh();
    }
  };

  const handleAddN = async () => {
    const countStr = prompt("How many rows?", "10");
    if (countStr) {
        const n = parseInt(countStr, 10);
        if (n > 0) {
            const prompts = Array(n).fill("");
            await api.addRows(prompts);
            refresh();
        }
    }
  };

  const handleExportSelected = async () => {
    if (!selectedIds.length) return;
    const res = await api.selectFolder();
    if (res.path) {
        await api.export(selectedIds, res.path);
    }
  };

  const handleGenerateSelected = async () => {
    if (!selectedIds.length) return;
    await api.generateRows(selectedIds);
    refresh();
  };

  const handleGenerateAll = async () => {
    const ids = rows.map(r => r.id);
    if (!ids.length) return;
    if (confirm(`Generate all ${ids.length} rows?`)) {
        await api.generateRows(ids);
        refresh();
    }
  };

  const handleStopAll = async () => {
    await api.stopAll();
    refresh();
  };

  const handleDeleteAll = async () => {
    if (!rows.length) return;
    if (confirm("Delete ALL rows in session? This cannot be undone.")) {
        const ids = rows.map(r => r.id);
        await api.deleteRows(ids);
        refresh();
    }
  };

  return (
    <footer className="h-16 bg-surface border-t border-white/5 flex items-center justify-between px-6 shrink-0 z-10 text-xs">
        <div className="flex items-center gap-3">
            <span className="text-text-muted font-mono mr-2 bg-white/5 px-2 py-1 rounded">{selectedIds.length} selected</span>
            <Button size="sm" variant="ghost" onClick={handleSelectAll} title="Select All"><CheckSquare size={14}/></Button>
            <Button size="sm" variant="ghost" onClick={handleClearSelection} title="Clear Selection"><Square size={14}/></Button>
            <Button size="sm" variant="ghost" onClick={handleSelectNoImage}>No Img</Button>
            <Button size="sm" variant="ghost" onClick={handleSelectPending}>Pending</Button>
            <div className="h-4 w-px bg-white/10 mx-1" />
            <Button size="sm" variant="secondary" onClick={handleAddN}>
                <PlusSquare size={14} className="mr-2" /> Add N...
            </Button>
            <Button size="sm" variant="danger" onClick={handleDeleteAll} title="Delete All Rows">
                Delete All
            </Button>
        </div>

        <div className="flex items-center gap-3">
            {isGenerating ? (
                <Button size="sm" variant="danger" onClick={handleStopAll} className="px-6">
                    <StopCircle size={16} className="mr-2" /> Stop All
                </Button>
            ) : (
                <Button size="sm" onClick={handleGenerateAll} className="px-4">
                    <Play size={16} className="mr-2" /> Generate All
                </Button>
            )}

            <div className="h-6 w-px bg-white/10 mx-2" />

            <Button size="sm" variant="secondary" onClick={handleExportSelected} disabled={!selectedIds.length}>
                <Download size={14} className="mr-2" /> Export
            </Button>
            <Button size="sm" variant="danger" onClick={handleDeleteSelected} disabled={!selectedIds.length}>
                <Trash2 size={14} className="mr-2" /> Delete
            </Button>
            <Button size="sm" onClick={handleGenerateSelected} disabled={!selectedIds.length}>
                <Play size={14} className="mr-2" /> Gen Selected
            </Button>
        </div>
    </footer>
  );
}
