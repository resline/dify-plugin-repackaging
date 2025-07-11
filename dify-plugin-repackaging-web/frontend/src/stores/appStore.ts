import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface Task {
  task_id: string;
  // Add other task properties as needed
}

interface AppState {
  // Tab navigation
  currentTab: string;
  setCurrentTab: (tab: string) => void;
  
  // Task management
  currentTask: Task | null;
  setCurrentTask: (task: Task | null) => void;
  isProcessing: boolean;
  setIsProcessing: (processing: boolean) => void;
  
  // Sidebar state
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  
  // Processing panel state
  isProcessingPanelMinimized: boolean;
  toggleProcessingPanel: () => void;
  setProcessingPanelMinimized: (minimized: boolean) => void;
  
  // Form state preservation
  formState: {
    url: string;
    platform: string;
    suffix: string;
  };
  setFormState: (state: Partial<AppState['formState']>) => void;
}

const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      // Tab navigation
      currentTab: 'url',
      setCurrentTab: (tab) => set({ currentTab: tab }),
      
      // Task management
      currentTask: null,
      setCurrentTask: (task) => set({ 
        currentTask: task, 
        isProcessing: !!task 
      }),
      isProcessing: false,
      setIsProcessing: (processing) => set({ isProcessing: processing }),
      
      // Sidebar state
      isSidebarOpen: true,
      toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
      setSidebarOpen: (open) => set({ isSidebarOpen: open }),
      
      // Processing panel state
      isProcessingPanelMinimized: false,
      toggleProcessingPanel: () => set((state) => ({ 
        isProcessingPanelMinimized: !state.isProcessingPanelMinimized 
      })),
      setProcessingPanelMinimized: (minimized) => set({ 
        isProcessingPanelMinimized: minimized 
      }),
      
      // Form state preservation
      formState: {
        url: '',
        platform: '',
        suffix: 'offline'
      },
      setFormState: (newState) => set((state) => ({
        formState: { ...state.formState, ...newState }
      }))
    }),
    {
      name: 'dify-plugin-repackaging-store',
      partialize: (state) => ({
        currentTab: state.currentTab,
        isSidebarOpen: state.isSidebarOpen,
        formState: state.formState
      })
    }
  )
);

export default useAppStore;