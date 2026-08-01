"use client";

import { format } from "date-fns";
import { Ticket, TicketStatus, TicketPriority, TicketCategory } from "@/lib/api";

interface TicketListProps {
  tickets?: Ticket[];
}

const statusColors: Record<TicketStatus, string> = {
  open: "bg-warning/10 text-warning border-warning/30",
  in_progress: "bg-primary/10 text-primary border-primary/30",
  resolved: "bg-success/10 text-success border-success/30",
};

const priorityColors: Record<TicketPriority, string> = {
  low: "bg-text-secondary/10 text-text-secondary",
  normal: "bg-primary/10 text-primary",
  high: "bg-warning/10 text-warning",
  urgent: "bg-danger/10 text-danger",
};

const categoryLabels: Record<TicketCategory, string> = {
  billing: "Billing",
  bug: "Bug",
  account: "Account",
  other: "Other",
};

export function TicketList({ tickets = [] }: TicketListProps) {
  return (
    <div className="bg-surface border border-border rounded-2xl overflow-hidden">
      <div className="p-4 border-b border-border flex items-center justify-between">
        <h2 className="text-lg font-semibold text-text-primary">Tickets</h2>
        <span className="text-sm text-text-secondary">{tickets.length} total</span>
      </div>

      {tickets.length === 0 ? (
        <div className="p-8 text-center text-text-secondary">
          <p>No tickets found</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border bg-muted">
                <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider">
                  Subject
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider">
                  Priority
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider">
                  Category
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-text-secondary uppercase tracking-wider">
                  Created
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {tickets.map((ticket) => (
                <tr key={ticket.id} className="hover:bg-muted/50">
                  <td className="px-4 py-3">
                    <p className="text-sm font-medium text-text-primary truncate max-w-xs">
                      {ticket.subject}
                    </p>
                    <p className="text-xs text-text-secondary truncate max-w-xs">
                      {ticket.description.slice(0, 60)}...
                    </p>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${statusColors[ticket.status]}`}>
                      {ticket.status.replace("_", " ")}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${priorityColors[ticket.priority]}`}>
                      {ticket.priority}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-sm text-text-secondary">
                      {categoryLabels[ticket.category]}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-text-secondary">
                    {format(new Date(ticket.created_at), "MMM d, yyyy")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}