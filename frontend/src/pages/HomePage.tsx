import { RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import type { DocumentRecord } from "../api";
import { api } from "../api";
import { AskBox } from "../components/AskBox";
import { DocumentList } from "../components/DocumentList";

export function HomePage() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const refresh = () =>
    api
      .listDocuments()
      .then(setDocuments)
      .catch(() => undefined);
  useEffect(() => {
    void refresh();
    const handler = () => void refresh();
    window.addEventListener("documents-refresh", handler);
    return () => window.removeEventListener("documents-refresh", handler);
  }, []);
  return (
    <div className="space-y-10">
      <div className="flex items-end justify-between">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-[.15em] text-[#e88d35]">
            YOUR LIBRARY
          </p>
          <h1 className="mt-2 font-serif text-4xl font-medium tracking-tight text-[#17233b]">
            Your documents
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            Keep your sources close. Ask when you are ready.
          </p>
        </div>
        <button
          onClick={refresh}
          className="flex items-center gap-2 text-xs text-slate-400 hover:text-[#e88d35]"
        >
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>
      <DocumentList documents={documents} />
      <AskBox documents={documents} />
    </div>
  );
}
