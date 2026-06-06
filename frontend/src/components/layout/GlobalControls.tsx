import { BackendState } from '@/api/types';
import { api } from '@/api/client';
import { useQueryClient } from '@tanstack/react-query';
import { ChevronDown } from 'lucide-react';

interface GlobalControlsProps {
  state: BackendState;
}

export function GlobalControls({ state }: GlobalControlsProps) {
  const queryClient = useQueryClient();
  const settings = state.session.global_settings;

  // Find current provider info to get models
  const currentProvider = state.providers.find(p => p.id === settings.provider_id);

  const handleProviderChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    await api.updateGlobalSettings({ provider_id: e.target.value });
    queryClient.invalidateQueries({ queryKey: ['state'] });
  };

  const handleModelChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    await api.updateGlobalSettings({ model_id: e.target.value });
    queryClient.invalidateQueries({ queryKey: ['state'] });
  };

  return (
    <div className="flex items-center gap-3">
      {/* Provider Selector */}
      <div className="relative">
        <select
          value={settings.provider_id}
          onChange={handleProviderChange}
          className="appearance-none bg-surface border border-white/10 rounded-md py-1.5 pl-3 pr-8 text-xs font-medium focus:ring-1 focus:ring-primary outline-none cursor-pointer hover:bg-white/5 transition-colors"
        >
          {state.providers.map(p => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
        <ChevronDown size={12} className="absolute right-2 top-1/2 -translate-y-1/2 opacity-50 pointer-events-none" />
      </div>

      <span className="text-white/20">/</span>

      {/* Model Selector */}
      <div className="relative">
        <select
          value={settings.model_id}
          onChange={handleModelChange}
          className="appearance-none bg-surface border border-white/10 rounded-md py-1.5 pl-3 pr-8 text-xs font-medium focus:ring-1 focus:ring-primary outline-none cursor-pointer hover:bg-white/5 transition-colors max-w-[200px] truncate"
        >
          {currentProvider?.models.map(m => (
            <option key={m.id} value={m.id}>{m.name}</option>
          ))}
        </select>
        <ChevronDown size={12} className="absolute right-2 top-1/2 -translate-y-1/2 opacity-50 pointer-events-none" />
      </div>

      {/* Stats Pill */}
      <div className="ml-4 px-3 py-1.5 rounded-full bg-surface/50 border border-white/5 text-[10px] font-mono text-text-muted">
         RPM: {settings.rate_limit_rpm}
      </div>
    </div>
  );
}