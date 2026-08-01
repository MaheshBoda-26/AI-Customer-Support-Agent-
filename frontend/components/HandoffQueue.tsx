"use client";

import { useEffect, useState } from "react";
import { createBrowserClient } from "@supabase/supabase-js";
import { AlertCircle, Clock, User, MessageSquare } from "lucide-react";
import { format } from "date-fns";

interface Handoff {
  id: string;
  conversation_id: string;
  reason: string;
  assigned_to: string | null;
  created_at: string;
}

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";

export function HandoffQueue() {
  const [handoffs, setHandoffs] = useState<Handoff[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!supabaseUrl || !supabaseAnonKey) {
      setIsLoading(false);
      return;
    }

    const supabase = createBrowserClient(supabaseUrl, supabaseAnonKey);

    // Initial fetch
    const fetchHandoffs = async () => {
      const { data, error } = await supabase
        .from("handoffs")
        .select("*")
        .order("created_at", { ascending: false })
        .limit(50);

      if (!error && data) {
        setHandoffs(data);
      }
      setIsLoading(false);
    };

    fetchHandoffs();

    // Realtime subscription
    const channel = supabase
      .channel("handoffs-changes")
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "handoffs",
        },
        (payload) => {
          if (payload.eventType === "INSERT") {
            setHandoffs((prev) => [payload.new as Handoff, ...prev.slice(0, 49)]);
          } else if (payload.eventType === "UPDATE") {
            setHandoffs((prev) =>
              prev.map((h) => (h.id === payload.new.id ? (payload.new as Handoff) : h))
            );
          } else if (payload.eventType === "DELETE") {
            setHandoffs((prev) => prev.filter((h) => h.id !== payload.old.id));
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  return (
    <div className="bg-surface border border-border rounded-2xl overflow-hidden">
      <div className="p-4 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-danger" />
          <h2 className="text-lg font-semibold text-text-primary">Escalation Queue</h2>
        </div>
        <span className={`flex items-center gap-1 text-sm ${
          handoffs.length > 0 ? "text-danger" : "text-text-secondary"
        }`}>
          {handoffs.length > 0 && <span className="w-2 h-2 bg-danger rounded-full animate-pulse" />}
          {handoffs.length} active
        </span>
      </div>

      {isLoading ? (
        <div className="p-8 text-center text-text-secondary">
          <div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full mx-auto mb-2" />
          <p>Loading escalations...</p>
        </div>
      ) : handoffs.length === 0 ? (
        <div className="p-8 text-center text-text-secondary">
          <AlertCircle className="w-12 h-12 mx-auto text-primary/30 mb-3" />
          <p>No active escalations</p>
        </div>
      ) : (
        <div className="divide-y divide-border">
          {handoffs.map((handoff) => (
            <div key={handoff.id} className="p-4 bg-danger/5 hover:bg-danger/10 transition-colors">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-danger/10 flex items-center justify-center flex-shrink-0">
                  <AlertCircle className="w-5 h-5 text-danger" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-medium text-text-primary">
                      Conversation: {handoff.conversation_id.slice(0, 8)}...
                    </p>
                    <span className="text-xs text-text-secondary whitespace-nowrap">
                      {format(new Date(handoff.created_at), "HH:mm:ss")}
                    </span>
                  </div>
                  <p className="text-sm text-text-secondary mt-1">{handoff.reason}</p>
                  <div className="flex items-center gap-3 mt-2 text-xs text-text-secondary">
                    <span className="flex items-center gap-1">
                      <User className="w-3 h-3" />
                      {handoff.assigned_to || "Unassigned"}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}