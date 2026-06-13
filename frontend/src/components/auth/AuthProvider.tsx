"use client";

import { useEffect } from "react";
import { supabase } from "@/lib/supabase";
import { useAuthStore } from "@/store/auth";
import { authApi } from "@/lib/auth-api";

/**
 * Listens to Supabase auth state changes and keeps the Zustand store in sync.
 * Mount once in the root layout.
 */
export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const { setSession, setProfile, clearAuth } = useAuthStore();

  // Demo account to role mapping (for development/testing)
  const getDemoProfileFromEmail = (email: string, userId: string) => {
    if (email === "demo.student@campusos.app") {
      return {
        id: userId,
        email,
        full_name: "Demo Student",
        role: "STUDENT" as const,
        is_demo: true,
      };
    } else if (email === "demo.admin@campusos.app") {
      return {
        id: userId,
        email,
        full_name: "Demo Admin",
        role: "ACADEMIC_ADMIN" as const,
        is_demo: true,
      };
    } else if (email === "demo.professor@campusos.app") {
      return {
        id: userId,
        email,
        full_name: "Demo Professor",
        role: "FACULTY" as const,
        is_demo: true,
      };
    }
    return null;
  };

  useEffect(() => {
    // Hydrate session on mount
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      if (session?.user?.email) {
        // Try to get profile from backend
        authApi.me()
          .then((res) => setProfile(res.data))
          .catch(() => {
            // If backend fails, check if it's a demo account and use fallback
            const demoProfile = getDemoProfileFromEmail(
              session.user.email || "",
              session.user.id
            );
            if (demoProfile) {
              setProfile(demoProfile);
            }
          });
      }
    });

    // Keep in sync with Supabase auth events
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        setSession(session);

        if (session?.user?.email) {
          try {
            const res = await authApi.me();
            setProfile(res.data);
          } catch {
            // If backend fails, use demo profile fallback
            const demoProfile = getDemoProfileFromEmail(
              session.user.email,
              session.user.id
            );
            if (demoProfile) {
              setProfile(demoProfile);
            }
          }
        } else {
          clearAuth();
        }
      }
    );

    return () => subscription.unsubscribe();
  }, [setSession, setProfile, clearAuth]);

  return <>{children}</>;
}
