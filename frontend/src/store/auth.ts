import { create } from "zustand";
import type { Session } from "@supabase/supabase-js";

export type Role = "STUDENT" | "ACADEMIC_ADMIN" | "FACULTY";

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  is_demo: boolean;
}

interface AuthState {
  session: Session | null;
  profile: UserProfile | null;
  setSession: (session: Session | null) => void;
  setProfile: (profile: UserProfile | null) => void;
  clearAuth: () => void;
  isAuthenticated: () => boolean;
  /** Supabase access token — attached to every API request */
  getToken: () => string | null;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  session: null,
  profile: null,

  setSession: (session) => set({ session }),
  setProfile: (profile) => set({ profile }),

  clearAuth: () => set({ session: null, profile: null }),

  isAuthenticated: () => get().session !== null,

  getToken: () => get().session?.access_token ?? null,
}));
