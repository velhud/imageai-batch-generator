import { type ReactNode } from 'react';
import { BackendState } from '@/api/types';
import { X, Activity, CheckCircle, AlertTriangle, Clock, List as ListIcon } from 'lucide-react';

interface StatsDialogProps {
  isOpen: boolean;
  onClose: () => void;
  state: BackendState;
}

export function StatsDialog({ isOpen, onClose, state }: StatsDialogProps) {
  if (!isOpen) return null;
  const { stats } = state;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in">
      <div className="w-full max-w-sm bg-surface border border-white/10 rounded-xl shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-white/10 bg-white/5">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Activity size={18} className="text-primary" /> Session Statistics
          </h2>
          <button onClick={onClose}><X size={20} className="text-text-muted hover:text-white" /></button>
        </div>
        
        <div className="p-6 grid grid-cols-2 gap-4">
            <StatCard label="Total Rows" value={stats.total} icon={<ListIcon />} />
            <StatCard label="Completed" value={stats.completed} icon={<CheckCircle className="text-emerald-500" />} />
            <StatCard label="Errors" value={stats.errors} icon={<AlertTriangle className="text-red-500" />} />
            <StatCard 
                label="Avg Duration" 
                value={`${(stats.average_duration ?? 0).toFixed(2)}s`} 
                icon={<Clock className="text-blue-400" />} 
            />
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, icon }: { label: string; value: number | string; icon: ReactNode }) {
    return (
        <div className="bg-black/20 p-4 rounded-lg border border-white/5 flex flex-col items-center justify-center gap-2">
            <div className="opacity-80">{icon}</div>
            <div className="text-2xl font-bold">{value}</div>
            <div className="text-xs text-text-muted uppercase tracking-wider">{label}</div>
        </div>
    );
}
