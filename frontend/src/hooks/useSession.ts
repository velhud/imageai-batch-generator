import { create } from 'zustand';

interface SessionState {
  activeView: 'list' | 'grid';
  isSidebarCollapsed: boolean;
  selectedRowIds: Set<string>;
  
  // Dialog States
  isBatchOpen: boolean;
  isSettingsOpen: boolean;
  
  toggleSidebar: () => void;
  setView: (view: 'list' | 'grid') => void;
  toggleRowSelection: (id: string, multi?: boolean) => void;
  clearSelection: () => void;
  
  setBatchOpen: (open: boolean) => void;
  setSettingsOpen: (open: boolean) => void;
}

export const useSession = create<SessionState>((set) => ({
  activeView: 'list',
  isSidebarCollapsed: false,
  selectedRowIds: new Set(),
  isBatchOpen: false,
  isSettingsOpen: false,

  toggleSidebar: () => set((state) => ({ isSidebarCollapsed: !state.isSidebarCollapsed })),
  setView: (view) => set({ activeView: view }),
  
  toggleRowSelection: (id, multi) => set((state) => {
    const newSet = new Set(multi ? state.selectedRowIds : []);
    if (newSet.has(id)) {
      newSet.delete(id);
    } else {
      newSet.add(id);
    }
    return { selectedRowIds: newSet };
  }),

  clearSelection: () => set({ selectedRowIds: new Set() }),
  
  setBatchOpen: (open) => set({ isBatchOpen: open }),
  setSettingsOpen: (open) => set({ isSettingsOpen: open }),
}));