/**
 * 全局状态管理
 */
import { create } from 'zustand';

interface AppState {
  // 用户信息
  user: {
    name: string;
    role: string;
  } | null;
  setUser: (user: AppState['user']) => void;
  
  // 加载状态
  loading: boolean;
  loadingTip?: string;
  setLoading: (loading: boolean, tip?: string) => void;
  
  // 当前选中的环境
  currentEnvironment: string | null;
  setCurrentEnvironment: (env: string | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  user: null,
  setUser: (user) => set({ user }),
  
  loading: false,
  loadingTip: "加载中...",
  setLoading: (loading, tip) => set({ loading, loadingTip: tip || "加载中..." }),
  
  currentEnvironment: null,
  setCurrentEnvironment: (env) => set({ currentEnvironment: env }),
}));
