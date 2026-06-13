import { apiClient } from "./api";
import type { UserProfile } from "@/store/auth";

export interface SyncProfilePayload {
  email: string;
  full_name: string;
  role: "student" | "professor";
}

export const authApi = {
  /** Called after Supabase signUp() to persist the role in our DB. */
  syncProfile: (payload: SyncProfilePayload) =>
    apiClient.post<UserProfile>("/auth/sync-profile", payload),

  /** Returns the current user's profile from our DB. */
  me: () => apiClient.get<UserProfile>("/auth/me"),
};
