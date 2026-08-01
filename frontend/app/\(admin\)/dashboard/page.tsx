"use client";

import { useState, useEffect } from "react";
import { createBrowserClient } from "@supabase/supabase-js";
import { TicketList } from "@/components/TicketList";
import { HandoffQueue } from "@/components/HandoffQueue";
import { Loader2, Shield } from "lucide-react";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";

export default function DashboardPage() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState<{ email: string } | null>(null);

  useEffect(() => {
    if (!supabaseUrl || !supabaseAnonKey) {
      setIsLoading(false);
      return;
    }

    const supabase = createBrowserClient(supabaseUrl, supabaseAnonKey);

    // Check session
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user) {
        setIsAuthenticated(true);
        setUser({ email: session.user.email || "" });
      }
      setIsLoading(false);
    });

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) {
        setIsAuthenticated(true);
        setUser({ email: session.user.email || "" });
      } else {
        setIsAuthenticated(false);
        setUser(null);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <div className="max-w-md w-full bg-surface border border-border rounded-2xl p-8">
          <Shield className="w-12 h-12 mx-auto text-primary mb-4" />
          <h1 className="text-2xl font-bold text-center text-text-primary mb-2">Admin Dashboard</h1>
          <p className="text-center text-text-secondary mb-6">Sign in to access the support dashboard</p>
          <button
            onClick={() => {
              if (supabaseUrl && supabaseAnonKey) {
                const supabase = createBrowserClient(supabaseUrl, supabaseAnonKey);
                supabase.auth.signInWithOAuth({ provider: "email" });
              }
            }}
            className="w-full px-4 py-3 bg-primary text-white rounded-lg hover:bg-primary-hover transition-colors font-medium"
          >
            Sign in with Email
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="bg-surface border-b border-border sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-xl font-semibold text-text-primary">Support Dashboard</h1>
          </div>
          <div className="flex items-center gap-4 text-sm text-text-secondary">
            <span>{user?.email}</span>
            <button className="text-primary hover:underline">Sign out</button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid gap-6 lg:grid-cols-2">
          <TicketList />
          <HandoffQueue />
        </div>
      </main>
    </div>
  );
}